"""Shader plugin for pynodz.

Provides NodeShader node type and Arnold/demo shader integration.
"""

from typing import Any

from .. import register_node_type, register_plugin
from .node_shader import NodeShader
from .shaders import get_shaders, get_demo_shaders, load_context

register_node_type("NodeShader", NodeShader)
register_plugin("shader", "shader")


def get_plugin_shaders() -> dict[str, Any]:
    """Get shader definitions from this plugin."""
    return get_shaders()


__all__ = [
    "NodeShader",
    "get_shaders",
    "get_demo_shaders",
    "get_plugin_shaders",
    "load_context",
]
