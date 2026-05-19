import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Agent, Transaction


AGENTS = [
    {
        "name": "planner",
        "role": "Architecture planning agent",
        "instructions": "Break vague engineering goals into small, testable implementation steps.",
    },
    {
        "name": "data-helper",
        "role": "Postgres data agent",
        "instructions": "Prefer explicit schemas, inspectable data, and simple SQL-backed workflows.",
    },
]

def transaction_rows() -> list[dict]:
    now = datetime.now(UTC)
    return [
        {
            "external_id": "txn_1001",
            "customer_name": "Asha Patel",
            "amount": 129.99,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(hours=2),
        },
        {
            "external_id": "txn_1002",
            "customer_name": "Jordan Lee",
            "amount": 54.20,
            "currency": "USD",
            "status": "error",
            "error_message": "Card declined",
            "created_at": now - timedelta(hours=5),
        },
        {
            "external_id": "txn_1003",
            "customer_name": "Maria Garcia",
            "amount": 310.00,
            "currency": "USD",
            "status": "error",
            "error_message": "Payment gateway timeout",
            "created_at": now - timedelta(days=1, hours=3),
        },
        {
            "external_id": "txn_1004",
            "customer_name": "Noah Smith",
            "amount": 88.75,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(days=1, hours=8),
        },
        {
            "external_id": "txn_1005",
            "customer_name": "Lina Chen",
            "amount": 42.10,
            "currency": "USD",
            "status": "error",
            "error_message": "Insufficient funds",
            "created_at": now - timedelta(days=3),
        },
        {
            "external_id": "txn_1006",
            "customer_name": "Priya Shah",
            "amount": 215.45,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(days=4),
        },
        {
            "external_id": "txn_1007",
            "customer_name": "Ethan Brooks",
            "amount": 18.99,
            "currency": "USD",
            "status": "error",
            "error_message": "Expired card",
            "created_at": now - timedelta(days=4, hours=6),
        },
        {
            "external_id": "txn_1008",
            "customer_name": "Sofia Rossi",
            "amount": 760.00,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(days=5, hours=2),
        },
        {
            "external_id": "txn_1009",
            "customer_name": "Marcus Johnson",
            "amount": 64.35,
            "currency": "USD",
            "status": "error",
            "error_message": "Fraud rule triggered",
            "created_at": now - timedelta(days=6),
        },
        {
            "external_id": "txn_1010",
            "customer_name": "Hannah Kim",
            "amount": 142.80,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(days=7, hours=3),
        },
        {
            "external_id": "txn_1011",
            "customer_name": "Omar Hassan",
            "amount": 93.25,
            "currency": "USD",
            "status": "error",
            "error_message": "AVS check failed",
            "created_at": now - timedelta(days=8),
        },
        {
            "external_id": "txn_1012",
            "customer_name": "Grace Miller",
            "amount": 27.50,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(days=8, hours=12),
        },
        {
            "external_id": "txn_1013",
            "customer_name": "Diego Torres",
            "amount": 489.10,
            "currency": "USD",
            "status": "error",
            "error_message": "Processor unavailable",
            "created_at": now - timedelta(days=9, hours=4),
        },
        {
            "external_id": "txn_1014",
            "customer_name": "Emily Wilson",
            "amount": 305.75,
            "currency": "USD",
            "status": "passed",
            "error_message": None,
            "created_at": now - timedelta(days=10, hours=2),
        },
        {
            "external_id": "txn_1015",
            "customer_name": "Ben Carter",
            "amount": 11.49,
            "currency": "USD",
            "status": "error",
            "error_message": "Duplicate transaction",
            "created_at": now - timedelta(days=11),
        },
    ]


async def seed() -> None:
    async with SessionLocal() as session:
        for payload in AGENTS:
            existing = await session.scalar(select(Agent).where(Agent.name == payload["name"]))
            if not existing:
                session.add(Agent(**payload))

        for payload in transaction_rows():
            existing = await session.scalar(
                select(Transaction).where(Transaction.external_id == payload["external_id"])
            )
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
            else:
                session.add(Transaction(**payload))

        await session.commit()
    print("Seeded transaction agents and transactions.")


if __name__ == "__main__":
    asyncio.run(seed())
