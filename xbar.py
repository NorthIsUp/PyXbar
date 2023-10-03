from __future__ import annotations

import json
import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from os.path import expanduser
from pathlib import Path
from shlex import quote
from typing import (
    Any,
    ClassVar,
    Generator,
    Iterable,
    Optional,
    Protocol,
    TypeVar,
    Union,
    get_type_hints,
)

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")


BoolNone = Optional[bool]

RenderableGenerator = Generator[str, None, None]


class Renderable(Protocol):
    def render(self, depth: int = 0) -> RenderableGenerator:
        ...


# ---------------------------------------------------------------------------- #
#                                    config                                    #
# ---------------------------------------------------------------------------- #


@dataclass
class Config:
    DEBUG: bool = False

    _errors: list[str] = field(init=False, default_factory=list)
    _warnings: list[str] = field(init=False, default_factory=list)

    def __post_init__(self):
        config_path = Path(__file__ + ".vars.json")
        if not config_path.exists():
            self.warn(f"{config_path.name} is missing, using defaults")

        else:
            config = json.loads(config_path.read_text())
            hints = get_type_hints(Config)
            for k in self.__dataclass_fields__:
                if k == "errors":
                    continue

                if val := config.get(f"VAR_{k}"):
                    setattr(self, k, hints[k](val))
                elif self.DEBUG:
                    self.warn(f"{k} is not set, using `{getattr(self, k)}`")

                if isinstance(v := getattr(self, k), Path):
                    setattr(self, k, v := v.expanduser())
                    if not v.exists():
                        self.error(f"{k} does not exist at {v}")

                if self.DEBUG:
                    logger.debug(f"{k}: {getattr(self, k)}")

    def render(self, depth: int = 0) -> RenderableGenerator:
        depth_prefix = f"{'--' * depth}"
        for title, color, preifx, messages in (
            ("errors", "red", "❌", self._errors),
            ("warnings", "yellow", "⚠️", self._warnings),
        ):
            if messages:
                yield from Divider().render(depth)
                yield from MenuItem(title, color=color).render(depth)
                for msg in sorted(messages):
                    yield from MenuItem(f"{depth_prefix} {preifx} {msg}").render(depth)

        if self.DEBUG:
            MenuItem("Vars").with_submenu(
                MenuItem(f"{k}: {getattr(self, k)}") for k in self.__dataclass_fields__
            ).render(depth + 1)
            # yield Cmd(f"📝 Edit Vars", f"open '{__file__}.vars.json'", depth=2)

    def error(self, msg: str):
        self._errors.append(msg)

    def warn(self, msg: str):
        self._warnings.append(msg)


CONFIG = Config()
# ---------------------------------------------------------------------------- #
#                                 menu classes                                 #
# ---------------------------------------------------------------------------- #


@dataclass
class Menu:
    title: str
    items: list[Renderable] = field(default_factory=list, init=False)
    config: Config = field(default_factory=Config, init=False)

    def render(self) -> Any:
        return "\n".join(
            (
                self.title,
                "---",
                *self._items(),
                *CONFIG.render(),
            )
        )

    def print(self) -> None:
        print(self.render())

    def _items(self) -> RenderableGenerator:
        for item in self.items:
            yield from item.render(depth=0)

    def with_items(self, *items: Renderable | Iterable[Renderable]) -> Menu:
        return with_something(self, self.items, *[_ for _ in items if _])


@dataclass
class MenuItem:
    title: str
    key: str = ""  # shift+k to add a key shortcut; Use + to create combinations; Example options: CmdOrCtrl, OptionOrAlt, shift, ctrl, super, tab, plus, return, escape, f12, up, down, space
    href: str = ""  # when clicked, open the url
    color: str = (
        ""  # change the text color. e.g. common colors 'red' and hex colors (#ff0000)
    )
    font: str = ""  # change the text font. eg. font=UbuntuMono-Bold
    size: int = 0  # change the text size. eg. size=12
    shell: str = ""  # make the item run a given script terminal with your script e.g. shell=/Users/user/xbar_Plugins/scripts/nginx.restart.sh if there are spaces in the file path you will need quotes e.g. shell="/Users/user/xbar Plugins/scripts/nginx.restart.sh" (bash is also supported but is deprecated)
    params: tuple[str, ...] = ()  # = to specify arguments to the script
    terminal: BoolNone = None  # start bash script without opening Terminal
    refresh: BoolNone = None  # make the item refresh the plugin it belongs to. If the item runs a script, refresh is performed after the script finishes. eg. refresh=true
    dropdown: BoolNone = None  # If false, the line will only appear and cycle in the status bar but not in the dropdown
    length: int = 0  # truncate the line to the specified number of characters. A … will be added to any truncated strings, as well as a tooltip displaying the full string. eg. length=10
    trim: BoolNone = None  # whether to trim leading/trailing whitespace from the title.  true or false (defaults to true)
    alternate: BoolNone = None  # =true to mark a line as an alternate to the previous one for when the Option key is pressed in the dropdown
    templateImage: str = ""  # set an image for this item. The image data must be passed as base64 encoded string and should consist of only black and clear pixels. The alpha channel in the image can be used to adjust the opacity of black content, however. This is the recommended way to set an image for the statusbar. Use a 144 DPI resolution to support Retina displays. The imageformat can be any of the formats supported by Mac OS X
    image: str = ""  # set an image for this item. The image data must be passed as base64 encoded string. Use a 144 DPI resolution to support Retina displays. The imageformat can be any of the formats supported by Mac OS X
    emojize: BoolNone = (
        None  # =false will disable parsing of github style :mushroom: into emoji
    )
    ansi: BoolNone = None  # =false turns off parsing of ANSI codes.
    disabled: BoolNone = None  # =true greyed out the line and disable click

    magic_number: ClassVar[int] = 19  # only use the 19 attrs above here
    only_if: bool = True
    submenu: list[Renderable] = field(default_factory=list, init=False)
    siblings: list[Renderable] = field(default_factory=list, init=False)

    @classmethod
    def _type_hint(cls, key: str, hints: dict[type, dict[str, type]] = {}):
        if cls not in hints:
            hints[cls] = get_type_hints(cls, globals())

        return hints[cls][key]

    @property
    def is_divider(self) -> bool:
        return self.title == "---"

    @property
    def config(self) -> Config:
        return self.parent.config

    def depth_prefix(self, depth: int = 0) -> str:
        return f"{'--' * depth}{' ' if depth and not self.is_divider else ''}"

    def _title(self, depth: int = 0) -> str:
        return f"{self.depth_prefix(depth)}{self.title}"

    def subclass_render_hook(self) -> Generator[Renderable, None, None]:
        yield from ()

    def shell_params(self) -> Iterable[str]:
        if not self.shell:
            return ()
        shell, *params = [quote(_) for _ in shlex.split(self.shell)]
        return (shell, *params, *self.params)

    def menu_params(self) -> Iterable[tuple[str, Any]]:
        return (
            (k, v)
            for k, v in (
                (k, getattr(self, k))
                for k in list(MenuItem.__dataclass_fields__)[1:19]
                if k != "shell"
            )
            if (self._type_hint(k) == BoolNone and v is not None) or v
        )

    def all_params(self) -> Iterable[str]:
        if shell_params := self.shell_params():
            shell, *shell_params = shell_params
            yield f"shell={shell}"
            yield from (f"param{i}={p}" for i, p in enumerate(shell_params, 1))

        yield from (f"{k}={quote(str(v))}" for k, v in self.menu_params())

    def render(self, depth: int = 0) -> RenderableGenerator:
        if self.only_if:
            yield " | ".join((self._title(depth), *self.all_params()))

            for item in self.subclass_render_hook():
                yield from item.render(depth)

            for item in self.submenu:
                yield from item.render(depth + 1)

            for item in self.siblings:
                yield from item.render(depth)

    def add_submenu(self, child: MenuItem) -> MenuItem:
        self.submenu.append(child)
        return self

    def with_submenu(self, *children: Renderable | Iterable[Renderable]) -> MenuItem:
        return with_something(self, self.submenu, *children)

    def with_siblings(self, *children: Renderable | Iterable[Renderable]) -> MenuItem:
        return with_something(self, self.siblings, *children)

    def with_parent(self, parent: Menu | MenuItem) -> MenuItem:
        self.parent = parent
        return self


@dataclass
class Divider(MenuItem):
    title: str = "---"


@dataclass
class ShellItem(MenuItem):
    cwd: Union[str, Path, None] = None

    def __init__(
        self,
        title: str,
        shell: str,
        cwd: Union[str, Path, None] = None,
        **kwargs: Any,
    ):
        super().__init__(title, shell=shell, **kwargs)
        self.cwd = cwd

    def __post_init__(self):
        if isinstance(self.cwd, str):
            self.cwd = Path(self.cwd)

        if self.cwd and not self.cwd.exists():
            CONFIG.error(f"❌ cwd does not exist at {self.cwd}")

        if self.shell and not self.params:
            self.shell, *self.params = (quote(_) for _ in shlex.split(self.shell))

    def shell_params(self, use_cwd: bool = True) -> Iterable[str]:
        shell_params = super().shell_params()

        if use_cwd and self.cwd:
            shell_params = ("cd", expanduser(self.cwd), "&&", *shell_params)

        return shell_params

    def shell_str(self, use_cwd: bool = False) -> str:
        return " ".join(self.shell_params(use_cwd=use_cwd))

    def subclass_render_hook(self, depth: int = 0) -> Generator[Renderable, None, None]:
        if CONFIG.DEBUG:
            yield MenuItem(
                f"╰─ {self.shell_str(use_cwd=False)}", font="Andale Mono", disabled=True
            )

    def run(self) -> str:
        shell_params = list(self.shell_params(use_cwd=False))
        if CONFIG.DEBUG:
            logger.debug(f"running: {shell_params}")
        output = subprocess.check_output(shell_params, cwd=self.cwd)
        return output.decode("utf-8").strip()


# ---------------------------------------------------------------------------- #
#                               utility functions                              #
# ---------------------------------------------------------------------------- #


def get_in(
    keys: str | list[str],
    coll: dict[object, object] | list[object],
    default: object = (_no_default := object()),
) -> Generator[object, None, None]:
    try:
        key, *keys = keys.split(".") if isinstance(keys, str) else keys
        if key == "*":
            for i in range(len(coll)):
                yield from get_in([i, *keys], coll, default)
        elif not keys:
            yield coll[key]
        else:
            yield from get_in(keys, coll[key], default)
    except (KeyError, IndexError, TypeError):
        if default is not _no_default:
            yield default


T = TypeVar("T")


def with_something(
    ret: T,
    key: list[Renderable],
    *children: Renderable | Iterable[Renderable],
) -> T:
    for child in children:
        if isinstance(child, Iterable):
            key.extend(child)
        else:
            key.append(child)
    return ret


if __name__ == "__main__":
    Menu("some title").with_items(
        MenuItem(
            "👁️ overview",
        ),
    ).print()
