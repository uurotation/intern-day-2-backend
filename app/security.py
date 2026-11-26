"""密码哈希与登录凭证生成。

- 密码用 bcrypt 存哈希，数据库里不出现明文。
- 登录凭证是随机不透明字符串，只在响应里返回一次；
  数据库里存的是它的 sha256 摘要，即使数据文件泄露也拿不到可用凭证。
"""

import hashlib
import secrets

import bcrypt

# bcrypt 只处理前 72 字节，超长密码在校验层就被拦掉了（见 schemas.LoginRequest）。
_DUMMY_HASH = bcrypt.hashpw(b"placeholder-for-timing", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def burn_time() -> None:
    """账号不存在时也算一次哈希，避免通过响应时间判断账号是否存在。"""
    bcrypt.checkpw(b"placeholder-for-timing", _DUMMY_HASH.encode("utf-8"))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
