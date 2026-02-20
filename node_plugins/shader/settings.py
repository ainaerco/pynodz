"""Shader settings persistence.

Manages shader-specific settings (pins, output types, defaults).
Settings are stored in shader_settings.json with migration from
legacy arnold_settings.json.
"""

import json
import os
from typing import Any

SETTINGS_PATH = "shader_settings.json"
LEGACY_PATH = "arnold_settings.json"

_settings: dict[str, Any] = {}


def load() -> dict[str, Any]:
    """Load shader settings from file.

    Migrates from legacy arnold_settings.json if shader_settings.json
    doesn't exist.
    """
    global _settings

    if os.path.isfile(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            _settings = json.load(f)
    elif os.path.isfile(LEGACY_PATH):
        with open(LEGACY_PATH, "r", encoding="utf-8") as f:
            _settings = json.load(f)
        save()
    else:
        _settings = {}

    return _settings


def save() -> None:
    """Save shader settings to file."""
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(_settings, sort_keys=False, indent=4, fp=f)


def get() -> dict[str, Any]:
    """Get current shader settings dict."""
    return _settings


def set_settings(value: dict[str, Any]) -> None:
    """Set shader settings dict."""
    global _settings
    _settings = value


def get_shader_setting(shader: str, attr: str | None = None) -> Any:
    """Get a setting for a shader, optionally a specific attribute."""
    if shader not in _settings:
        return None
    if attr is None:
        return _settings[shader]
    if attr not in _settings[shader]:
        return None
    return _settings[shader][attr]


def set_shader_setting(shader: str, attr: str, value: Any) -> None:
    """Set a setting for a shader attribute."""
    if shader not in _settings:
        _settings[shader] = {}
    _settings[shader][attr] = value
