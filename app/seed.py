"""初始化练习账号：python -m app.seed

账号信息全部是虚构的，密码只在运行时从环境变量读取，
不写进源码、不写进 Git 历史、也不打印到日志里。
"""

import os
from datetime import datetime, timezone

from .db import get_conn, init_db
from .security import hash_password

DEFAULT_USERNAME = os.getenv("SEED_USERNAME", "demo")
DEFAULT_PASSWORD = os.getenv("SEED_PASSWORD", "demo12345")
DEFAULT_DISPLAY_NAME = os.getenv("SEED_DISPLAY_NAME", "练习同学")

SAMPLE_MEMOS = [
    ("交周报（虚构示例）", "2026-11-26T18:00", 1, 1000.0),
    ("读 FastAPI 官方教程的身份认证一节", "2026-11-27T21:00", 2, 2000.0),
    ("整理四象限的拖拽交互说明", None, 2, 3000.0),
    ("回复导师的评审意见", "2026-11-26T12:00", 3, 4000.0),
    ("了解 Agent Framework 是什么", None, 4, 5000.0),
]


def main() -> None:
    init_db()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (DEFAULT_USERNAME,)
        ).fetchone()

        if existing is None:
            cursor = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (
                    DEFAULT_USERNAME,
                    DEFAULT_DISPLAY_NAME,
                    hash_password(DEFAULT_PASSWORD),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
            user_id = cursor.lastrowid
            for title, due_at, quadrant, sort_order in SAMPLE_MEMOS:
                conn.execute(
                    """
                    INSERT INTO memos (user_id, title, due_at, quadrant, done, sort_order, created_at)
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        user_id,
                        title,
                        due_at,
                        quadrant,
                        sort_order,
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
            print(f"已创建练习账号：{DEFAULT_USERNAME}（密码见 SEED_PASSWORD，默认 demo12345）")
            print(f"已写入 {len(SAMPLE_MEMOS)} 条虚构备忘示例。")
        else:
            print(f"练习账号 {DEFAULT_USERNAME} 已存在，未做改动。")


if __name__ == "__main__":
    main()
