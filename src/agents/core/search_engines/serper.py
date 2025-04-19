import os
from typing import Dict, Any, Optional, List, TypeVar, Generic
from dataclasses import dataclass
import requests

T = TypeVar('T')


class SerperAPIException(Exception):
    """Custom exception for Serper API related errors"""
    pass


@dataclass
class SerperConfig:
    """Configuration for Serper API"""
    api_key: str
    api_url: str = "https://google.serper.dev/search"
    default_location: str = 'us'
    timeout: int = 100

    @classmethod
    def from_env(cls) -> 'SerperConfig':
        """Create config from environment variables"""
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise SerperAPIException(
                "SERPER_API_KEY environment variable not set"
            )
        return cls(api_key=api_key)


class SearchResult(Generic[T]):
    """Container for search results with error handling"""
    def __init__(
        self,
        data: Optional[T] = None,
        error: Optional[str] = None
    ):
        self.data = data
        self.error = error
        self.success = error is None

    @property
    def failed(self) -> bool:
        return not self.success


class SerperAPI:
    def __init__(
        self,
        config: Optional[SerperConfig] = None
    ):
        self.config = config or SerperConfig.from_env()
        self.headers = {
            'X-API-KEY': self.config.api_key,
            'Content-Type': 'application/json'
        }

    @staticmethod
    def extract_fields(
        items: List[Dict[str, Any]],
        fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Extract specified fields from a list of dictionaries"""
        return [
            {key: item.get(key, "") for key in fields if key in item}
            for item in items
        ]

    def get_sources(
        self,
        query: str,
        num_results: int = 8,
        stored_location: Optional[str] = None
    ) -> SearchResult[Dict[str, Any]]:
        """
        Fetch search results from Serper API.

        Args:
            query: Search query string
            num_results: Number of results to return
                (default: 10, max: 20 for pro users)
            stored_location: Optional location string

        Returns:
            SearchResult containing the search results or error information
        """
        if not query.strip():
            return SearchResult(error="Query cannot be empty")

        try:
            search_location = (
                stored_location or self.config.default_location
            ).lower()

            payload = {
                "q": query,
                "num": min(max(1, num_results), 10),
                "gl": search_location
            }

            response = requests.post(
                self.config.api_url,
                headers=self.headers,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            data = response.json()

            results = {
                'organic': self.extract_fields(
                    data.get('organic', []),
                    ['title', 'link', 'snippet', 'date']
                ),
                'topStories': self.extract_fields(
                    data.get('topStories', []),
                    ['title', 'imageUrl']
                ),
                'images': self.extract_fields(
                    data.get('images', [])[:6],
                    ['title', 'imageUrl']
                ),
                'graph': data.get('knowledgeGraph'),
                'answerBox': data.get('answerBox'),
                'peopleAlsoAsk': data.get('peopleAlsoAsk'),
                'relatedSearches': data.get('relatedSearches')
            }

            return SearchResult(data=results)

        except requests.RequestException as e:
            return SearchResult(error=f"API request failed: {str(e)}")
        except Exception as e:
            return SearchResult(error=f"Unexpected error: {str(e)}")
