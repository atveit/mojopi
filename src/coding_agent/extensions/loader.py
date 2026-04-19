import importlib.util
import sys
from pathlib import Path

def load_extension_file(path: str) -> None:
    """Load a single Python extension file by path. Executes the module."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Extension file not found: {path}")
    spec = importlib.util.spec_from_file_location(f"_ext_{p.stem}", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

def load_extensions_dir(directory: str) -> int:
    """Load all .py files from directory. Returns count loaded. Silently skips missing dir."""
    d = Path(directory).expanduser()
    if not d.is_dir():
        return 0
    count = 0
    for f in sorted(d.glob("*.py")):
        try:
            load_extension_file(str(f))
            count += 1
        except Exception as e:
            print(f"[extensions] failed to load {f}: {e}")
    return count

def load_all_extensions(extra: str = "") -> int:
    """Load from global ~/.pi/agent/extensions/, project .pi/extensions/, and extra path."""
    total = 0
    total += load_extensions_dir("~/.pi/agent/extensions/")
    total += load_extensions_dir(".pi/extensions/")
    if extra:
        try:
            load_extension_file(extra)
            total += 1
        except Exception as e:
            print(f"[extensions] failed to load extra extension {extra}: {e}")
    return total
