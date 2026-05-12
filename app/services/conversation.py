"""Conversation memory with sliding window and summarization."""

from datetime import datetime
from typing import Any, List, Optional

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.models import ConversationMessage, ConversationState

logger = structlog.get_logger()


class ConversationMemory:
    """Manages conversation history with sliding window and summarization.

    Features:
    - Sliding window of recent messages
    - Automatic summarization when window is full
    - Persistent conversation state
    """

    def __init__(
        self,
        window_size: int = 10,
        summary_threshold: int = 20,
    ):
        """Initialize conversation memory.

        Args:
            window_size: Number of recent messages to keep in context.
            summary_threshold: Messages count before summarization triggers.
        """
        self.llm = ChatOpenAI(model=settings.openai_model, temperature=0)
        self.window_size = window_size
        self.summary_threshold = summary_threshold
        self._conversations: dict[str, ConversationState] = {}
        logger.info(
            "Initialized conversation memory",
            window_size=window_size,
            summary_threshold=summary_threshold,
        )

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> ConversationState:
        """Add a message to conversation history.

        Args:
            conversation_id: Unique conversation identifier.
            role: Message role (user/assistant/system).
            content: Message content.

        Returns:
            Updated conversation state.
        """
        state = self._get_or_create(conversation_id)

        state.messages.append(ConversationMessage(role=role, content=content))
        state.updated_at = datetime.utcnow()

        # Trigger summarization if needed
        if len(state.messages) >= self.summary_threshold:
            await self._summarize(state)

        logger.debug(
            "Added message to conversation",
            conversation_id=conversation_id,
            message_count=len(state.messages),
        )

        return state

    async def get_context(self, conversation_id: str) -> tuple[str, List[ConversationMessage]]:
        """Get conversation context for LLM prompt.

        Returns summary + recent messages within window.

        Args:
            conversation_id: Unique conversation identifier.

        Returns:
            Tuple of (summary, recent_messages).
        """
        state = self._conversations.get(conversation_id)
        if not state:
            return "", []

        recent = state.messages[-self.window_size :]
        return state.summary or "", recent

    def get_state(self, conversation_id: str) -> Optional[ConversationState]:
        """Get full conversation state.

        Args:
            conversation_id: Unique conversation identifier.

        Returns:
            Conversation state or None if not found.
        """
        return self._conversations.get(conversation_id)

    async def clear(self, conversation_id: str) -> bool:
        """Clear conversation history.

        Args:
            conversation_id: Unique conversation identifier.

        Returns:
            True if conversation was found and cleared.
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info("Cleared conversation", conversation_id=conversation_id)
            return True
        return False

    def _get_or_create(self, conversation_id: str) -> ConversationState:
        """Get existing or create new conversation state.

        Args:
            conversation_id: Unique conversation identifier.

        Returns:
            Conversation state.
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationState(conversation_id=conversation_id)
        return self._conversations[conversation_id]

    async def _summarize(self, state: ConversationState) -> None:
        """Generate summary of conversation history.

        Keeps the summary and drops older messages.

        Args:
            state: Conversation state to summarize.
        """
        messages_text = "\n".join(f"{m.role}: {m.content}" for m in state.messages)

        prompt = f"""Summarize the following conversation in 2-3 sentences.
Focus on the key topics and user intent.

Conversation:
{messages_text}

Summary:"""

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        state.summary = response.content if isinstance(response.content, str) else str(response.content)

        # Keep only recent messages after summarization
        state.messages = state.messages[-self.window_size :]

        logger.info(
            "Summarized conversation",
            conversation_id=state.conversation_id,
            summary_length=len(state.summary),
        )

    def to_langchain_messages(self, conversation_id: str) -> List[Any]:
        """Convert conversation to LangChain message format.

        Args:
            conversation_id: Unique conversation identifier.

        Returns:
            List of LangChain messages.
        """
        state = self._conversations.get(conversation_id)
        if not state:
            return []

        messages: List[Any] = []

        # Add summary as system message if exists
        if state.summary:
            messages.append(SystemMessage(content=f"Conversation summary: {state.summary}"))

        # Add recent messages
        for msg in state.messages[-self.window_size :]:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        return messages


# Singleton instance
conversation_memory = ConversationMemory()
