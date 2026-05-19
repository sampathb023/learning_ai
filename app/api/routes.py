from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runner import AgentRunner
from app.agents.tools import TOOL_REGISTRY
from app.db import get_session
from app.models import Task, ToolCall, Transaction
from app.schemas import (
    AgentRunCreate,
    AgentRunRead,
    TaskRead,
    TransactionRead,
    ToolCallRead,
    ToolInfo,
    ToolInvokeCreate,
    ToolInvokeRead,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def transaction_chat() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Transaction Agent</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #f7f8fb; color: #172033; }
    main { max-width: 980px; margin: 0 auto; padding: 32px 20px; }
    h1 { font-size: 28px; margin: 0 0 8px; letter-spacing: 0; }
    p { margin: 0 0 24px; color: #5d697c; }
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 20px; }
    .panel { background: #fff; border: 1px solid #dde3ee; border-radius: 8px; padding: 18px; }
    label { display: block; font-size: 13px; font-weight: 700; margin-bottom: 8px; }
    textarea {
      width: 100%; min-height: 120px; box-sizing: border-box; resize: vertical;
      border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px;
      font: inherit; color: #172033; background: #fff;
    }
    button {
      margin-top: 12px; border: 0; border-radius: 6px; background: #176b5b; color: white;
      font: inherit; font-weight: 700; padding: 10px 14px; cursor: pointer;
    }
    button:disabled { opacity: .65; cursor: wait; }
    .query-buttons { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .query-buttons button {
      margin: 0; background: #eef4f2; color: #176b5b; border: 1px solid #bfd5ce;
      padding: 8px 10px; font-size: 13px;
    }
    pre {
      white-space: pre-wrap; overflow-wrap: anywhere; background: #111827; color: #e5e7eb;
      border-radius: 8px; padding: 14px; min-height: 180px; margin: 16px 0 0;
    }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th, td { text-align: left; padding: 9px 6px; border-bottom: 1px solid #e5e7eb; }
    th { color: #5d697c; font-size: 12px; text-transform: uppercase; }
    @media (max-width: 800px) { .layout { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <h1>Transaction Agent</h1>
    <p>Ask a plain-English question. The backend will translate it into a tool call against Postgres.</p>
    <div class="layout">
      <section class="panel">
        <label for="question">Question</label>
        <textarea id="question">Give me the transactions failed in the last 2 days</textarea>
        <div class="query-buttons" aria-label="Sample transaction questions">
          <button type="button" data-query="Show successful transactions in the last 5 days">Success, 5 days</button>
          <button type="button" data-query="Show failed transactions in the last 5 days">Failed, 5 days</button>
          <button type="button" data-query="Show successful transactions in the last 10 days">Success, 10 days</button>
          <button type="button" data-query="Show failed transactions in the last 10 days">Failed, 10 days</button>
        </div>
        <button id="ask">Ask Agent</button>
        <pre id="answer">The answer will appear here.</pre>
      </section>
      <aside class="panel">
        <strong>Sample data</strong>
        <table id="transactions">
          <thead><tr><th>ID</th><th>Status</th><th>Amount</th></tr></thead>
          <tbody></tbody>
        </table>
      </aside>
    </div>
  </main>
  <script>
    const answer = document.querySelector("#answer");
    const button = document.querySelector("#ask");
    const question = document.querySelector("#question");

    async function loadTransactions() {
      const response = await fetch("/transactions");
      const rows = await response.json();
      document.querySelector("#transactions tbody").innerHTML = rows.map(row => `
        <tr>
          <td>${row.external_id}</td>
          <td>${row.status}</td>
          <td>${row.amount} ${row.currency}</td>
        </tr>
      `).join("");
    }

    document.querySelectorAll("[data-query]").forEach(sampleButton => {
      sampleButton.addEventListener("click", () => {
        question.value = sampleButton.dataset.query;
      });
    });

    button.addEventListener("click", async () => {
      button.disabled = true;
      answer.textContent = "Running agent...";
      const input = question.value;
      const response = await fetch("/agent-runs", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({title: "Transaction question", input})
      });
      const data = await response.json();
      answer.textContent = data.task.output + "\\n\\nTool calls: " + data.tool_calls.length;
      button.disabled = false;
    });

    loadTransactions();
  </script>
</body>
</html>
"""


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("select 1"))
    return {"status": "ok", "database": "connected"}


@router.get("/transactions", response_model=list[TransactionRead])
async def list_transactions(
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Transaction]:
    stmt = select(Transaction).order_by(Transaction.created_at.desc())
    if status:
        stmt = stmt.where(Transaction.status == status.lower())
    return list(await session.scalars(stmt))


@router.post("/agent-runs", response_model=AgentRunRead, status_code=201)
async def run_agent(
    payload: AgentRunCreate, session: AsyncSession = Depends(get_session)
) -> AgentRunRead:
    task = Task(**payload.model_dump())
    session.add(task)
    await session.flush()

    runner = AgentRunner(session)
    completed_task, tool_calls = await runner.run(task)
    return AgentRunRead(task=completed_task, tool_calls=tool_calls)


@router.get("/tasks", response_model=list[TaskRead])
async def list_tasks(session: AsyncSession = Depends(get_session)) -> list[Task]:
    return list(await session.scalars(select(Task).order_by(Task.created_at.desc())))


@router.get("/tool-calls", response_model=list[ToolCallRead])
async def list_tool_calls(session: AsyncSession = Depends(get_session)) -> list[ToolCall]:
    return list(await session.scalars(select(ToolCall).order_by(ToolCall.created_at.desc())))


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    return [
        ToolInfo(name=name, description=getattr(tool, "description", "Local tool"))
        for name, tool in TOOL_REGISTRY.items()
    ]


@router.post("/tools/{tool_name}/invoke", response_model=ToolInvokeRead)
async def invoke_tool(
    tool_name: str,
    payload: ToolInvokeCreate,
    session: AsyncSession = Depends(get_session),
) -> ToolInvokeRead:
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    output = await tool(session, payload.input)
    return ToolInvokeRead(tool_name=tool_name, input=payload.input, output=output)
