import os
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_CONFIG_PATH = "config.yaml"


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load YAML config file and .env file.

    Args:
        config_path: Optional path to YAML config file.
                     If not provided, will attempt to load ./config.yaml.

    Returns:
        Dictionary containing merged configuration.
    """
    load_dotenv()
    logger.info("Loaded .env file (if exists).")
    actual_config_path = config_path or os.getenv(
        "CONFIG_FILE_PATH", DEFAULT_CONFIG_PATH
    )
    logger.info(
        f"Attempting to load YAML config from '{actual_config_path}'..."
    )
    yaml_config = {}
    try:
        with open(actual_config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        if not isinstance(yaml_config, dict):
            logger.warning(
                f"YAML file '{actual_config_path}' does not contain a valid "
                f"dictionary structure, using empty config."
            )
            yaml_config = {}
        else:
            logger.info(
                f"Successfully loaded YAML config from '{actual_config_path}'."
            )
    except FileNotFoundError:
        logger.warning(
            f"YAML config file '{actual_config_path}' not found, "
            f"using default values or environment variables."
        )
    except yaml.YAMLError as e:
        logger.error(
            f"Error parsing YAML file '{actual_config_path}': {e}, "
            f"using empty config."
        )

    # Prepare final config dictionary (currently only contains YAML content,
    # will get specific values through functions later)
    # Return loaded YAML config directly, API Keys will be fetched on demand
    final_config = yaml_config if yaml_config else {}

    # --- Add validation logic to ensure key sections exist ---
    if 'service' not in final_config:
        logger.warning(
            "YAML config is missing 'service' section, using default."
        )
        final_config['service'] = {}
    if 'models' not in final_config:
        logger.warning(
            "YAML config is missing 'models' section, using default."
        )
        final_config['models'] = {}
    if 'agents' not in final_config:
        logger.warning(
            "YAML config is missing 'agents' section, using default."
        )
        final_config['agents'] = {'common': {}, 'codact': {}, 'react': {}}
    if 'common' not in final_config['agents']:
        final_config['agents']['common'] = {}
    if 'codact' not in final_config['agents']:
        final_config['agents']['codact'] = {}
    if 'react' not in final_config['agents']:
        final_config['agents']['react'] = {}

    return final_config


# --- Helper function to safely get values from config dictionary,
#     providing default values if keys are not found ---
def get_config_value(
    config: Dict[str, Any], key_path: str, default: Any = None
) -> Any:
    """Get config value from nested dictionary safely, providing default
    values if keys are not found.

    Args:
        config: Config dictionary (from load_config).
        key_path: Dot-separated key path (e.g. 'service.port').
        default: Default value to return if key is not found.

    Returns:
        Found config value or default value.
    """
    keys = key_path.split('.')
    value = config
    try:
        for key in keys:
            if isinstance(value, dict):
                value = value[key]
            else:
                return default
        return value
    except KeyError:
        return default
    except Exception as e:
        logger.warning(f"Error getting config '{key_path}': {e}")
        return default


# Load config once, for other modules to import
# Note: This ensures config is loaded once at application startup
# If dynamic reloading is needed, a different mechanism is required
APP_CONFIG = load_config()


# --- Functions to directly access API Keys
# (still read from environment variables) ---
def get_api_key(key_name: str) -> Optional[str]:
    """Get API key from environment variables."""
    return os.getenv(key_name)
