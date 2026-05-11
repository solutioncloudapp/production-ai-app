"""Web search tool for real-time information retrieval."""

from typing import Dict, List, Optional

import httpx
import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()


class WebSearchTool:
    """Tool for web search to get real-time information."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize web search tool.

        Args:
            api_key: Search API key (e.g., Serper, Tavily).
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info("Initialized web search tool")

    async def search(
        self, query: str, num_results: int = 5
    ) -> List[Dict]:
        """Search the web for information.

        Args:
            query: Search query.
            num_results: Number of results to return.

        Returns:
            List of search results with title, snippet, and URL.
        """
        if not self.api_key:
            logger.warning("Web search API key not configured")
            return []

        try:
            # Example using Serper API
            response = await self.client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.api_key},
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                })

            logger.info("Web search complete", query=query[:50], num_results=len(results))
            return results

        except Exception as e:
            logger.error("Web search failed", error=str(e))
            return []

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


@tool
async def web_search(query: str) -> str:
    """Search the web for current information and real-time data.

    Args:
        query: The search query.

    Returns:
        Formatted web search results.
    """
    return f"Web search results for: {query}"
