"""Base agent class for all agents in the swarm."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..cortensor_client import CortensorClient


@dataclass
class AgentMessage:
    """Message passed between agents."""

    content: str
    sender: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AgentTask:
    """Task to be executed by an agent."""

    task_id: str
    description: str
    input_data: dict[str, Any]
    parent_task_id: str | None = None
    status: str = "pending"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "input_data": self.input_data,
            "parent_task_id": self.parent_task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, client: CortensorClient):
        self.name = name
        self.client = client
        self.message_history: list[AgentMessage] = []

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentTask:
        """Execute a task and return the result."""
        pass

    async def send_message(self, content: str, metadata: dict[str, Any] | None = None) -> AgentMessage:
        """Send a message (logged to history)."""
        message = AgentMessage(
            content=content,
            sender=self.name,
            metadata=metadata or {},
        )
        self.message_history.append(message)
        return message

    async def inference(self, prompt: str) -> str:
        """Execute inference through Cortensor."""
        response = await self.client.inference(prompt)
        return response.content

    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type."""
        return f"You are {self.name}, an AI agent in a multi-agent system."
