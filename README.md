Python library to make xbar development easy in python

Include this in your file after the regular imports
```py
def install(pkg: str, spec: str = ""):
    try:
        __import__(pkg)
    except ImportError:
        install_args = ["install", "--upgrade", f"--target={Path(__file__).parent}"]
        getattr(__import__("pip"), "main")(install_args + [spec or pkg])
        __import__(pkg)


install("pyxbar")


from pyxbar import (  # noqa: E402
    Config,
    Divider,
    Menu,
    MenuItem,
    Renderable,
    ShellItem,
)


@dataclass
class MyConfig(Config):
    MYVARIABLE: bool = True
    ...

CONFIG = get_config(MyConfig)  # type: ignore
)
```
