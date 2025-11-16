# Config Manager

Small, singleton JSON configuration system with automatic code generation for strongly‑typed access. Reads `./.config`, generates key classes, exposes `cm.config`, and supports runtime save/regeneration.

## Overview
- Singleton instance providing project‑wide config access
- Auto‑generates typed accessors from your JSON config
- Load/save at runtime; regenerates key classes on demand
- Discovers module `.config_template` files and consolidates them into a single `.config`

## Features
- Strongly‑typed access
  - Generates nested dataclasses mirroring your JSON
  - Handles lists of dicts with synthesized item dataclasses
  - Also exposes the raw dict for each node via `___DATA___`
- Lifecycle and regeneration
  - Ensures `./.config` exists; creates if missing
  - Regenerates `config_keys.py` on initialization and on `save_config(...)`
- Template consolidation
  - Scans modules for `.config_template` and merges into one file
  - Preserves existing values by default (`preserve_existing=True`)

## Quickstart

```python
from managers.config_manager.config_manager import ConfigManager

# Initialize (singleton)
cm = ConfigManager(config_path='.config', verbose=True)

# Read values (typed access)
some_value = cm.config.section.subsection.leaf

# When you need mapping behavior, use the raw dict or helper
node = cm.config.section
value = node.dict_get("arbitrary_key", default=None)
value2 = node.___DATA___["arbitrary_key"]  # raises KeyError if missing

# Update and persist (regenerates keys)
cm.save_config({"database": {"host": "db.local", "port": 5433}})

# Singleton guarantee
assert ConfigManager() is cm
```

### Generate `.config` from module templates

```python
from managers.config_manager import ConfigTemplate

ct = ConfigTemplate()  # optionally pass a custom path
ct.generate_config(preserve_existing=True)
ct.list_config_summary()
```

## API

```python
class ConfigManager:
    def __init__(self, config_path: str = '.config', verbose: bool = False): ...
    @property
    def config(self): ...  # generated typed accessors root
    def save_config(self, updates: dict) -> None: ...  # persists JSON and regenerates keys

class ConfigTemplate:
    def generate_config(self, preserve_existing: bool = True) -> None: ...
    def list_config_summary(self) -> None: ...
```

## Notes
- Class naming: keys → CamelCase; first‑level keys may append `_P`/`_U`/`_M` suffixes for Plugin/Util/Manager.
- Lists of dicts combine union schemas to derive item shapes.
- Regeneration overwrites `config_keys.py` (don’t edit it manually).
- Dict access: each generated class has `___DATA___: Dict[str, Any]` capturing the raw JSON for direct mapping access.

## Requirements & prerequisites
- Python standard library only for manager logic; generated classes are pure Python.

## Troubleshooting
- Import errors for generated keys: Ensure you initialized `ConfigManager()` at least once.
- Changes not reflected: Call `cm.save_config(...)` or reinitialize `ConfigManager()`.
- JSON parse errors: Confirm `.config` is valid JSON.
- Path issues: The module assumes `os.getcwd()` is your project root.

## Module structure

```
managers/config_manager/
├─ __init__.py             # package exports
├─ config_manager.py       # singleton manager and generation driver
├─ config_template.py      # templates discovery and consolidation
├─ config_keys.py          # generated dataclasses (do not edit)
├─ refresh.py              # CLI hook to refresh/regenerate
├─ init.yaml               # module metadata
└─ README.md               # this file
```

## See also
- YAML Reading Core: parse and validate YAML files you might convert to JSON config
- Logger Utility: standardized logging for config operations
- Temp Files Manager: create temporary workspaces for config generation steps