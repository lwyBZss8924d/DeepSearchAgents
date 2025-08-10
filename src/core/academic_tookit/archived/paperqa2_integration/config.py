#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/academic_tookit/paperqa2_integration/config.py
# code style: PEP 8

"""
Configuration management for PaperQA2 integration.

This module provides configuration classes and utilities for managing
PaperQA2 settings in conjunction with our academic toolkit.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from paperqa import Settings
from paperqa.settings import AnswerSettings
from ..paper_reader.mistral_ocr import MistralOCRConfig


openai_api_key = os.getenv("LITELLM_MASTER_KEY")
openai_base_url = os.getenv("LITELLM_BASE_URL")
mistral_api_key = os.getenv("MISTRAL_API_KEY")


@dataclass
class PaperQA2Config:
    """
    Configuration for PaperQA2 integration.

    This configuration:
    - Manages LLM and embedding model selection
    - Controls parsing and chunking behavior
    - Sets evidence retrieval parameters
    - Configures caching and storage
    """

    # Model configuration
    llm_model: str = field(
        default="openai/gemini-2.5-pro",
        metadata={"help": "LLM model for Q&A"}
    )
    embedding_model: str = field(
        default="text-embedding-3-large",
        metadata={"help": "Embedding model for retrieval"}
    )

    # Parsing configuration
    chunk_size: int = field(
        default=5000,
        metadata={"help": "Size of text chunks"}
    )
    chunk_overlap: int = field(
        default=200,
        metadata={"help": "Overlap between chunks"}
    )
    use_mistral_ocr: bool = field(
        default=True,
        metadata={"help": "Use Mistral OCR for PDF parsing"}
    )

    # Retrieval configuration
    evidence_k: int = field(
        default=10,
        metadata={"help": "Number of evidence pieces to retrieve"}
    )
    answer_max_sources: int = field(
        default=5,
        metadata={"help": "Maximum sources in answer"}
    )

    # Agent configuration
    use_agent: bool = field(
        default=True,
        metadata={"help": "Use agent for multi-step reasoning"}
    )
    agent_strategy: str = field(
        default="function_calling",
        metadata={"help": "Agent strategy"}
    )

    # Storage configuration
    cache_dir: Optional[Path] = field(
        default=None,
        metadata={"help": "Directory for caching"}
    )
    index_dir: Optional[Path] = field(
        default=None,
        metadata={"help": "Directory for search index"}
    )

    # Provider configuration
    use_custom_providers: bool = field(
        default=True,
        metadata={"help": "Use custom metadata providers"}
    )
    enable_default_providers: bool = field(
        default=True,
        metadata={"help": "Also use default providers"}
    )

    # API keys (optional, can use environment)
    openai_api_key: Optional[str] = field(
        default=None,
        metadata={"help": "OpenAI API key"}
    )
    openai_base_url: Optional[str] = field(
        default=None,
        metadata={"help": "OpenAI API base URL"}
    )
    mistral_api_key: Optional[str] = field(
        default=None,
        metadata={"help": "Mistral API key"}
    )

    def __post_init__(self):
        """Initialize directories and load from environment."""
        # Set up directories
        if self.cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "paperqa2_academic"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if self.index_dir is None:
            self.index_dir = self.cache_dir / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Load API keys from environment if not set
        if self.openai_api_key is None:
            # Use LITELLM_MASTER_KEY for OpenAI API key
            self.openai_api_key = (
                os.getenv("LITELLM_MASTER_KEY") or
                os.getenv("OPENAI_API_KEY")
            )

        if self.openai_base_url is None:
            # Use LITELLM_BASE_URL for OpenAI base URL
            self.openai_base_url = (
                os.getenv("LITELLM_BASE_URL") or
                os.getenv("OPENAI_BASE_URL")
            )

        if self.mistral_api_key is None:
            self.mistral_api_key = os.getenv("MISTRAL_API_KEY")

    def to_paperqa_settings(self) -> Settings:
        """
        Convert to PaperQA2 Settings object.

        Returns:
            Configured Settings instance
        """
        from paperqa.settings import ParsingSettings

        # Configure answer settings
        answer_settings = AnswerSettings(
            evidence_k=self.evidence_k,
            answer_max_sources=self.answer_max_sources,
            answer_length="detailed",
            evidence_summary_length="detailed",
        )

        # Configure parsing settings
        parsing_settings = ParsingSettings(
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )

        # Create settings with all parameters
        settings_kwargs = {
            "llm": self.llm_model,
            "summary_llm": self.llm_model,  # Also set summary_llm to our model
            "embedding": self.embedding_model,
            "answer": answer_settings,
            "parsing": parsing_settings,
        }

        if self.index_dir:
            settings_kwargs["index_directory"] = str(self.index_dir)

        settings = Settings(**settings_kwargs)

        # Note: API key and base URL should be set via environment variables
        # or passed to the model configuration directly, not on Settings object
        # For LiteLLM compatibility, ensure these are set in environment:
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        if self.openai_base_url:
            base_url = self.openai_base_url
            if not base_url.endswith('/v1'):
                base_url = base_url.rstrip('/') + '/v1'
            os.environ["OPENAI_BASE_URL"] = base_url

        return settings

    def to_mistral_config(self) -> MistralOCRConfig:
        """
        Create Mistral OCR configuration.

        Returns:
            MistralOCRConfig instance
        """
        return MistralOCRConfig(
            api_key=self.mistral_api_key or "",
            max_pages=100,  # Process in chunks
            include_image_base64=True,
            retry_attempts=3,
            min_markdown_length=500,
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PaperQA2Config":
        """
        Create config from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            PaperQA2Config instance
        """
        # Filter to valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in config_dict.items() if k in valid_fields}

        # Handle path conversions
        for path_field in ["cache_dir", "index_dir"]:
            if path_field in filtered and filtered[path_field] is not None:
                filtered[path_field] = Path(filtered[path_field])

        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Configuration dictionary
        """
        result = {}

        for field_name, field_obj in self.__dataclass_fields__.items():
            value = getattr(self, field_name)

            # Convert paths to strings
            if isinstance(value, Path):
                value = str(value)

            # Skip None values
            if value is not None:
                result[field_name] = value

        return result

    def to_manager_kwargs(self) -> Dict[str, Any]:
        """
        Convert config to kwargs for PaperQA2Manager.

        Returns:
            Dictionary of manager initialization arguments
        """
        kwargs = {
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "evidence_k": self.evidence_k,
            "use_custom_providers": self.use_custom_providers,
            "cache_dir": self.cache_dir,
            "settings": self.to_paperqa_settings()  # Pre-configured settings
        }

        # Add Mistral OCR parser if enabled
        if self.use_mistral_ocr and self.mistral_api_key:
            from .mistral_ocr_parser import create_mistral_ocr_parser
            from ..paper_reader.mistral_ocr import MistralOCRConfig

            ocr_config = MistralOCRConfig(
                api_key=self.mistral_api_key,
                max_pages=100,
                include_image_base64=True
            )
            kwargs["pdf_parser"] = create_mistral_ocr_parser(config=ocr_config)

        return kwargs


@dataclass
class SearchConfig:
    """Configuration for paper search behavior."""

    default_sources: List[str] = field(
        default_factory=lambda: ["arxiv"],
        metadata={"help": "Default sources to search"}
    )
    max_concurrent_searches: int = field(
        default=3,
        metadata={"help": "Maximum concurrent searches"}
    )
    search_timeout: float = field(
        default=30.0,
        metadata={"help": "Search timeout in seconds"}
    )
    deduplicate_results: bool = field(
        default=True,
        metadata={"help": "Deduplicate search results"}
    )
    cache_search_results: bool = field(
        default=True,
        metadata={"help": "Cache search results"}
    )
    cache_ttl: int = field(
        default=3600,
        metadata={"help": "Cache TTL in seconds"}
    )


def load_config_from_env() -> PaperQA2Config:
    """
    Load configuration from environment variables.

    Environment variables:
    - PAPERQA2_LLM_MODEL
    - PAPERQA2_EMBEDDING_MODEL
    - PAPERQA2_CHUNK_SIZE
    - PAPERQA2_EVIDENCE_K
    - PAPERQA2_USE_MISTRAL_OCR
    - PAPERQA2_CACHE_DIR
    - etc.

    Returns:
        PaperQA2Config instance
    """
    config_dict = {}

    # Map environment variables to config fields
    env_mapping = {
        "PAPERQA2_LLM_MODEL": "llm_model",
        "PAPERQA2_EMBEDDING_MODEL": "embedding_model",
        "PAPERQA2_CHUNK_SIZE": "chunk_size",
        "PAPERQA2_CHUNK_OVERLAP": "chunk_overlap",
        "PAPERQA2_USE_MISTRAL_OCR": "use_mistral_ocr",
        "PAPERQA2_EVIDENCE_K": "evidence_k",
        "PAPERQA2_ANSWER_MAX_SOURCES": "answer_max_sources",
        "PAPERQA2_USE_AGENT": "use_agent",
        "PAPERQA2_CACHE_DIR": "cache_dir",
        "PAPERQA2_INDEX_DIR": "index_dir",
        "OPENAI_API_KEY": "openai_api_key",
        "MISTRAL_API_KEY": "mistral_api_key",
    }

    for env_var, config_field in env_mapping.items():
        value = os.getenv(env_var)
        if value is not None:
            # Convert types
            if config_field in ["chunk_size", "chunk_overlap", "evidence_k",
                                "answer_max_sources"]:
                value = int(value)
            elif config_field in ["use_mistral_ocr", "use_agent",
                                  "use_custom_providers"]:
                value = value.lower() in ["true", "1", "yes"]

            config_dict[config_field] = value

    return PaperQA2Config.from_dict(config_dict)
