"""依赖项：从 Authorization 头解析登录凭证。

鉴权只在这一处做。任何一个受保护接口都要经过 get_current_user，
未携带、伪造、已过期、已退出的凭证统一返回 401。
"""

import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from .db import get_conn
from .security import token_digest

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="登录状态无效，请重新登录",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UNAUTHORIZED

    token = authorization[7:].strip()
    if not token:
        raise UNAUTHORIZED

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT s.expires_at, u.id, u.username, u.display_name
            FROM sessions AS s
            JOIN users AS u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_digest(token),),
        ).fetchone()

        if row is None:
            raise UNAUTHORIZED

        if row["expires_at"] <= int(time.time()):
            # 过期就顺手清掉，免得表里越积越多。
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest(token),))
            raise UNAUTHORIZED

        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
        }


CurrentUser = Annotated[dict, Depends(get_current_user)]
