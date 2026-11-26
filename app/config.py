"""运行期配置，全部通过环境变量覆盖，代码里不出现任何真实凭证。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = os.getenv("APP_DB_PATH", str(BASE_DIR / "data" / "app.db"))

SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "120"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

APP_NAME = "四象限备忘录 API"
APP_VERSION = "0.1.0"
