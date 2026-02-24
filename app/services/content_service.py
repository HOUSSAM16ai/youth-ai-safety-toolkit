"""
Content Service to encapsulate raw SQL queries for content retrieval.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ContentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_content(
        self, q: str | None, level: str | None, subject: str | None, limit: int = 50
    ) -> list[dict[str, Any]]:
        query_str = (
            "SELECT id, type, title, level, subject, year, lang FROM content_items WHERE 1=1"
        )
        params = {}

        if level:
            query_str += " AND level = :level"
            params["level"] = level
        if subject:
            query_str += " AND subject = :subject"
            params["subject"] = subject
        if q:
            query_str += " AND (title LIKE :q OR md_content LIKE :q)"
            params["q"] = f"%{q}%"

        query_str += " LIMIT :limit"
        params["limit"] = limit

        result = await self.db.execute(text(query_str), params)
        rows = result.fetchall()

        return [
            {
                "id": row[0],
                "type": row[1],
                "title": row[2],
                "level": row[3],
                "subject": row[4],
                "year": row[5],
                "lang": row[6],
            }
            for row in rows
        ]

    async def get_content(self, content_id: str) -> dict[str, Any]:
        result = await self.db.execute(
            text(
                "SELECT id, type, title, level, subject, year, lang, md_content FROM content_items WHERE id = :id"
            ),
            {"id": content_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Content not found")

        return {
            "id": row[0],
            "type": row[1],
            "title": row[2],
            "level": row[3],
            "subject": row[4],
            "year": row[5],
            "lang": row[6],
            "md_content": row[7],
        }

    async def get_content_raw(self, content_id: str) -> str:
        result = await self.db.execute(
            text("SELECT md_content FROM content_items WHERE id = :id"), {"id": content_id}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Content not found")
        return row[0]

    async def get_content_solution(self, content_id: str) -> dict[str, Any]:
        result = await self.db.execute(
            text(
                "SELECT solution_md, steps_json, final_answer FROM content_solutions WHERE content_id = :id"
            ),
            {"id": content_id},
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Solution not found")

        return {"solution_md": row[0], "steps_json": row[1], "final_answer": row[2]}
