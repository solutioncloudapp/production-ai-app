"""Code search tool for codebase and API documentation lookup."""

from typing import Any, Dict, List, Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()


class CodeSearchTool:
    """Tool for searching code repositories and documentation."""

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize code search tool.

        Args:
            repo_path: Path to code repository to index.
        """
        self.repo_path = repo_path
        self._index: Dict[str, str] = {}
        logger.info("Initialized code search tool", repo_path=repo_path)

    async def index_repository(self, path: str) -> None:
        """Index a code repository for search.

        Args:
            path: Path to repository.
        """
        import asyncio
        import os

        self.repo_path = path
        self._index = {}

        for root, dirs, files in os.walk(path):
            # Skip hidden directories and common non-code dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "__pycache__", "venv"]]

            for file in files:
                if self._is_code_file(file):
                    filepath = os.path.join(root, file)
                    try:

                        def _read_file(fp: str = filepath) -> str:
                            with open(fp, "r") as f:
                                return f.read()

                        content = await asyncio.to_thread(_read_file)
                        self._index[filepath] = content
                    except Exception:
                        pass

        logger.info("Repository indexed", path=path, files=len(self._index))

    async def search(self, query: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search indexed code for relevant snippets.

        Args:
            query: Search query (function name, concept, etc.).
            language: Optional language filter.

        Returns:
            List of matching code snippets.
        """
        results = []
        query_lower = query.lower()

        for filepath, content in self._index.items():
            if language and not filepath.endswith(f".{language}"):
                continue

            if query_lower in content.lower():
                # Extract relevant lines
                lines = content.split("\n")
                matching_lines = [(i, line) for i, line in enumerate(lines) if query_lower in line.lower()]

                for line_num, line in matching_lines[:3]:
                    start = max(0, line_num - 2)
                    end = min(len(lines), line_num + 3)
                    snippet = "\n".join(lines[start:end])

                    results.append(
                        {
                            "file": filepath,
                            "line": line_num + 1,
                            "snippet": snippet,
                            "match": line.strip(),
                        }
                    )

        logger.info("Code search complete", query=query, results=len(results))
        return results[:10]

    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file.

        Args:
            filename: File name to check.

        Returns:
            True if file is a code file.
        """
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".go",
            ".rs",
            ".rb",
            ".php",
            ".c",
            ".cpp",
            ".h",
            ".cs",
            ".swift",
            ".kt",
        }
        return any(filename.endswith(ext) for ext in code_extensions)


@tool
async def code_search(query: str, language: str = "") -> str:
    """Search code repositories and API documentation.

    Args:
        query: The search query (function name, concept, etc.).
        language: Optional language filter (python, javascript, etc.).

    Returns:
        Formatted code search results.
    """
    return f"Code search results for: {query}"
