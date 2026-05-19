from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import TOOL_REGISTRY
from app.models import Agent, Task, ToolCall


class AgentRunner:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run(self, task: Task) -> tuple[Task, list[ToolCall]]:
        agents = await self._resolve_agents(task)
        task.status = "running"
        await self.session.flush()

        planner = self._agent_named(agents, "planner")
        data_helper = self._agent_named(agents, "data-helper")
        parse_call = await self._call_tool(
            task=task,
            agent=planner,
            tool_name="parse_transaction_question",
            payload={"question": task.input},
        )

        search_call = await self._call_tool(
            task=task,
            agent=data_helper,
            tool_name="search_transactions",
            payload=parse_call.output,
        )
        tool_calls = [parse_call, search_call]

        task.output = self._compose_output(task, agents, tool_calls)
        task.status = "completed"
        await self.session.commit()
        await self.session.refresh(task)
        return task, tool_calls

    @staticmethod
    def _agent_named(agents: list[Agent], name: str) -> Agent | None:
        for agent in agents:
            if agent.name == name:
                return agent
        return agents[0] if agents else None

    async def _resolve_agents(self, task: Task) -> list[Agent]:
        stmt = select(Agent).order_by(Agent.created_at.asc()).limit(3)
        return list(await self.session.scalars(stmt))

    async def _call_tool(
        self,
        task: Task,
        agent: Agent | None,
        tool_name: str,
        payload: dict,
    ) -> ToolCall:
        tool = TOOL_REGISTRY[tool_name]
        output = await tool(self.session, payload)
        tool_call = ToolCall(
            tool_name=tool_name,
            input=payload,
            output=output,
            task_id=task.id,
            agent_id=agent.id if agent else None,
        )
        self.session.add(tool_call)
        await self.session.flush()
        return tool_call

    @staticmethod
    def _compose_output(task: Task, agents: list[Agent], tool_calls: list[ToolCall]) -> str:
        agent_names = ", ".join(agent.name for agent in agents) if agents else "default runner"
        transaction_results = []
        filters = {}
        for call in tool_calls:
            if call.tool_name == "parse_transaction_question":
                filters = call.output
            if call.tool_name == "search_transactions":
                transaction_results = call.output.get("transactions", [])

        lines = [f"{agent_names} completed task '{task.title}'.", "", "Result:"]

        if transaction_results:
            lines.append(
                f"Planner interpreted your question as filters: status={filters.get('status')}, "
                f"days={filters.get('days')}."
            )
            lines.append(f"Data helper found {len(transaction_results)} matching transactions:")
            for transaction in transaction_results:
                lines.append(
                    "- "
                    f"{transaction['external_id']} | {transaction['customer_name']} | "
                    f"{transaction['amount']} {transaction['currency']} | "
                    f"{transaction['status']} | {transaction['created_at']} | "
                    f"{transaction['error_message']}"
                )
        else:
            lines.append(
                f"Planner interpreted your question as filters: status={filters.get('status')}, "
                f"days={filters.get('days')}."
            )
            lines.append("Data helper found no matching transactions.")

        lines.extend(
            [
                "",
                "Next experiment:",
                "Expose search_transactions through a real MCP server so an external agent can call it.",
            ]
        )
        return "\n".join(lines)
