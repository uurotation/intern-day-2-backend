"""四象限备忘录接口。

所有查询都带 user_id 条件，用户只能看见和改动自己的数据；
即使前端伪造了别人的 id，也只是得到 404。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status

from ..db import get_conn, next_sort_order
from ..deps import CurrentUser
from ..schemas import MemoCreate, MemoOut, MemoReorderRequest, MemoUpdate

router = APIRouter(prefix="/memos", tags=["memos"])

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="备忘录不存在")


def _row_to_memo(row) -> MemoOut:
    return MemoOut(
        id=row["id"],
        title=row["title"],
        due_at=row["due_at"],
        quadrant=row["quadrant"],
        done=bool(row["done"]),
        sort_order=row["sort_order"],
    )


@router.get("", response_model=list[MemoOut], summary="按顺序列出备忘录")
def list_memos(
    current_user: CurrentUser,
    quadrant: int | None = Query(default=None, ge=1, le=4, description="只取某个象限"),
) -> list[MemoOut]:
    sql = "SELECT * FROM memos WHERE user_id = ?"
    params: list[object] = [current_user["id"]]
    if quadrant is not None:
        sql += " AND quadrant = ?"
        params.append(quadrant)
    sql += " ORDER BY sort_order ASC, id ASC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_memo(row) for row in rows]


@router.post("", response_model=MemoOut, status_code=status.HTTP_201_CREATED, summary="新建备忘录")
def create_memo(payload: MemoCreate, current_user: CurrentUser) -> MemoOut:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO memos (user_id, title, due_at, quadrant, done, sort_order, created_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
            """,
            (
                current_user["id"],
                payload.title,
                payload.due_at,
                payload.quadrant,
                next_sort_order(conn, current_user["id"]),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        row = conn.execute("SELECT * FROM memos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_memo(row)


@router.patch("/{memo_id}", response_model=MemoOut, summary="修改、划掉或移动象限")
def update_memo(memo_id: int, payload: MemoUpdate, current_user: CurrentUser) -> MemoOut:
    fields: list[str] = []
    params: list[object] = []

    if payload.title is not None:
        fields.append("title = ?")
        params.append(payload.title)
    if "due_at" in payload.model_fields_set:
        fields.append("due_at = ?")
        params.append(payload.due_at)
    if "quadrant" in payload.model_fields_set:
        fields.append("quadrant = ?")
        params.append(payload.quadrant)
    if payload.done is not None:
        fields.append("done = ?")
        params.append(1 if payload.done else 0)

    if not fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="没有需要更新的字段",
        )

    params.extend([memo_id, current_user["id"]])
    with get_conn() as conn:
        cursor = conn.execute(
            f"UPDATE memos SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            params,
        )
        if cursor.rowcount == 0:
            raise NOT_FOUND
        row = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    return _row_to_memo(row)


@router.delete("/{memo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除备忘录")
def delete_memo(memo_id: int, current_user: CurrentUser) -> Response:
    with get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM memos WHERE id = ? AND user_id = ?",
            (memo_id, current_user["id"]),
        )
        if cursor.rowcount == 0:
            raise NOT_FOUND
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT, summary="按新顺序整体重排")
def reorder_memos(payload: MemoReorderRequest, current_user: CurrentUser) -> Response:
    """前端把拖拽后的完整顺序发上来，后端按数组下标重写 sort_order。

    用"整份顺序"而不是"和目标项换位置"，是为了避免两位数互相踩踏、
    也省掉前端算中间值的小数漂移。
    """
    with get_conn() as conn:
        owned = {
            row["id"]
            for row in conn.execute(
                "SELECT id FROM memos WHERE user_id = ?", (current_user["id"],)
            ).fetchall()
        }
        if not set(payload.ids) <= owned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="提交的备忘录不属于当前用户",
            )

        for index, memo_id in enumerate(payload.ids):
            conn.execute(
                "UPDATE memos SET sort_order = ? WHERE id = ? AND user_id = ?",
                ((index + 1) * 1000.0, memo_id, current_user["id"]),
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
