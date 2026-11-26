"""自测：覆盖登录、鉴权拦截、退出后失效、排序重排。

运行：uv run pytest -q
"""

import os
import pathlib
import tempfile

_TEST_DB = pathlib.Path(tempfile.mkdtemp()) / "test.db"
os.environ["APP_DB_PATH"] = str(_TEST_DB)

from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

from app.db import get_conn, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD = "test12345"


@pytest.fixture(autouse=True)
def clean_db() -> None:
    """每个用例都从空库开始，避免前一个用例的数据影响判断。"""
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM memos")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM users")


def _seed_user(username: str = "tester", display_name: str = "测试同学") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, display_name, password_hash, created_at) "
            "VALUES (?, ?, ?, '2026-01-01T00:00:00+00:00')",
            (username, display_name, hash_password(PASSWORD)),
        )


def _login(client: TestClient, username: str = "tester") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_health_needs_no_auth() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_rejects_wrong_password_and_unknown_user_with_same_message() -> None:
    with TestClient(app) as client:
        _seed_user()
        wrong = client.post("/auth/login", json={"username": "tester", "password": "nope"})
        unknown = client.post("/auth/login", json={"username": "ghost", "password": "nope"})
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    # 两种失败必须给出同一句话，否则会泄露账号是否存在。
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_login_rejects_empty_fields() -> None:
    with TestClient(app) as client:
        resp = client.post("/auth/login", json={"username": "", "password": ""})
    assert resp.status_code == 422


def test_me_requires_valid_token() -> None:
    with TestClient(app) as client:
        _seed_user()
        assert client.get("/auth/me").status_code == 401
        assert client.get("/auth/me", headers={"Authorization": "Bearer forged"}).status_code == 401

        token = _login(client)
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "tester"
        # 响应里不能出现密码或凭证。
        assert "password" not in resp.text and token not in resp.text


def test_memos_require_auth_and_are_scoped_to_user() -> None:
    with TestClient(app) as client:
        _seed_user()
        assert client.get("/memos").status_code == 401

        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post("/memos", json={"title": "写周报", "quadrant": 1}, headers=headers)
        assert created.status_code == 201
        memo_id = created.json()["id"]

        listed = client.get("/memos", headers=headers).json()
        assert [m["id"] for m in listed] == [memo_id]

        # 另一个账号拿不到别人的数据，也改不动别人的数据。
        _seed_user("other", "另一个同学")
        other_headers = {"Authorization": f"Bearer {_login(client, 'other')}"}
        assert client.get("/memos", headers=other_headers).json() == []
        assert client.patch(f"/memos/{memo_id}", json={"done": True}, headers=other_headers).status_code == 404


def test_toggle_done_reorder_and_delete() -> None:
    with TestClient(app) as client:
        _seed_user()
        headers = {"Authorization": f"Bearer {_login(client)}"}

        ids = [
            client.post("/memos", json={"title": f"事项{i}"}, headers=headers).json()["id"]
            for i in range(3)
        ]

        done = client.patch(f"/memos/{ids[0]}", json={"done": True}, headers=headers)
        assert done.status_code == 200 and done.json()["done"] is True

        reversed_ids = list(reversed(ids))
        assert client.post("/memos/reorder", json={"ids": reversed_ids}, headers=headers).status_code == 204
        assert [m["id"] for m in client.get("/memos", headers=headers).json()] == reversed_ids

        assert client.delete(f"/memos/{ids[0]}", headers=headers).status_code == 204
        assert len(client.get("/memos", headers=headers).json()) == 2


def test_logout_invalidates_old_token() -> None:
    with TestClient(app) as client:
        _seed_user()
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        assert client.post("/auth/logout", headers=headers).status_code == 204
        # 退出后原凭证立刻失效。
        assert client.get("/auth/me", headers=headers).status_code == 401
        assert client.get("/memos", headers=headers).status_code == 401


def test_expired_session_is_rejected() -> None:
    import time

    with TestClient(app) as client:
        _seed_user()
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        from app.security import token_digest

        with get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE token_hash = ?",
                (int(time.time()) - 10, token_digest(token)),
            )
        assert client.get("/auth/me", headers=headers).status_code == 401
