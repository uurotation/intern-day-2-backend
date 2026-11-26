"""登录、当前用户、退出。"""

import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status

from .. import config
from ..db import get_conn
from ..deps import CurrentUser
from ..schemas import LoginRequest, LoginResponse, UserOut
from ..security import burn_time, new_token, token_digest, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# 账号不存在和密码错误必须给同一句提示，否则等于告诉攻击者"这个账号存在"。
INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="账号或密码错误",
)


@router.post("/login", response_model=LoginResponse, summary="账号密码登录")
def login(payload: LoginRequest) -> LoginResponse:
    with get_conn() as conn:
        user = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()

        if user is None:
            burn_time()
            raise INVALID_CREDENTIALS

        if not verify_password(payload.password, user["password_hash"]):
            raise INVALID_CREDENTIALS

        token = new_token()
        ttl_seconds = config.SESSION_TTL_MINUTES * 60
        conn.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (
                user["id"],
                token_digest(token),
                int(time.time()) + ttl_seconds,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )

    return LoginResponse(access_token=token, expires_in=ttl_seconds)


@router.get("/me", response_model=UserOut, summary="获取当前用户")
def me(current_user: CurrentUser) -> UserOut:
    return UserOut(**current_user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="退出登录")
def logout(
    current_user: CurrentUser,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    # 走到这里说明凭证已通过校验，删掉会话即可，原凭证立刻失效。
    token = (authorization or "")[7:].strip()
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE token_hash = ? AND user_id = ?",
            (token_digest(token), current_user["id"]),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
