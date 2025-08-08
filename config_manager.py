import json
import os
import logging
import sys
from typing import Any, Dict, List

# Add path handling to work from the new nested directory structure
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()  # Use current working directory as project root
sys.path.insert(0, project_root)

from utils.logger_util.logger import get_logger

# Run this file once to generate config keys
# Run this file again if you changed the .config file

class ConfigManager:
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of ConfigManager exists."""
        if not hasattr(cls, 'instance'):
            cls.instance = super(ConfigManager, cls).__new__(cls)
        return cls.instance

    def __init__(self, config_path: str = '.config', verbose: bool = False):
    
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Use centralized logger instead of internal setup
        self.logger = get_logger("ConfigManager", verbose=verbose)
        self.config_path = config_path
        self.verbose = verbose
        
        self.logger.debug("Initializing ConfigManager...")
        if not os.path.exists(self.config_path):
            self.logger.debug("Configuration file not found, creating a new one.")
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as file:
                file.write('{}')
                    
        self.raw_config = {}           
        self._load_config(self.config_path)
        self.ckg = ConfigKeysGenerator(self.raw_config)
        self.ckg.generate()
        
        from managers.config_manager.config_keys import ConfigKeys
        self.config = ConfigKeys()

    @staticmethod
    def _init_nested_item(item_instance, item_data):
        """Recursively initialize nested item with data."""
        for field_name, field_value in item_data.items():
            if hasattr(item_instance, field_name):
                if isinstance(field_value, dict):
                    # Handle nested dict - create nested class instance
                    nested_class = getattr(item_instance, f'{field_name}_class', None)
                    if nested_class:
                        nested_instance = nested_class()
                        for nested_key, nested_value in field_value.items():
                            if hasattr(nested_instance, nested_key):
                                setattr(nested_instance, nested_key, nested_value)
                        setattr(item_instance, field_name, nested_instance)
                else:
                    # Handle simple field
                    setattr(item_instance, field_name, field_value)

    def _load_config(self, config_path):
        """Load configuration from a file."""
        try:
            with open(config_path, 'r') as file:
                config_str = file.read()
                if not config_str.strip():
                    self.logger.debug("Configuration file is empty, initializing with an empty config.")
                self.raw_config = json.loads(config_str) if config_str else {}
            self.logger.debug("Configuration loaded successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred while loading the configuration: {e}")
        
    def save_config(self, key_value: Dict[str, Any] = None):
        """Save the current configuration to a file."""
        if key_value:
            self.raw_config.update(key_value)
        try:
            with open(self.config_path, 'w') as file:
                json.dump(self.raw_config, file, indent=2)
            self.logger.debug("Configuration saved successfully.")
            self.ckg.generate()  # Regenerate config keys after saving
        except Exception as e:
            self.logger.error(f"An error occurred while saving the configuration: {e}")

        
class ConfigKeysGenerator:
    """Generates configuration keys from the current raw configuration (arbitrary depth)."""
    
    def __init__(self, raw_config: Dict[str, Any] = None):
        self.raw_config = raw_config or {}
        # Track emitted classes to avoid duplicates (use fully-qualified names)
        self._emitted: set[str] = set()
    
    def generate(self):
        header = (
            "from dataclasses import dataclass\n"
            "from typing import List, Optional, Dict, Any\n"
            "from managers.config_manager.config_manager import ConfigManager\n\n"
        )
        body = self._emit_class(
            class_name="ConfigKeys",
            node=self.raw_config,
            indent_count=0,
            path=["ConfigKeys"],
            is_root=True,
            parents=[],
        )
        out = header + body
        config_keys_path = os.path.join(current_dir, 'config_keys.py')
        os.makedirs(os.path.dirname(config_keys_path), exist_ok=True)
        with open(config_keys_path, 'w') as f:
            f.write(out)
    
    # ---------------- Internal helpers ----------------
    def _tokenize(self, s: str) -> List[str]:
        return ["".join(ch for ch in p if ch.isalnum()).lower() for p in s.replace('-', '_').split('_') if p]

    def _to_camel(self, s: str) -> str:
        """Convert tokens to full CamelCase without truncation."""
        parts = self._tokenize(s)
        if not parts:
            return s.capitalize()
        chunks: List[str] = []
        for p in parts:
            if p.isdigit():
                chunks.append(p)
            else:
                chunks.append(p.capitalize())
        return ''.join(chunks)

    def _apply_first_layer_suffix(self, base: str) -> str:
        # Replace trailing Plugin/Util/Manager with _P/_U/_M
        if base.endswith('Plugin'):
            return base[:-len('Plugin')] + '_P'
        if base.endswith('Util'):
            return base[:-len('Util')] + '_U'
        if base.endswith('Manager'):
            return base[:-len('Manager')] + '_M'
        return base

    def _short_class_name(self, current_class_name: str, key: str, kind: str, used_names: set[str] | None = None, is_first_layer: bool = False) -> str:
        base = self._to_camel(key)
        if kind == 'item':
            base = f"{base}_I"
        elif is_first_layer:
            base = self._apply_first_layer_suffix(base)
        # Ensure doesn't start with digit
        if base and base[0].isdigit():
            base = "C_" + base
        # Ensure uniqueness among siblings
        if used_names is not None:
            name = base
            n = 2
            while name in used_names:
                name = f"{base}{n}"
                n += 1
            used_names.add(name)
            return name
        return base
    
    def _is_list_of_dicts(self, value: Any) -> bool:
        return isinstance(value, list) and len(value) > 0 and all(isinstance(it, dict) for it in value)
    
    def _union_dict_schema(self, lst: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Merge keys and pick a representative non-None value for type inference
        keys: set[str] = set()
        for it in lst:
            keys.update(it.keys())
        schema: Dict[str, Any] = {}
        for k in keys:
            rep = None
            for it in lst:
                if k in it and it[k] is not None:
                    rep = it[k]
                    break
            schema[k] = rep
        return schema
    
    def _emit_class(self, class_name: str, node: Any, indent_count: int, path: List[str], is_root: bool, parents: List[str] | None = None) -> str:
        if parents is None:
            parents = []
        fqcn = ".".join(parents + [class_name]) if parents else class_name
        # Avoid emitting same class twice (track by fully-qualified name)
        if fqcn in self._emitted:
            return ""
        self._emitted.add(fqcn)
        
        indent = "\t" * indent_count
        out: List[str] = []
        out.append(f"{indent}@dataclass")
        out.append(f"{indent}class {class_name}:")
        
        # Fields
        nested_chunks: List[str] = []
        used_names: set[str] = set()
        if isinstance(node, dict):
            for key, val in node.items():
                is_first_layer = (class_name == 'ConfigKeys')
                if isinstance(val, dict):
                    nested_cls = self._short_class_name(class_name, key, kind='class', used_names=used_names, is_first_layer=is_first_layer)
                    out.append(f"{indent}\t{key}: Optional['{nested_cls}'] = None")
                    nested_chunks.append(self._emit_class(nested_cls, val, indent_count + 1, path + [key], False, parents=parents + [class_name]))
                elif self._is_list_of_dicts(val):
                    item_schema = self._union_dict_schema(val)
                    item_cls = self._short_class_name(class_name, key, kind='item', used_names=used_names, is_first_layer=is_first_layer)
                    out.append(f"{indent}\t{key}: Optional[List['{item_cls}']] = None")
                    nested_chunks.append(self._emit_class(item_cls, item_schema, indent_count + 1, path + [key, "item"], False, parents=parents + [class_name]))
                else:
                    py_type = type(val).__name__ if val is not None else 'Any'
                    if isinstance(val, list):
                        annotated = 'List'
                        default = 'None'
                    elif isinstance(val, dict):
                        annotated = 'Dict'
                        default = 'None'
                    elif isinstance(val, str):
                        annotated = 'str'
                        default = f'"{val}"'
                    else:
                        annotated = py_type
                        default = str(val)
                    out.append(f"{indent}\t{key}: Optional[{annotated}] = {default}")
        else:
            # Non-dict nodes should not happen for a class root; still guard
            out.append(f"{indent}\tpass")
        
        # Methods: from_raw and _populate (recursive construction)
        out.append("")
        out.append(f"{indent}\t@staticmethod")
        out.append(f"{indent}\tdef from_raw(raw: Dict[str, Any] | None) -> '{class_name}':")
        out.append(f"{indent}\t\tinst = {fqcn}()")
        out.append(f"{indent}\t\tinst._populate(raw or {{}})")
        out.append(f"{indent}\t\treturn inst")
        out.append("")
        out.append(f"{indent}\tdef _populate(self, data: Dict[str, Any]):")
        if isinstance(node, dict) and node:
            for key, val in node.items():
                keyq = f"'{key}'"
                is_first_layer = (class_name == 'ConfigKeys')
                if isinstance(val, dict):
                    nested_cls = self._short_class_name(class_name, key, kind='class', is_first_layer=is_first_layer)
                    out.append(f"{indent}\t\tself.{key} = self.{nested_cls}.from_raw(data.get({keyq}, {{}}))")
                elif self._is_list_of_dicts(val):
                    item_cls = self._short_class_name(class_name, key, kind='item', is_first_layer=is_first_layer)
                    out.append(f"{indent}\t\tself.{key} = []")
                    out.append(f"{indent}\t\tfor __it in data.get({keyq}, []):")
                    out.append(f"{indent}\t\t\tself.{key}.append(self.{item_cls}.from_raw(__it))")
                else:
                    out.append(f"{indent}\t\tself.{key} = data.get({keyq}, self.{key})")
        else:
            out.append(f"{indent}\t\tpass")
        
        # Root __init__ auto-populates from embedded literal
        out.append("")
        out.append(f"{indent}\tdef __init__(self):")
        if is_root:
            # Embed literal for root only
            literal = self._literal(node)
            out.append(f"{indent}\t\tself._populate({literal})")
        else:
            out.append(f"{indent}\t\tpass")
        
        # Append nested classes
        out.append("")
        for ch in nested_chunks:
            if ch:
                out.append(ch)
        out.append("")
        return "\n".join(out)
    
    def _literal(self, value: Any) -> str:
        # Safe Python literal for embedding raw_config
        try:
            return repr(value)
        except Exception:
            return 'None'