import re
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction


class Tool(Protocol):
    name: str

    async def __call__(self, session: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class ParseTransactionQuestionTool:
    name = "parse_transaction_question"
    description = "Turn a plain-English transaction question into query filters."

    async def __call__(self, session: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
        question = str(payload.get("question", "")).lower()
        status = ""
        if any(word in question for word in ["failed", "failure", "error"]):
            status = "error"
        elif any(word in question for word in ["success", "successful", "succeeded", "passed"]):
            status = "passed"

        days = 2
        window_match = re.search(r"(?:last|past)\s*(\d+)\s*days?", question)
        if window_match:
            days = int(window_match.group(1))
        elif "today" in question:
            days = 1
        return {"status": status, "days": days}


class SearchTransactionsTool:
    name = "search_transactions"
    description = "Search transactions by status and time window."

    async def __call__(self, session: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
        status = str(payload.get("status", "")).strip().lower()
        days = int(payload.get("days", 2))

        stmt = select(Transaction).order_by(Transaction.created_at.desc()).limit(50)
        if status:
            stmt = stmt.where(Transaction.status == status)
        if days > 0:
            stmt = stmt.where(Transaction.created_at >= datetime.now(UTC) - timedelta(days=days))

        rows = (await session.scalars(stmt)).all()
        return {
            "count": len(rows),
            "transactions": [
                {
                    "id": row.id,
                    "external_id": row.external_id,
                    "customer_name": row.customer_name,
                    "amount": float(row.amount),
                    "currency": row.currency,
                    "status": row.status,
                    "error_message": row.error_message,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ],
        }


TOOL_REGISTRY: dict[str, Tool] = {
    ParseTransactionQuestionTool.name: ParseTransactionQuestionTool(),
    SearchTransactionsTool.name: SearchTransactionsTool(),
}
