# AI Driven Highspeed Development Framework Module — Config Manager

## Overview
A singleton JSON configuration system with automatic code generation. On initialization, it reads `./.config`, generates strongly-typed access classes, and exposes `cm.config` for type-safe reads. Supports runtime load/save with regeneration of key classes.

## Capabilities
- Auto-generates config key classes from JSON on initialization
- Singleton pattern (single application instance)
- Type-safe config access via generated dataclasses
- Automatic nested structure handling (arbitrary depth)
- Runtime config loading and saving with regeneration
- Works from current working directory as project root

## Components
### ConfigManager
Responsible for loading, generating, and exposing strongly-typed configuration accessors.
- Ensures `.config` exists (creates if missing)
- Loads JSON into memory as `raw_config`
- Invokes `ConfigKeysGenerator.generate()` to emit `config_keys.py`
- Instantiates `ConfigKeys` and exposes it as `cm.config`
- On `save_config()`, updates the JSON file and regenerates classes

### ConfigTemplate
Discovers module templates and consolidates them into a single project configuration.
- Discovery: Scans modules and locates `.config_template` files
- Load: Reads JSON templates
- Consolidate: Builds a single dictionary keyed by module name
- Merge: Preserves existing values by default (`preserve_existing=True`)
- Backup: Creates `.config.backup` before overwriting
- Save: Writes the consolidated configuration to `./.config`
- CLI: Refresh via `python adhd_cli.py refresh config_manager`

Example (programmatic generation):
```python
from managers.config_manager import ConfigTemplate

ct = ConfigTemplate()  # optionally pass a custom path
ct.generate_config(preserve_existing=True)
ct.list_config_summary()
```

## Lifecycle (How It Works)
1. First construction `ConfigManager(config_path='.config')`:
   - Ensures `.config` exists
   - Loads JSON into memory as `raw_config`
   - Generates `config_keys.py` and instantiates `cm.config`
2. Save/update: `cm.save_config({...})` persists changes and regenerates keys

Generated classes use nested dataclasses and optional lists to mirror your JSON structure. Class names are synthesized from keys, with first-level suffix rules for Plugin/Util/Manager.

## Quick Start
```python
from managers.config_manager.config_manager import ConfigManager

# Initialize (singleton)
cm = ConfigManager(config_path='.config', verbose=True)

# Access values (type-safe)
host = cm.config.database.host
port = cm.config.database.port

# Update and persist (regenerates keys)
cm.save_config({"database": {"host": "db.local", "port": 5433}})

# Singleton guarantee
cm1 = ConfigManager()
cm2 = ConfigManager()
assert cm1 is cm2
```

## Examples
### API Usage (code)
```python
from managers.config_manager.config_manager import ConfigManager

# Initialize
cm = ConfigManager(config_path='.config')

# Get a simple value
api_key = cm.config.api_key

# Update nested structure
cm.save_config({"webcam_plugin": {"devices": [{"name": "cam01", "device_id": 0}]}})

# Iterate list items (generated list-of-dicts)
for dev in cm.config.webcam_plugin.devices or []:
    print(dev.name, dev.device_id)
```

### Config JSON (data)
```json
{
  "webcam_plugin": {
    "devices": [
      {"name": "cam01", "device_id": 0},
      {"name": "cam02", "device_id": 1}
    ]
  },
  "yolo_pose_plugin": {
    "model_name": "yolo11x-pose.pt",
    "confidence_threshold": 0.5
  }
}
```

## CLI and Regeneration
- Manual edits to `./.config` require regeneration of `config_keys.py`.
- Do one of:
  1) Reinitialize: `cm = ConfigManager()` (singleton updates)
  2) Use ADHD CLI: `python adhd_cli.py refresh config_manager`

## Module File Layout
- `managers/config_manager/config_manager.py` — Singleton, I/O, generator driver
- `managers/config_manager/config_keys.py` — Generated dataclasses (do not edit manually)
- `managers/config_manager/agent_instruction.md` — This document
- `./.config` — Project JSON config

## Implementation Notes
- Class naming: keys → CamelCase; first layer applies `_P`/`_U`/`_M` if ending with Plugin/Util/Manager
- Lists of dicts generate an item dataclass based on the union schema across items
- Regeneration overwrites `config_keys.py`

## Troubleshooting
- `ImportError` for generated keys: Ensure you instantiated `ConfigManager` at least once to generate `config_keys.py`
- Changes not reflected: Call `cm.save_config(...)` or reinitialize `ConfigManager()`
- JSON parse errors: Validate `.config` is valid JSON
- Path issues in embedded environments: Module uses `os.getcwd()` as project root and adjusts `sys.path` accordingly

## Warnings
- Regeneration overwrites `config_keys.py`. Do not manually edit it
- Manual `.config` edits require refresh as described above to keep classes in sync

## Related Files
- `.config` — Main configuration file at project root

## Versioning & Maintenance
- Intended to remain backward compatible for JSON structures; breaking changes only if `.config` layout fundamentally changes
- Keep this document updated when adding generator rules