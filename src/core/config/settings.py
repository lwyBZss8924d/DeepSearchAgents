#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/core/config/settings.py
# code style: PEP 8

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, Any, List, Optional
import os
import logging
import tomllib


logger = logging.getLogger("deepsearch-config")


class Settings(BaseSettings):
    """DeepSearchAgent configuration class, managed with Pydantic"""

    # Service configuration
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8000
    VERSION: str = ""
    DEEPSEARCH_AGENT_MODE: str = "codact"

    # Debug mode
    DEBUG: bool = False

    # Model configuration
    ORCHESTRATOR_MODEL_ID: str = ""
    SEARCH_MODEL_NAME: str = ""
    RERANKER_TYPE: str = "jina-reranker-m0"

    # Common agent configuration
    VERBOSE_TOOL_CALLBACKS: bool = True

    # React agent configuration
    REACT_MAX_STEPS: int = 25
    REACT_PLANNING_INTERVAL: int = 7
    REACT_MAX_TOOL_THREADS: int = 1

    # CodeAct agent configuration
    CODACT_EXECUTOR_TYPE: str = "local"
    CODACT_MAX_STEPS: int = 25
    CODACT_VERBOSITY_LEVEL: int = 2
    CODACT_PLANNING_INTERVAL: int = 4
    CODACT_EXECUTOR_KWARGS: Dict[str, Any] = Field(default_factory=dict)
    CODACT_ADDITIONAL_IMPORTS: List[str] = Field(default_factory=list)
    CODACT_USE_STRUCTURED_OUTPUTS: bool = True

    # Managed agents configuration
    MANAGED_AGENTS_ENABLED: bool = True
    MAX_DELEGATION_DEPTH: int = 3
    DEFAULT_MANAGED_AGENTS: List[str] = Field(
        default_factory=lambda: ["react", "codact"]
    )

    # Tools configuration
    TOOLS_HUB_COLLECTIONS: List[str] = Field(default_factory=list)
    TOOLS_TRUST_REMOTE_CODE: bool = False
    TOOLS_MCP_SERVERS: List[Dict[str, Any]] = Field(default_factory=list)
    TOOLS_SPECIFIC_CONFIG: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict
    )

    # Logging configuration
    LOGGING_LITELLM_LEVEL: str = "WARNING"
    LOGGING_FILTER_REPEATED_LOGS: bool = True
    LOGGING_FILTER_COST_CALCULATOR: bool = True
    LOGGING_FILTER_TOKEN_COUNTER: bool = True
    LOGGING_FORMAT: str = "minimal"

    # Token counting configuration
    ENABLE_TOKEN_COUNTING: bool = True
    LOG_TOKENS: bool = True

    # LiteLLM model list
    MODEL_LIST: List[Dict[str, Any]] = Field(default_factory=list)

    # APIKeys
    litellm_master_key: Optional[str] = None
    litellm_base_url: Optional[str] = None
    serper_api_key: Optional[str] = None
    jina_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    wolfram_alpha_app_id: Optional[str] = None
    hf_token: Optional[str] = None  # Hugging Face token for private repos

    model_config = {
        "env_file": ".env",
        "extra": "allow"
    }

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key"""
        return os.getenv(key_name)


def load_toml_config(settings_instance: Settings) -> Settings:
    """Load configuration from TOML file and update settings"""
    config_path = os.getenv("CONFIG_PATH", "config.toml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:  # note: TOML needs binary mode
                toml_config = tomllib.load(f)

            if not isinstance(toml_config, dict):
                logger.warning(
                    f"TOML file '{config_path}' does not contain a valid "
                    "dictionary structure, using default configuration."
                )
                return settings_instance

            # Update service configuration
            if 'service' in toml_config:
                service_config = toml_config['service']
                if 'host' in service_config:
                    settings_instance.SERVICE_HOST = service_config['host']
                if 'port' in service_config:
                    settings_instance.SERVICE_PORT = service_config['port']
                if 'version' in service_config:
                    settings_instance.VERSION = service_config['version']
                if 'deepsearch_agent_mode' in service_config:
                    settings_instance.DEEPSEARCH_AGENT_MODE = (
                        service_config['deepsearch_agent_mode']
                    )

            # Update debug mode
            if 'debug' in toml_config:
                settings_instance.DEBUG = toml_config['debug']

            # Update model configuration
            if 'models' in toml_config:
                models_config = toml_config['models']
                if 'orchestrator_id' in models_config:
                    settings_instance.ORCHESTRATOR_MODEL_ID = (
                        models_config['orchestrator_id']
                    )
                if 'search_id' in models_config:
                    settings_instance.SEARCH_MODEL_NAME = (
                        models_config['search_id']
                    )
                if 'reranker_type' in models_config:
                    settings_instance.RERANKER_TYPE = (
                        models_config['reranker_type']
                    )

            # Update tools configuration
            if 'tools' in toml_config:
                tools_config = toml_config['tools']
                if 'hub_collections' in tools_config:
                    settings_instance.TOOLS_HUB_COLLECTIONS = (
                        tools_config['hub_collections']
                    )
                if 'trust_remote_code' in tools_config:
                    settings_instance.TOOLS_TRUST_REMOTE_CODE = (
                        tools_config['trust_remote_code']
                    )
                if 'mcp_servers' in tools_config:
                    settings_instance.TOOLS_MCP_SERVERS = (
                        tools_config['mcp_servers']
                    )
                if 'specific' in tools_config:
                    settings_instance.TOOLS_SPECIFIC_CONFIG = (
                        tools_config['specific']
                    )

            # Update agent common configuration
            if 'agents' in toml_config and 'common' in toml_config['agents']:
                common_config = toml_config['agents']['common']
                if 'verbose_tool_callbacks' in common_config:
                    settings_instance.VERBOSE_TOOL_CALLBACKS = (
                        common_config['verbose_tool_callbacks']
                    )

            # Update React agent configuration
            if 'agents' in toml_config and 'react' in toml_config['agents']:
                react_config = toml_config['agents']['react']
                if 'max_steps' in react_config:
                    settings_instance.REACT_MAX_STEPS = (
                        react_config['max_steps']
                    )
                if 'planning_interval' in react_config:
                    settings_instance.REACT_PLANNING_INTERVAL = (
                        react_config['planning_interval']
                    )
                if 'max_tool_threads' in react_config:
                    settings_instance.REACT_MAX_TOOL_THREADS = (
                        react_config['max_tool_threads']
                    )

            # Update CodeAct agent configuration
            if 'agents' in toml_config and 'codact' in toml_config['agents']:
                codact_config = toml_config['agents']['codact']
                if 'executor_type' in codact_config:
                    settings_instance.CODACT_EXECUTOR_TYPE = (
                        codact_config['executor_type']
                    )
                if 'max_steps' in codact_config:
                    settings_instance.CODACT_MAX_STEPS = (
                        codact_config['max_steps']
                    )
                if 'verbosity_level' in codact_config:
                    settings_instance.CODACT_VERBOSITY_LEVEL = (
                        codact_config['verbosity_level']
                    )
                if 'planning_interval' in codact_config:
                    settings_instance.CODACT_PLANNING_INTERVAL = (
                        codact_config['planning_interval']
                    )
                if 'executor_kwargs' in codact_config:
                    settings_instance.CODACT_EXECUTOR_KWARGS = (
                        codact_config['executor_kwargs']
                    )
                if 'additional_authorized_imports' in codact_config:
                    settings_instance.CODACT_ADDITIONAL_IMPORTS = (
                        codact_config['additional_authorized_imports']
                    )
                if 'use_structured_outputs' in codact_config:
                    settings_instance.CODACT_USE_STRUCTURED_OUTPUTS = (
                        codact_config['use_structured_outputs']
                    )

            # Update managed agents configuration
            if 'agents' in toml_config and 'manager' in toml_config['agents']:
                manager_config = toml_config['agents']['manager']
                if 'enabled' in manager_config:
                    settings_instance.MANAGED_AGENTS_ENABLED = (
                        manager_config['enabled']
                    )
                if 'max_delegation_depth' in manager_config:
                    settings_instance.MAX_DELEGATION_DEPTH = (
                        manager_config['max_delegation_depth']
                    )
                if 'default_managed_agents' in manager_config:
                    settings_instance.DEFAULT_MANAGED_AGENTS = (
                        manager_config['default_managed_agents']
                    )

            # Update logging configuration
            if 'logging' in toml_config:
                logging_config = toml_config['logging']
                if 'litellm_level' in logging_config:
                    settings_instance.LOGGING_LITELLM_LEVEL = (
                        logging_config['litellm_level']
                    )
                if 'filter_repeated_logs' in logging_config:
                    settings_instance.LOGGING_FILTER_REPEATED_LOGS = (
                        logging_config['filter_repeated_logs']
                    )
                if 'filter_cost_calculator' in logging_config:
                    settings_instance.LOGGING_FILTER_COST_CALCULATOR = (
                        logging_config['filter_cost_calculator']
                    )
                if 'filter_token_counter' in logging_config:
                    settings_instance.LOGGING_FILTER_TOKEN_COUNTER = (
                        logging_config['filter_token_counter']
                    )
                if 'format' in logging_config:
                    settings_instance.LOGGING_FORMAT = logging_config['format']
                if 'enable_token_counting' in logging_config:
                    settings_instance.ENABLE_TOKEN_COUNTING = (
                        logging_config['enable_token_counting']
                    )
                if 'log_tokens' in logging_config:
                    settings_instance.LOG_TOKENS = (
                        logging_config['log_tokens']
                    )

            # Update model list
            if 'model_list' in toml_config:
                settings_instance.MODEL_LIST = toml_config['model_list']

            logger.info(
                f"Successfully loaded TOML configuration from '{config_path}'"
            )
        except Exception as e:
            logger.error(f"Error loading TOML configuration: {e}")
    else:
        logger.warning(
            f"Configuration file '{config_path}' does not exist, "
            "using default configuration"
        )

    # Allow environment variables to override TOML configuration
    if os.getenv("DEEPSEARCH_AGENT_MODE"):
        settings_instance.DEEPSEARCH_AGENT_MODE = (
            os.getenv("DEEPSEARCH_AGENT_MODE")
        )
    if os.getenv("ORCHESTRATOR_MODEL_ID"):
        settings_instance.ORCHESTRATOR_MODEL_ID = (
            os.getenv("ORCHESTRATOR_MODEL_ID")
        )
    if os.getenv("SEARCH_MODEL_NAME"):
        settings_instance.SEARCH_MODEL_NAME = (
            os.getenv("SEARCH_MODEL_NAME")
        )

    # Allow environment variables for Hugging Face token
    if os.getenv("HF_TOKEN"):
        settings_instance.hf_token = os.getenv("HF_TOKEN")

    return settings_instance


# Create a singleton settings instance
settings = load_toml_config(Settings())
