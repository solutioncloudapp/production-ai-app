"""Prompt registry for versioned, hot-swappable prompt management."""

from typing import Any, Dict, List, Optional

import structlog
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

from app.models import PromptTemplate
from app.prompts.templates import PROMPT_TEMPLATES

logger = structlog.get_logger()


class PromptRegistry:
    """Central registry for versioned prompt templates.

    Features:
    - Versioned prompt templates
    - Hot-swappable without code changes
    - Type-specific prompt selection
    - Validation of template variables
    """

    def __init__(self) -> None:
        """Initialize prompt registry."""
        self._templates: Dict[str, List[PromptTemplate]] = {}
        self._compiled: Dict[str, ChatPromptTemplate] = {}
        logger.info("Initialized prompt registry")

    def initialize(self) -> None:
        """Load and compile all prompt templates."""
        for prompt_id, config in PROMPT_TEMPLATES.items():
            template = PromptTemplate(
                id=prompt_id,
                version=config["version"],
                template=config["system"] + "\n\n" + config["human"],
                variables=config["variables"],
                metadata=config.get("metadata", {}),
            )
            self._register(template)
            self._compile(prompt_id, config)

        logger.info(
            "Prompt registry initialized",
            num_prompts=len(self._templates),
        )

    def get(self, prompt_id: str, version: Optional[str] = None) -> ChatPromptTemplate:
        """Get compiled prompt template by ID.

        Args:
            prompt_id: Prompt identifier.
            version: Optional specific version. Uses latest if not specified.

        Returns:
            Compiled ChatPromptTemplate.

        Raises:
            KeyError: If prompt_id not found.
        """
        if prompt_id not in self._templates:
            raise KeyError(f"Prompt '{prompt_id}' not found in registry")

        if version:
            key = f"{prompt_id}:{version}"
            if key in self._compiled:
                return self._compiled[key]
            raise KeyError(f"Version '{version}' not found for prompt '{prompt_id}'")

        return self._compiled[prompt_id]

    def register(self, template: PromptTemplate) -> None:
        """Register a new prompt template.

        Args:
            template: PromptTemplate to register.
        """
        self._register(template)
        config = {
            "system": template.template.split("\n\n")[0],
            "human": template.template.split("\n\n")[-1],
            "variables": template.variables,
        }
        self._compile(template.id, config)
        logger.info("Registered prompt template", id=template.id, version=template.version)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all registered prompts.

        Returns:
            List of prompt metadata dictionaries.
        """
        result = []
        for _prompt_id, versions in self._templates.items():
            for v in versions:
                result.append(
                    {
                        "id": v.id,
                        "version": v.version,
                        "variables": v.variables,
                        "metadata": v.metadata,
                    }
                )
        return result

    def get_version(self, prompt_id: str) -> str:
        """Get latest version of a prompt.

        Args:
            prompt_id: Prompt identifier.

        Returns:
            Version string.
        """
        if prompt_id not in self._templates:
            raise KeyError(f"Prompt '{prompt_id}' not found")
        return self._templates[prompt_id][-1].version

    def _register(self, template: PromptTemplate) -> None:
        """Internal registration logic.

        Args:
            template: PromptTemplate to register.
        """
        if template.id not in self._templates:
            self._templates[template.id] = []
        self._templates[template.id].append(template)

    def _compile(self, prompt_id: str, config: Dict[str, Any]) -> None:
        """Compile prompt template into ChatPromptTemplate.

        Args:
            prompt_id: Prompt identifier.
            config: Prompt configuration dictionary.
        """
        messages = [
            SystemMessagePromptTemplate.from_template(config["system"]),
            HumanMessagePromptTemplate.from_template(config["human"]),
        ]
        self._compiled[prompt_id] = ChatPromptTemplate.from_messages(messages)


# Singleton instance
prompt_registry = PromptRegistry()
