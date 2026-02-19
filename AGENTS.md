# Agent guide — pynodz

This file gives AI agents enough context to edit the codebase safely.

## What this project is

- **pynodz** is a node-based editor: canvas, nodes, connections, attributes, undo/redo.
- **Stack**: Python 3.12+, QtPy (PyQt6), Qt Widgets + Graphics View.
- **Entry point**: `main.py` → `NodeDialog()`; scene is `Scene`/`View` with `QGraphicsScene`/`QGraphicsView`.

## Codebase map (where to edit what)

| Goal | Primary files |
|------|----------------|
| New node type | `nodeTypes/Node*.py`, then register in `nodeUtils.getNodeClass` and `nodeTypes/__init__.py` |
| New attribute widget (e.g. new type in UI) | `nodeAttrs.py`: add class, then `getAttrByType` / `getAttrDefault` |
| Connection behavior / drawing | `nodeParts/Connection.py` |
| Node chrome (title, inputs, resize, dropdown) | `nodeParts/Parts.py` |
| Undo/redo for an action | `nodeCommand.py`: new `QUndoCommand` subclass, push on `nodeUtils.options.undoStack` |
| Main window, menus, options, scene/view behavior | `main.py` (`NodeDialog`, `Scene`, `View`) |
| Global options, node registry, undo stack | `nodeUtils.py` (`NodesOptions`) |
| Node data (dict keys, defaults) | `nodeTypes/Node.py` `init()`, and shader defs if using NodeShader |

## Conventions

- **uv**: Use **uv** for all Python and test execution. Do not run `python` or `pytest` directly; use `uv run python ...` and `uv run pytest` (e.g. `uv run python main.py`, `uv run pytest`).
- **Qt**: Use `qtpy` (not `PyQt6`/`PySide2` directly) so the backend can be switched.
- **Node data**: Nodes are built from a dict `d` (e.g. `id`, `display_name`, `rect`, `rgb`, `collapsed`, `width`, `height`). Persistence is YAML/JSON; don’t assume a DB.
- **Singleton options**: `nodeUtils.options` holds selected nodes, undo stack, node radius, arnold defaults, etc. Use it for global state.
- **Imports**: `nodeAttrs` is large; `nodeTypes.NodeShader` imports it. To avoid circular imports, use late imports (e.g. `_is_node_shader` in `nodeAttrs`) or keep `nodeTypes` → `nodeAttrs` one-way where possible.
- **Style**: Ruff line-length 80; type hints used in places (e.g. `nodeCommand.py`).

## Important patterns

- **Creating nodes**: Use `CommandCreateNode` (and optionally `CommandCreateConnection`); push onto `nodeUtils.options.undoStack`.
- **Node class from type name**: `nodeUtils.getNodeClass(typ)` returns the class (e.g. `NodeShader`, `NodeGroup`).
- **Attribute type → widget**: `nodeAttrs.getAttrByType(typ)` / `getAttrDefault(typ)`; extend both when adding a new attribute kind.
- **Drag/drop**: `NodeMimeData` in `nodeUtils`; scene uses `Scene.dragEnterEvent` / `dragMoveEvent` / `dropEvent` and forwards to items that `acceptDrops()`.

## Optional / external

- **Arnold**: `parseArnold.getArnoldShaders()` — only if the module exists; otherwise stub returns `{}`.
- **Rez**: `rezContext.loadContext(filename)` — same idea; stub returns `{}`.
- **Images**: `images.imageDialog.PreviewFileDialog` or fallback `QFileDialog`.
- **Geometry**: `_geometry.getBarycentric`, `Vector`, `Ray` — optional.

## Tests

- **Location**: `tests/` (pytest; `test_qt.py`, `test_nodeUtils.py`).
- **Run**: `uv run pytest` from project root (do not call `pytest` directly).
- **GUI tests**: pytest-qt for Qt-related tests.

## After making changes

After editing code, the agent **must** confirm that format check passes:

```bash
uv run ruff format --check
```

If it fails, fix formatting (e.g. run `uv run ruff format` to apply, then re-run the check).

When adding features, prefer extending existing `Node*` and `NodeAttr*` classes and adding undo commands in `nodeCommand.py`; avoid adding new global singletons beyond `nodeUtils.options`.
