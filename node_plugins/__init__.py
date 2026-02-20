"""Simple plugin system for node extensions.

Plugins register themselves by importing their module, which calls
register_plugin() with their name and node types.
"""

_node_types: dict[str, type] = {}
_plugin_modules: dict[str, object] = {}


def register_node_type(name: str, cls: type) -> None:
    """Register a node type class."""
    _node_types[name] = cls


def get_node_type(name: str) -> type | None:
    """Get a registered node type by name."""
    return _node_types.get(name)


def get_node_types() -> dict[str, type]:
    """Get all registered node types."""
    return _node_types.copy()


def register_plugin(name: str, module: object) -> None:
    """Register a plugin module."""
    _plugin_modules[name] = module


def get_plugin(name: str) -> object | None:
    """Get a registered plugin module."""
    return _plugin_modules.get(name)
