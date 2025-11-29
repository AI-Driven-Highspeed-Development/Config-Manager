---
applyTo: "project/**/*.py,managers/**/*.py,plugins/**/*.py,utils/**/*.py,mcps/**/*.py,cores/**/*.py,*.py"
---

Config Manager:
- Purpose: Centralized config management for ADHD framework projects, structured access and modification for module settings.
- Usage:
```python
from managers.config_manager import ConfigManager

cm = ConfigManager()
config = cm.config.my_module_name
data_path = config.paths.data
dict_value = config.dict_get('some_key')
```
- NEVER modify ConfigKeys directly; ConfigKeys are auto-generated from .config files.
- Therefore, no need to worry non-existent attributes when editing codes for future config keys.
- NEVER use getattr/setattr to access config attributes; use dot notation instead (e.g., `config.my_key`), or for key-value retrieval, use `config.dict_get('my_key')`.
- Update config: run `python adhd_framework.py refresh --module config-manager` to regenerate code after modifying .config, can omit `--module` to refresh all for convenience, remind user for manually sync instead of done by AI agent.
- <module_type>/<module_name>/.config_template: defines default config schema auto-generated into .config on module init. refresh after edits will not overwrite user changes to prevent data loss, manual sync to .config before refresh maybe needed.