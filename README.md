Python library to make xbar development easy in python

Include this in your file after the regular imports

```py
def install(pkg: str, spec: str = ""):
    sys.path += [] if (sp := f"{Path(__file__)}.site-packages") in sys.path else [sp]
    try:
        __import__(pkg)
    except ImportError:
        install_args = ["install", "--upgrade", f"--target={sp}"]
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


class MyConfig(Config):
    MYVARIABLE: bool = True
    ...

CONFIG = get_config(MyConfig)  # type: ignore
)



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
