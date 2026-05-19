from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TransactionRead(BaseModel):
    id: int
    external_id: str
    customer_name: str
    amount: float
    currency: str
    status: str
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskRead(BaseModel):
    id: int
    title: str
    input: str
    status: str
    output: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    input: str = Field(min_length=2)


class ToolCallRead(BaseModel):
    id: int
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any]
    task_id: int
    agent_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunRead(BaseModel):
    task: TaskRead
    tool_calls: list[ToolCallRead]


class ToolInfo(BaseModel):
    name: str
    description: str


class ToolInvokeCreate(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeRead(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any]
