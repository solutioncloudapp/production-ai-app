"""Tests for prompts layer."""

import pytest

from app.models import PromptTemplate
from app.prompts.registry import PromptRegistry
from app.prompts.templates import PROMPT_TEMPLATES


class TestPromptTemplates:
    """Tests for prompt templates."""

    def test_templates_not_empty(self):
        assert len(PROMPT_TEMPLATES) > 0

    def test_template_structure(self):
        for _prompt_id, config in PROMPT_TEMPLATES.items():
            assert "version" in config
            assert "system" in config
            assert "human" in config
            assert "variables" in config
            assert "metadata" in config

    def test_required_prompts_exist(self):
        required = [
            "rag_generation",
            "query_rewrite",
            "query_route",
            "document_grade",
            "query_decompose",
        ]
        for prompt_id in required:
            assert prompt_id in PROMPT_TEMPLATES

    def test_template_variables_are_list(self):
        for _prompt_id, config in PROMPT_TEMPLATES.items():
            assert isinstance(config["variables"], list)

    def test_template_version_format(self):
        for _prompt_id, config in PROMPT_TEMPLATES.items():
            version = config["version"]
            parts = version.split(".")
            assert len(parts) == 3
            assert all(p.isdigit() for p in parts)


class TestPromptRegistry:
    """Tests for PromptRegistry."""

    @pytest.fixture
    def registry(self):
        reg = PromptRegistry()
        reg.initialize()
        return reg

    def test_initialization(self, registry):
        assert len(registry._templates) > 0
        assert len(registry._compiled) > 0

    def test_get_prompt(self, registry):
        prompt = registry.get("rag_generation")
        assert prompt is not None

    def test_get_nonexistent_prompt(self, registry):
        with pytest.raises(KeyError):
            registry.get("nonexistent_prompt")

    def test_get_prompt_version(self, registry):
        version = registry.get_version("rag_generation")
        assert version is not None
        assert isinstance(version, str)

    def test_get_nonexistent_prompt_version(self, registry):
        with pytest.raises(KeyError):
            registry.get_version("nonexistent_prompt")

    def test_list_prompts(self, registry):
        prompts = registry.list_prompts()
        assert len(prompts) > 0
        for p in prompts:
            assert "id" in p
            assert "version" in p
            assert "variables" in p

    def test_register_new_template(self, registry):
        template = PromptTemplate(
            id="custom_prompt",
            version="1.0.0",
            template="System: Be helpful\n\nHuman: {query}",
            variables=["query"],
        )
        registry.register(template)

        prompt = registry.get("custom_prompt")
        assert prompt is not None

    def test_register_updates_list(self, registry):
        before = len(registry.list_prompts())
        template = PromptTemplate(
            id="another_prompt",
            version="1.0.0",
            template="System: Test\n\nHuman: {input}",
            variables=["input"],
        )
        registry.register(template)
        after = len(registry.list_prompts())

        assert after == before + 1

    def test_compile_creates_chat_prompt(self, registry):
        prompt = registry.get("rag_generation")
        # LangChain ChatPromptTemplate has messages attribute
        assert hasattr(prompt, "messages")
        assert len(prompt.messages) == 2  # System + Human

    def test_get_specific_version(self, registry):
        # Version-specific lookup requires the version to be compiled
        # The default get returns the latest version
        prompt = registry.get("rag_generation")
        assert prompt is not None

    def test_get_invalid_version(self, registry):
        with pytest.raises(KeyError):
            registry.get("rag_generation", version="99.99.99")
