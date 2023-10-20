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
    Literal,
    Union,
    get_type_hints,
    overload,
)

from typing_extensions import NotRequired, TypedDict, Unpack

from pyxbar.config import Config, get_config
from pyxbar.types import Boolable, Optional, Renderable, RenderableGenerator
from pyxbar.utils import with_something

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")


class MenuItemKwargsOptional(TypedDict, total=False):
    key: NotRequired[str]
    href: NotRequired[str]
    color: NotRequired[str]
    font: NotRequired[Union[str, Literal["monospace"]]]
    size: NotRequired[int]
    shell: NotRequired[str]
    params: NotRequired[tuple[str, ...]]
    terminal: NotRequired[Optional[bool]]
    refresh: NotRequired[Optional[bool]]
    dropdown: NotRequired[Optional[bool]]
    length: NotRequired[int]
    trim: NotRequired[Optional[bool]]
    alternate: NotRequired[Optional[bool]]
    templateImage: NotRequired[str]
    image: NotRequired[str]
    emojize: NotRequired[Optional[bool]]
    ansi: NotRequired[Optional[bool]]
    disabled: NotRequired[Optional[bool]]


class MenuItemKwargs(MenuItemKwargsOptional, total=False):
    title: str


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
    """AI is creating summary for

    Attributes:
        title: (str):
            the text of the menu item
        key: (str):
            shortcut key, use + to create combinations
            options: (CmdOrCtrl, OptionOrAlt, shift, ctrl, super, tab, plus,
            return, escape, f12, up, down, space)
            e.g. key=k or key=shift+k
        href: (str):
            open href when clicked
        color: (str):
            the text color
            e.g. common colors 'red' and hex colors '#ff0000'
        font: (str):
            text font (defaults to system font).
            e.g. font=UbuntuMono-Bold
        size: (int):
            text size
        shell: (str):
            run this command when clicked
        params: (tuple[str, ...]):
            arguments to the script
        terminal: (bool | None):
            should the script run in a terminal window
        refresh: (bool | None):
            refresh the current menu. If the item runs a script, refresh is
            performed after the script finishes
        dropdown: (bool | None):
            If false, the line will only appear and cycle in the status bar but
            not in the dropdown
        length: (int):
            truncate the line to the specified number of characters. A … will be
            added to any truncated strings, as well as a tooltip displaying the
            full string.
            e.g. length=10
        trim: (bool | None):
            should leading/trailing whitespace be trimmed from the title
        alternate: (bool | None):
            mark a line as an alternate to the previous one for when the Option
            key is pressed in the dropdown
        templateImage: (str):
            set an image for this item. The image data must be passed as base64
            encoded string and should consist of only black and clear pixels.
            The alpha channel in the image can be used to adjust the opacity of
            black content, however. This is the recommended way to set an image
            for the statusbar. Use a 144 DPI resolution to support Retina
            displays. The imageformat can be any of the formats supported by Mac
            OS X
        image: (str):
            set an image for this item. The image data must be passed as base64
            encoded string. Use a 144 DPI resolution to support Retina displays.
            The imageformat can be any of the formats supported by Mac OS X
        emojize: (bool | None):
            should convert text into an emoji. e.g. :mushroom: into 🍄
        ansi: (bool | None):
            should parsing of ANSI codes.
        disabled: (bool | None):
            should the line be greyed out and click disabled


    Yields:
        [type]: [description]
    """

    title: str
    key: str = ""
    href: str = ""
    color: str = ""
    font: Union[str, Literal["monospace"]] = ""
    size: int = 0
    shell: str = ""
    params: tuple[str, ...] = ()
    terminal: Optional[bool] = None
    refresh: Optional[bool] = None
    dropdown: Optional[bool] = None
    length: int = 0
    trim: Optional[bool] = None
    alternate: Optional[bool] = None
    templateImage: str = ""
    image: str = ""
    emojize: Optional[bool] = None
    ansi: Optional[bool] = None
    disabled: Optional[bool] = None

    magic_number: ClassVar[int] = 19  # only use the 19 attrs above here
    title_alternate: Optional[str] = None  # alternate title for Option key
    monospace: Optional[bool] = False  # shortcut to set font to monospace
    only_if: Boolable = True
    submenu: list[Renderable] = field(default_factory=list, init=False)
    siblings: list[Renderable] = field(default_factory=list, init=False)

    @classmethod
    def _type_hint(cls, key: str, hints: dict[type, dict[str, type]] = {}):
        if cls not in hints:
            hints[cls] = get_type_hints(cls, globals())

        return hints[cls][key]

    def __post_init__(self):
        if self.submenu:
            self.submenu = list(self.submenu)

        if self.siblings:
            self.siblings = list(self.siblings)

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

    def _title(self, depth: int = 0, alternate: bool = False) -> str:
        return f"{self.depth_prefix(depth)}{self.title if not alternate else self.title_alternate}"

    def subclass_render_hook(self) -> Generator[Renderable, None, None]:
        yield from ()

    def shell_params(self) -> Iterable[str]:
        if not self.shell:
            return ()
        shell, *params = [quote(_) for _ in shlex.split(self.shell)]
        return (shell, *params, *self.params)

    def menu_params(self) -> Iterable[tuple[str, Any]]:
        if self.font == "monospace" or self.monospace:
            self.font = self.config.MONO_FONT

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

            if self.title_alternate:
                yield " | ".join((self._title(depth, True), *self.all_params()))

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

    @overload
    def with_alternate(
        self, title_or_item: str, **kwargs: Unpack[MenuItemKwargsOptional]
    ) -> MenuItem:
        ...

    @overload
    def with_alternate(
        self, title_or_item: None = ..., **kwargs: Unpack[MenuItemKwargs]
    ) -> MenuItem:
        ...

    @overload
    def with_alternate(self, title_or_item: MenuItemKwargs) -> MenuItem:
        ...

    @overload
    def with_alternate(self, title_or_item: MenuItem) -> MenuItem:
        ...

    def with_alternate(
        self,
        title_or_item: Union[str, MenuItemKwargs, MenuItem, None] = None,
        title: Optional[str] = None,
        **kwargs: Unpack[MenuItemKwargsOptional],
    ) -> MenuItem:
        if title_or_item is None and title:
            title_or_item = MenuItemKwargs(title=title, **kwargs)
        if isinstance(title_or_item, str):
            title_or_item = MenuItemKwargs(title=title_or_item, **kwargs)
        if isinstance(title_or_item, dict):
            title_or_item = MenuItem(**title_or_item)
        if isinstance(title_or_item, MenuItem):
            title_or_item.alternate = True
            return self.with_siblings(title_or_item)
        raise NotImplementedError()


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
        if cwd is not None:
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

    def check_output(self) -> str:
        shell_params = list(self.shell_params(use_cwd=False))
        if self.config.DEBUG:
            self.logger.debug(f"running: {shell_params}")
        output = subprocess.check_output(shell_params, cwd=self.cwd)
        return output.decode("utf-8").strip()


class MenuItemable(Renderable):
    """subclass this in a dataclass to make something that will become a menu item!"""

    def menu_item(self) -> MenuItem:
        raise NotImplementedError("subclass must implement this ")

    def render(self, depth: int = 0) -> MenuItem:
        yield from self.menu_item().render(depth=depth)
