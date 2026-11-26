# 后端演示脚本

按顺序执行即可从零走到「登录 → 读写备忘录 → 退出」全流程，约 5 分钟。
命令在仓库根目录执行；Windows PowerShell 与 Linux/macOS 通用，`curl` 换行用 `\` 的地方在 PowerShell 里写成一行。

## 一、启动

```bash
docker compose up --build -d
docker compose ps
docker compose exec api uv run python -m app.seed
```

预期：`api` 容器状态为 `running`，seed 输出 `已创建练习账号：demo`。
账号固定为 `demo` / `demo12345`，数据落在命名卷 `api-data`。

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

## 二、登录与当前用户

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"demo\",\"password\":\"demo12345\"}"
# {"access_token":"...","token_type":"bearer","expires_in":7200}
```

把返回的令牌记下来，后续请求都要带 `Authorization: Bearer <token>`：

```bash
curl -s http://localhost:8000/auth/me -H "Authorization: Bearer <token>"
# {"id":1,"username":"demo","display_name":"练习同学"}
```

## 三、备忘录读写

```bash
# 列表：按 sort_order 升序，初始 5 条示例
curl -s http://localhost:8000/memos -H "Authorization: Bearer <token>"

# 新增
curl -s -X POST http://localhost:8000/memos -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"交第二天总结\",\"due_at\":\"2026-11-27T18:00\",\"quadrant\":1}"

# 划掉
curl -s -X PATCH http://localhost:8000/memos/2 -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -d "{\"done\":true}"

# 拖进象限 3（不重要但紧急）
curl -s -X PATCH http://localhost:8000/memos/3 -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" -d "{\"quadrant\":3}"

# 整体排序：把当前全部 id 按新顺序提交
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/memos/reorder \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d "{\"ids\":[3,1,2,4,5]}"
```

象限取值：`1` 重要且紧急、`2` 重要不紧急、`3` 不重要但紧急、`4` 不重要不紧急、`null` 未分类。
前端把象限拆成两行标签展示，提交时再拼回数值。

## 四、错误场景（演示时挑两条即可）

```bash
# 错误密码与不存在的账号：提示完全一致，防账号枚举
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d "{\"username\":\"demo\",\"password\":\"wrong\"}"
# {"detail":"账号或密码错误"}

# 伪造令牌
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/memos \
  -H "Authorization: Bearer forged-token-xxx"
# 401

# 空标题
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/memos \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"title\":\"  \"}"
# 422

# 退出后旧令牌立即失效
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <token>"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/memos \
  -H "Authorization: Bearer <token>"
# 204 然后 401
```

## 五、数据持久化验证

```bash
docker compose down          # 只停容器，不删卷
docker compose up -d
curl -s http://localhost:8000/memos -H "Authorization: Bearer <新登录的令牌>"
```

预期：上面新增、划掉、排序的结果都还在，账号也还在。

`docker compose down -v` 会删除卷，数据全部清空，需要重新执行 `app.seed`。

## 六、接口自动化测试

```bash
uv run pytest -q        # 宿主机
docker compose exec api uv run pytest -q   # 容器内
```

预期：`8 passed`。覆盖登录成功/失败、令牌失效、用户隔离、字段校验与排序。
