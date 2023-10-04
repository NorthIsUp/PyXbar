from __future__ import annotations

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
    Union,
    get_type_hints,
)

from pyxbar.config import Config, get_config
from pyxbar.types import Boolable, Optional, Renderable, RenderableGenerator
from pyxbar.utils import with_something

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")


@dataclass
class Menu:
    title: str
    items: list[Renderable] = field(default_factory=list, init=False)

    def render(self) -> Any:
        return "\n".join(
            (
                self.title,
                "---",
                *self._items(),
                *get_config().render(),  # type: ignore
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
    terminal: Optional[bool] = None  # start bash script without opening Terminal
    refresh: Optional[
        bool
    ] = None  # make the item refresh the plugin it belongs to. If the item runs a script, refresh is performed after the script finishes. eg. refresh=true
    dropdown: Optional[
        bool
    ] = None  # If false, the line will only appear and cycle in the status bar but not in the dropdown
    length: int = 0  # truncate the line to the specified number of characters. A … will be added to any truncated strings, as well as a tooltip displaying the full string. eg. length=10
    trim: Optional[
        bool
    ] = None  # whether to trim leading/trailing whitespace from the title.  true or false (defaults to true)
    alternate: Optional[
        bool
    ] = None  # =true to mark a line as an alternate to the previous one for when the Option key is pressed in the dropdown
    templateImage: str = ""  # set an image for this item. The image data must be passed as base64 encoded string and should consist of only black and clear pixels. The alpha channel in the image can be used to adjust the opacity of black content, however. This is the recommended way to set an image for the statusbar. Use a 144 DPI resolution to support Retina displays. The imageformat can be any of the formats supported by Mac OS X
    image: str = ""  # set an image for this item. The image data must be passed as base64 encoded string. Use a 144 DPI resolution to support Retina displays. The imageformat can be any of the formats supported by Mac OS X
    emojize: Optional[
        bool
    ] = None  # =false will disable parsing of github style :mushroom: into emoji
    ansi: Optional[bool] = None  # =false turns off parsing of ANSI codes.
    disabled: Optional[bool] = None  # =true greyed out the line and disable click

    magic_number: ClassVar[int] = 19  # only use the 19 attrs above here
    only_if: Boolable = True
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
        return get_config()

    @property
    def logger(self) -> logging.Logger:
        return logger

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
            if (self._type_hint(k) == Optional[bool] and v is not None) or v
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

    def with_submenu(self, *children: Renderable | Iterable[Renderable]) -> MenuItem:
        return with_something(self, self.submenu, *children)

    def with_siblings(self, *children: Renderable | Iterable[Renderable]) -> MenuItem:
        return with_something(self, self.siblings, *children)


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
        super().__init__(title=title, shell=shell, **kwargs)
        self.cwd = cwd

    def __post_init__(self):
        if isinstance(self.cwd, str):
            self.cwd = Path(self.cwd)

        if self.cwd and not self.cwd.exists():
            self.config.error(f"❌ cwd does not exist at {self.cwd}")

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
        if self.config.DEBUG:
            yield MenuItem(
                title=f"╰─ {self.shell_str(use_cwd=False)}",
                font=get_config().MONO_FONT,
                disabled=True,
            )

    def run(self) -> str:
        shell_params = list(self.shell_params(use_cwd=False))
        if self.config.DEBUG:
            self.logger.debug(f"running: {shell_params}")
        output = subprocess.check_output(shell_params, cwd=self.cwd)
        return output.decode("utf-8").strip()
