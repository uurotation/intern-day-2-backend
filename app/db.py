"""SQLite 存储层。

练习项目不引入独立数据库，用标准库 sqlite3 足够；
数据文件默认落在 data/app.db，容器里通过 volume 挂出来，重启不丢。
"""

import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT    NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);

CREATE TABLE IF NOT EXISTS memos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT    NOT NULL,
    due_at     TEXT,
    quadrant   INTEGER CHECK (quadrant BETWEEN 1 AND 4),
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    sort_order REAL    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memos_user ON memos(user_id, sort_order);
"""


def get_conn() -> sqlite3.Connection:
    """每次请求开一条连接。SQLite 本地文件开连接成本很低，比共享连接更省心。"""
    conn = sqlite3.connect(config.DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def next_sort_order(conn: sqlite3.Connection, user_id: int) -> float:
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM memos WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return float(row["max_order"]) + 1000.0
