"""请求与响应模型。

每个字段都带约束，FastAPI 会自动把字段缺失、空串、超长、类型不对
转成 422 并在响应里指出是哪个字段出了问题。
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_PATTERN = r"^[a-zA-Z0-9_.-]{3,32}$"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32, description="登录账号")
    # 72 是 bcrypt 的输入上限，超过会被静默截断，所以在入口直接拒绝。
    password: str = Field(min_length=1, max_length=72, description="登录密码")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(description="凭证有效秒数")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str


class MemoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120, description="事件内容")
    due_at: str | None = Field(default=None, max_length=32, description="截止时间，ISO 8601")
    quadrant: int | None = Field(default=None, ge=1, le=4, description="1-4 为四象限，空表示未分类")

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("事件内容不能为空")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def check_due_at(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("截止时间格式应为 ISO 8601，例如 2026-11-26T18:00") from exc
        return value


class MemoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    due_at: str | None = Field(default=None, max_length=32)
    quadrant: int | None = Field(default=None, ge=1, le=4)
    done: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("事件内容不能为空")
        return cleaned

    @field_validator("due_at")
    @classmethod
    def check_due_at(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("截止时间格式应为 ISO 8601，例如 2026-11-26T18:00") from exc
        return value


class MemoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    due_at: str | None
    quadrant: int | None
    done: bool
    sort_order: float


class MemoReorderRequest(BaseModel):
    ids: list[int] = Field(min_length=1, description="按新顺序排列的备忘录 id")


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
