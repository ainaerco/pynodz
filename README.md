# pynodz

A node-based editor built with Qt. Create, connect, and edit nodes on a canvas with support for shader-style attributes, undo/redo, and optional Arnold shader integration.

## Requirements

- Python ≥ 3.12
- Qt (PyQt6 via QtPy)

## Setup

Use **uv** for the environment and running.

```bash
# From project root
uv sync
```

## Run

```bash
uv run python main.py
```

Opens the node editor window (`NodeDialog`): scene with nodes, connections, context menus, and options (proxy, node radius, background brightness).

## Project structure

| Path | Purpose |
|------|--------|
| `main.py` | Entry point, `NodeDialog`, `Scene`, `View`, menus, options dialog |
| `nodeUtils.py` | `NodesOptions`, `NodeMimeData`, helpers: `getNodeClass`, `normalizeName`, `incrementName`, `listRemove`, `mergeDicts` |
| `nodeAttrs.py` | Attribute widgets: Bool, Float, Int, Enum, RGB/RGBA, Vector, Matrix, String, Spline, Ramp, Array, Image, Panel; `getAttrByType`, `getAttrDefault` |
| `nodeCommand.py` | Undo commands: move node, animated move, set attribute, set color, create/delete node, create/delete connection |
| `nodeTypes/` | Node classes: `Node`, `NodeShader`, `NodeGroup`, `NodeBookmark`, `NodeBlock`, `NodeControl`, `NodeGraph`, `NodeNote` |
| `nodeParts/` | `Connection`, `Parts` (TitleItem, NodeInput, NodeResize, DropDown) |
| `bezier.py` | Bezier/spline helpers |
| `htmlEditor.py` | HTML editing for node content |
| `tests/` | Pytest tests (`test_qt.py`, `test_nodeUtils.py`) |

## Node types

- **Node** — Base node (title, connector, resize, dropdown, color).
- **NodeShader** — Shader node with attribute panels; integrates with optional Arnold shader definitions.
- **NodeGroup** — Group container.
- **NodeBookmark** — Bookmark node.
- **NodeBlock** — Block node.
- **NodeControl** — Control node.
- **NodeGraph** — Graph node.
- **NodeNote** — Note node.

Node data is dict-based (`id`, `display_name`, `rect`, `rgb`, `collapsed`, `width`, `height`, etc.). Shader nodes use `shader` and `attributes` from the dialog’s shader definitions.

## Tech stack

- **GUI**: QtPy (PyQt6), Qt Widgets + Graphics View (`QGraphicsScene`, `QGraphicsView`, `QGraphicsWidget`).
- **Data**: YAML/JSON for scenes; optional `parseArnold` and `rezContext` for Arnold/Rez integration.
- **Testing**: pytest, pytest-qt.
- **Linting**: ruff (line-length 80), pyright.

## Optional modules

- `parseArnold` — `getArnoldShaders()`; provide to enable Arnold shader nodes.
- `rezContext` — `loadContext(filename)`; provide for Rez context loading.
- `images.imageDialog` — `PreviewFileDialog`; fallback is `QFileDialog`.
- `_geometry` — `getBarycentric`, `Vector`, `Ray` for geometry helpers.

## Tests

```bash
uv run pytest
```

## License

See repository or project metadata.
