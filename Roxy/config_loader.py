"""Configuration loader with environment variable substitution."""

import os
import re
import yaml
import logging
from typing import Any, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and parse configuration with environment variable substitution."""

    def __init__(self, config_path: str):
        """
        Initialize config loader.

        Args:
            config_path: Path to YAML config file
        """
        self.config_path = config_path
        self.config = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            raw_config = f.read()

        # Substitute environment variables
        config_str = self._substitute_env_vars(raw_config)

        # Parse YAML
        self.config = yaml.safe_load(config_str)

        # Validate required fields
        self._validate_config()

        logger.info(f"Configuration loaded from {self.config_path}")
        return self.config

    def _substitute_env_vars(self, text: str) -> str:
        """
        Substitute ${VAR_NAME} with environment variables.

        Args:
            text: Text containing variable placeholders

        Returns:
            Text with variables substituted
        """
        pattern = re.compile(r'\$\{([^}]+)\}')

        def replacer(match):
            var_name = match.group(1)
            default = None

            # Support ${VAR:-default} syntax
            if ':-' in var_name:
                var_name, default = var_name.split(':-', 1)

            value = os.getenv(var_name, default)

            if value is None:
                logger.warning(f"Environment variable not set: {var_name}")
                return match.group(0)  # Leave unchanged

            return value

        return pattern.sub(replacer, text)

    def _validate_config(self):
        """Validate required configuration fields."""
        if not self.config:
            raise ValueError("Configuration is empty")

        # Check for cameras
        if 'cameras' not in self.config or not self.config['cameras']:
            raise ValueError("No cameras configured")

        # Check for LLM config
        if 'llm' not in self.config:
            raise ValueError("LLM configuration missing")

        if not self.config['llm'].get('api_key'):
            raise ValueError("LLM API key not configured")

        # Check for analyzers
        if 'analyzers' not in self.config or not self.config['analyzers']:
            logger.warning("No analyzers configured")

        logger.info("Configuration validation passed")

    def get_camera_configs(self) -> Dict[str, str]:
        """Get camera configurations as {camera_id: rtsp_url}."""
        cameras = {}
        for camera_id, config in self.config.get('cameras', {}).items():
            if config.get('enabled', True):
                cameras[camera_id] = config['url']
        return cameras

    def get_camera_locations(self) -> Dict[str, str]:
        """Get camera locations as {camera_id: location}."""
        locations = {}
        for camera_id, config in self.config.get('cameras', {}).items():
            if config.get('enabled', True):
                locations[camera_id] = config.get('location', camera_id)
        return locations

    def get_motion_config(self) -> Dict[str, Any]:
        """Get motion detection configuration."""
        return self.config.get('motion_detection', {
            'threshold': 1000,
            'window_minutes': 10
        })

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.config.get('llm', {})

    def get_analyzer_configs(self) -> list:
        """Get analyzer configurations."""
        return self.config.get('analyzers', [])

    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return self.config.get('notifications', {})

    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return self.config.get('processing', {'fps': 1})

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config.get('logging', {
            'level': 'INFO',
            'save_alert_images': True,
            'alert_image_directory': './alerts'
        })


def load_config(config_path: str = "config_advanced.yaml") -> Dict[str, Any]:
    """
    Load configuration from file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader(config_path)
    return loader.load()
