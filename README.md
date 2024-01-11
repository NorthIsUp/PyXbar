Python library to make xbar development easy in python

Include this in your file after the regular imports

```py
import os, sys
from pathlib import Path

def install(pkg: str, spec: str = "", cache_dir: Path | str = "~/.cache"):
    name, cache = Path(__file__), Path(os.environ.get("XDG_CACHE_HOME", cache_dir))
    sitep = (cache / f"pyxbar/{name.name}/site-packages").as_posix()
    sys.path += [] if sitep in sys.path else [sitep]
    try:
        __import__(pkg)
    except ImportError:
        install_args = ["install", "--upgrade", f"--target={sitep}", spec or pkg]
        getattr(__import__("pip"), "main")(install_args)
        __import__("importlib").invalidate_caches()



# install the PyXbar library from pypi
install("pyxbar")

# use it!
from pyxbar import (
    Config,
    Divider,
    Menu,
    MenuItem,
    Renderable,
    ShellItem,
)


class MyConfig(Config):
    MYVARIABLE: bool = True
    ...

CONFIG = get_config(MyConfig)  # type: ignore




if __name__ == "__main__":
    Menu("some title").with_items(
        Divider(),  # shortcut for ---, also handles submenu depth
        MenuItem(
            "👁️ overview",
        ).with_submenu(
            MenuItem("hi, i'm a submenu!").
            MenuItem("hi, i'm monospace!", monospaced=True)
        ),
    ).print()

```
