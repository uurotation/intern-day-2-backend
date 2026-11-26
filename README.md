# 四象限备忘录 · 后端

第二天练习项目的后端仓库：Python + FastAPI 提供 JSON API，负责登录鉴权与四象限备忘录的数据读写。

- 配套前端仓库：https://github.com/uurotation/intern-day-2-frontend
- 配套 PR：待本仓库首次推送后补
- 本次联调使用的前端分支/提交：待本仓库首次推送后补

## 一、项目主题与功能范围

一个只给自己看的备忘录：写下一件有截止时间的事，贴上「紧急 / 不紧急」「重要 / 不重要」的标签，
在另一个页面把未分类的事拖进四象限。

本仓库负责的部分：

| 能力 | 说明 |
| --- | --- |
| 账号密码登录 | 校验 SQLite 里的真实用户，bcrypt 校验密码，签发随机不透明令牌 |
| 获取当前用户 | 凭令牌返回 `id / username / display_name`，不返回密码哈希 |
| 退出登录 | 服务端删除会话，原令牌立即失效 |
| 四象限备忘录 | 增删改查、划掉（`done`）、按用户隔离 |
| 整体排序 | 前端把拖拽后的完整顺序提交，后端按下标重写顺序 |

**不做**：注册、找回密码、短信/第三方登录、角色权限、多设备会话管理。

### 验收条件

- [x] 错误账号与错误密码返回同一句提示（`账号或密码错误`）
- [x] 未携带、伪造、过期、已退出的令牌访问受保护接口一律 `401`
- [x] 一个用户看不到、也改不动另一个用户的备忘录
- [x] 字段为空、超长、格式错误时返回 `422` 并指出字段
- [x] 密码与令牌不出现在接口响应和日志里
- [x] 允许前端开发服务器跨域访问，其他来源的预检请求被拒

## 二、技术栈与版本

| 组件 | 版本 |
| --- | --- |
| Python | 3.12 |
| FastAPI | 见 `uv.lock` |
| Uvicorn | 见 `uv.lock` |
| bcrypt | 见 `uv.lock` |
| uv | 0.13.10 |
| SQLite | 标准库 `sqlite3` |

依赖清单在 `pyproject.toml`，锁文件是 `uv.lock`，镜像构建按锁文件安装。

## 三、目录结构

```text
intern-day-2-backend/
├── .devcontainer/          开发容器（Git + Python + uv）
├── .github/pull_request_template.md
├── app/
│   ├── config.py           环境变量读取
│   ├── db.py               SQLite 连接与建表
│   ├── security.py         bcrypt 哈希、令牌生成与摘要
│   ├── schemas.py          请求/响应模型与字段校验
│   ├── deps.py             令牌解析与 401 判定（鉴权只在这里）
│   ├── main.py             FastAPI 入口、CORS、/health
│   ├── seed.py             初始化虚构练习账号
│   └── routers/
│       ├── auth.py         登录 / 当前用户 / 退出
│       └── todos.py        备忘录 CRUD 与排序
├── tests/test_api.py       接口自测
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── uv.lock
└── .env.example
```

## 四、环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的前端来源，逗号分隔 |
| `SESSION_TTL_MINUTES` | `120` | 登录凭证有效分钟数 |
| `APP_DB_PATH` | `./data/app.db`（容器内 `/app/data/app.db`） | SQLite 文件路径 |
| `SEED_USERNAME` / `SEED_PASSWORD` / `SEED_DISPLAY_NAME` | `demo` / `demo12345` / `练习同学` | 仅初始化脚本使用 |

复制 `.env.example` 为 `.env` 后按需修改；`.env` 不进 Git。

## 五、初始化练习账号

账号是虚构的，密码在落库时只保存 bcrypt 哈希。

```bash
uv run python -m app.seed
```

输出示例：`已创建练习账号：demo`。默认账号 `demo` / 密码 `demo12345`。
重复执行不会重复创建，也不会覆盖已有账号。想换密码用环境变量覆盖：

```bash
SEED_USERNAME=demo SEED_PASSWORD=<你的练习密码> uv run python -m app.seed
```

## 六、接口约定

文档：`http://localhost:8000/docs`（OpenAPI 自动生成）

| 方法 | 路径 | 需要登录 | 说明 |
| --- | --- | --- | --- |
| GET | `/health` | 否 | 健康检查，返回 `{"status":"ok","version":"0.1.0"}` |
| POST | `/auth/login` | 否 | body `{username, password}`，成功返回 `{access_token, token_type, expires_in}` |
| GET | `/auth/me` | 是 | 返回 `{id, username, display_name}` |
| POST | `/auth/logout` | 是 | `204`，服务端删除当前会话 |
| GET | `/memos` | 是 | 按 `sort_order` 升序返回；可选 `?quadrant=1..4` |
| POST | `/memos` | 是 | body `{title, due_at?, quadrant?}`，`201` |
| PATCH | `/memos/{id}` | 是 | 可改 `title / due_at / quadrant / done`，只提交要改的字段 |
| DELETE | `/memos/{id}` | 是 | `204` |
| POST | `/memos/reorder` | 是 | body `{ids: [按新顺序排列的 id]}`，`204` |

象限取值：`1` 重要且紧急、`2` 重要不紧急、`3` 不重要但紧急、`4` 不重要不紧急、`null` 未分类。
前端把象限反过来拆成两个标签显示：`1` → 「紧急」「重要」，`2` → 「不紧急」「重要」，依此类推。

`due_at` 用 ISO 8601 字符串（如 `2026-11-26T18:00`），按本地时间存储，**不做时区换算**。

## 七、登录状态方案

- 采用**随机不透明令牌**（`secrets.token_urlsafe(32)`），不是 JWT，也不是 Cookie。
- 数据库 `sessions` 表只存令牌的 **sha256 摘要**，即使数据文件泄露也拿不到可用凭证。
- 有效期由 `SESSION_TTL_MINUTES` 控制，过期会话在下次访问时删除并返回 `401`。
- 退出登录直接删除会话行，**原令牌立刻失效**（这条有测试覆盖）。
- 前端把令牌放在 `localStorage`，每次请求带 `Authorization: Bearer <token>`。

为什么不用 Cookie：前端 5173、后端 8000 跨端口，Cookie 方案要处理 `SameSite` 与 `Secure`，
在 `localhost` 与 `127.0.0.1` 混用时容易静默失效；练习阶段用 Bearer 更好排查，`curl` 也方便验证 `401`。
代价是令牌落在 `localStorage`，理论上受 XSS 影响——这是本练习明确的取舍，未做 CSRF 防护。

## 八、数据保存方式

| 数据 | 位置 | 服务重启后 | 重建容器后 |
| --- | --- | --- | --- |
| 用户 | `users` 表 | 保留 | 保留（命名卷 `api-data`） |
| 会话 | `sessions` 表 | 保留（未过期即有效） | 保留 |
| 备忘录 | `memos` 表 | 保留 | 保留 |

执行 `docker compose down -v` 删除卷后全部清空，需重新运行 `python -m app.seed`。

## 九、启动方式

### 1. 开发容器（日常开发）

VS Code 打开本目录 → `Reopen in Container`。容器内已备 `git / python / uv`，
`postCreateCommand` 会执行 `uv sync && uv run python -m app.seed`。

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
uv run pytest -q
```

### 2. Docker Compose（独立启动）

```bash
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs --tail=100
```

首次启动后初始化账号（容器内执行）：

```bash
docker compose exec api uv run python -m app.seed
```

访问 `http://localhost:8000/health` 与 `http://localhost:8000/docs`。

### 3. 与前端联调

- 后端发布宿主机 `8000`，前端发布宿主机 `5173`。
- **浏览器直接访问 `http://localhost:8000`**，不经过 `127.0.0.1` 混用，也不使用容器内 `localhost` 或 Compose 服务名。
- 两个仓库是两个独立的 Compose 项目，默认不共享服务发现，所以前端通过宿主端口访问后端。
- 后端已放行 `http://localhost:5173` 与 `http://127.0.0.1:5173` 两个来源，并允许 `Authorization` 头，
  预检请求 `OPTIONS` 已通过 `CORSMiddleware` 处理。
- 若改了前端端口，必须同步改 `CORS_ORIGINS`，否则浏览器会拦下响应。

## 十、自测记录

以下为实际执行结果（本机 Windows + Python 3.12 + uv 0.13.10）：

| 检查项 | 操作 | 结果 |
| --- | --- | --- |
| 健康检查 | `GET /health` | `200 {"status":"ok","version":"0.1.0"}` |
| 错误密码 | `POST /auth/login` 错误密码 | `401 {"detail":"账号或密码错误"}` |
| 账号不存在 | `POST /auth/login` 不存在的账号 | `401`，提示与上一条完全一致 |
| 正常登录 | `demo` / 练习密码 | `200`，返回 `access_token` 与 `expires_in=7200` |
| 当前用户 | 带令牌 `GET /auth/me` | `200 {"id":1,"username":"demo","display_name":"练习同学"}` |
| 未带凭证 | 不带 `Authorization` | `401` |
| 伪造凭证 | `Bearer forged-token-xxx` | `401` |
| 列表 | `GET /memos` | `200`，返回 5 条虚构示例，按 `sort_order` 升序 |
| 新增 | `POST /memos` | `201`，返回新 id |
| 空标题 | `title` 为纯空格 | `422` |
| 划掉 | `PATCH /memos/2 {"done":true}` | `200`，`done` 变为 `true` |
| 拖进象限 | `PATCH /memos/3 {"quadrant":3}` | `200`，`quadrant` 变为 `3` |
| 整体排序 | `POST /memos/reorder {"ids":[3,1,2,4,5,6]}` | `204`，再查顺序为 `3,1,2,4,5,6` |
| 删除 | `DELETE /memos/6` | `204` |
| 退出 | `POST /auth/logout` | `204` |
| 退出后旧凭证 | 用退出前的令牌访问 `/memos` | `401` |
| 过期凭证 | 单测把 `expires_at` 改到过去 | `401` |
| CORS 预检 | `OPTIONS /memos`，`Origin: http://localhost:5173` | `200`，回 `access-control-allow-origin: http://localhost:5173` |
| 陌生来源 | `Origin: http://evil.example.com` | `400`，无放行头 |
| 用户隔离 | 另一账号读取同一份数据 | 列表为空，`PATCH` 他人条目返回 `404` |
| 单元测试 | `uv run pytest -q` | `8 passed` |

## 十一、已知问题与限制

1. **Vite 开发服务器演示，不是生产部署**：前端以开发模式启动，后端用 `uvicorn` 单进程。
2. **截止时间不做时区换算**：`due_at` 按本地时间原样存取，换时区访问会按浏览器本地时间解析。
3. **排序是"整份顺序"提交**：一次 `reorder` 会重写该用户所有条目的 `sort_order`，条目量大时效率不佳，但换来实现简单、不会出现小数漂移。
4. **令牌存 `localStorage`**：受 XSS 影响，见第七节的取舍说明；未实现 CSRF 防护（Bearer 方案本身不受 CSRF 影响，但 Cookie 方案需要）。
5. **未做注册与限流**：登录接口没有失败次数限制，练习范围外。
6. 会话表不会自动清理长期未使用的过期行，只在被访问时删除。
