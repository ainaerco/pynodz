# Agent guide — pynodz

This file gives AI agents enough context to edit the codebase safely.

## What this project is

- **pynodz** is a node-based editor: canvas, nodes, connections, attributes, undo/redo.
- **Stack**: Python 3.12+, QtPy (PyQt6), Qt Widgets + Graphics View.
- **Entry point**: `main.py` → `NodeDialog()`; scene is `Scene`/`View` with `QGraphicsScene`/`QGraphicsView`.

## Codebase map (where to edit what)

| Goal | Primary files |
|------|----------------|
| New node type (core) | `node_types/node*.py`, then register in `node_utils.get_node_class` and `node_types/__init__.py` |
| New node type (plugin) | `node_plugins/<plugin>/node_*.py`, register via `register_node_type()` in plugin `__init__.py` |
| New attribute widget (e.g. new type in UI) | `node_attrs.py`: add class, then `getAttrByType` / `getAttrDefault` |
| Connection behavior / drawing | `node_parts/connection.py` |
| Node chrome (title, inputs, resize, dropdown) | `node_parts/parts.py` |
| Undo/redo for an action | `node_command.py`: new `QUndoCommand` subclass, push on `node_utils.options.undoStack` |
| Main window, menus, options, scene/view behavior | `main.py` (`NodeDialog`, `Scene`, `View`) |
| Global options, node registry, undo stack | `node_utils.py` (`NodesOptions`) |
| Node data (dict keys, defaults) | `node_types/node.py` `init()`, and shader defs if using NodeShader |
| Plugin system | `node_plugins/__init__.py` — registry for node types and plugins |

## Conventions

- **uv**: Use **uv** for all Python and test execution. Do not run `python` or `pytest` directly; use `uv run python ...` and `uv run pytest` (e.g. `uv run python main.py`, `uv run pytest`).
- **Qt**: Use `qtpy` (not `PyQt6`/`PySide2` directly) so the backend can be switched.
- **Node data**: Nodes are built from a dict `d` (e.g. `id`, `display_name`, `rect`, `rgb`, `collapsed`, `width`, `height`). Persistence is YAML/JSON; don't assume a DB.
- **Singleton options**: `node_utils.options` holds selected nodes, undo stack, node radius, etc. Use it for global state. Shader-specific settings are in `node_plugins/shader/settings.py`.
- **Imports**: `node_attrs` is large; plugins may import it. To avoid circular imports, use late imports or keep imports one-way where possible.
- **Style**: Ruff line-length 80; type hints used in places (e.g. `node_command.py`).

### Naming Conventions

| Element | Convention | Examples |
|---------|-----------|----------|
| **Classes** | PascalCase | `NodeDialog`, `NodeAttrFloat`, `Connection` |
| **Functions/Methods** | camelCase | `get_node_class`, `normalizeName`, `setRect` |
| **Variables** | camelCase | `filterString`, `nodeRadius`, `displayName` |
| **Private attributes** | `_leadingUnderscore` | `_attrParent`, `_isNodeShader` |
| **Module files** | camelCase | `node_utils.py`, `nodeShader.py`, `connection.py` |
| **Constants** | UPPER_CASE | `RECENT_FILES_COUNT` |

## Important patterns

- **Creating nodes**: Use `CommandCreateNode` (and optionally `CommandCreateConnection`); push onto `node_utils.options.undoStack`.
- **Node class from type name**: `node_utils.get_node_class(typ)` returns the class (e.g. `NodeShader`, `NodeGroup`).
- **Attribute type → widget**: `node_attrs.getAttrByType(typ)` / `getAttrDefault(typ)`; extend both when adding a new attribute kind.
- **Drag/drop**: `NodeMimeData` in `node_utils`; scene uses `Scene.dragEnterEvent` / `dragMoveEvent` / `dropEvent` and forwards to items that `acceptDrops()`.
- **Icons**: Use Qt Awesome (Font Awesome 6) via `node_utils.options.getAwesomeIcon(name)` or `getAwesomePixmap(name, size)` for icons. The `getIcon(path)` method is for custom user-loaded icons only.

## Optional / external

- **Arnold**: `parseArnold.getArnoldShaders()` — integrated via `node_plugins/shader/shaders.py`; only if the module exists.
- **Rez**: `rezContext.load_context(filename)` — same idea; integrated via shader plugin.
- **Images**: `images.imageDialog.PreviewFileDialog` or fallback `QFileDialog`.
- **Geometry**: `_geometry.getBarycentric`, `Vector`, `Ray` — optional.

## Plugin system

The shader functionality is extracted into a plugin at `node_plugins/shader/`. This allows it to be deprecated or made optional later.

### Structure

```
node_plugins/
├── __init__.py          # Plugin registry (register_node_type, get_node_type)
└── shader/
    ├── __init__.py      # Plugin entry point, registers NodeShader
    ├── node_shader.py   # NodeShader class
    ├── shaders.py       # Demo shaders, Arnold/Rez loaders
    └── settings.py      # Shader settings persistence (shader_settings.json)
```

### Creating a new plugin

1. Create `node_plugins/<name>/__init__.py`
2. Import and call `register_node_type("NodeX", NodeX)` 
3. Import the plugin in `main.py` to activate it

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

When adding features, prefer extending existing `Node*` and `NodeAttr*` classes and adding undo commands in `node_command.py`; avoid adding new global singletons beyond `node_utils.options`.

## Icons (Qt Awesome)

The project uses **Qt Awesome** (Font Awesome 6) for icons instead of PNG files.

### Available Icon Prefixes

| Prefix | Description | Example |
|--------|-------------|---------|
| `fa6` | Font Awesome 6 Regular | `fa6.flag` |
| `fa6s` | Font Awesome 6 Solid | `fa6s.flag` |
| `fa6b` | Font Awesome 6 Brands | `fa6b.github` |
| `mdi` | Material Design Icons | `mdi.home` |
| `ph` | Phosphor | `ph.house` |
| `ri` | Remix Icon | `ri.home-line` |
| `msc` | Microsoft Codicons | `msc.github` |

### Usage

```python
# For buttons and actions (returns QIcon)
icon = node_utils.options.getAwesomeIcon("fa6s.folder-open")

# For graphics items (returns QPixmap)
pixmap = node_utils.options.getAwesomePixmap("fa6s.file", 18)

# With custom color
icon = node_utils.options.getAwesomeIcon("fa6s.palette", color=QColor("red"))
```

### Finding Icons

- Run `uv run qta-browser` to open the icon browser
- Browse online at https://fontawesome.com/icons

### Legacy

- `getIcon(path)` in `node_utils.py` - Still works for custom user icons (e.g., NodeBookmark)
- Keep PNG files in `resources/icons/` only for special cases (e.g., `grid.png`, `transparent_small.png`)
