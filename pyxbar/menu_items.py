from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field
from os.path import expanduser
from pathlib import Path
from shlex import quote
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
    TypeVar,
    Union,
)

from pyxbar.config import get_config

from .menu import MenuItem
from .types import Renderable
from .utils import camel_to_snake, get_in


@dataclass
class Divider(MenuItem):
    """Shortcut for a divider, super handy"""

    title: str = "---"


@dataclass
class MonoItem(MenuItem):
    """Shortcut for a monospace text menu item"""

    color: str = "white"
    monospace: Union[bool, None] = True


@dataclass
class ShellItem(MenuItem):
    """Menu Item that runs a shell script when selected"""

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

    def check_output(self, check: bool = True) -> str:
        shell_params = list(self.shell_params(use_cwd=False))
        if self.config.DEBUG:
            self.logger.debug(f"running: {shell_params}")
        try:
            output = subprocess.check_output(shell_params, cwd=self.cwd)
        except subprocess.CalledProcessError:
            if check:
                raise
            return ""
        else:
            return output.decode("utf-8").strip()


class DataclassItem:
    """
    Helpers to turn attributes in a dataclass to menu items
    """

    def menu_item_from_attr(
        self, name: str, attr: str, tr: Callable[[str], str] = str
    ) -> MenuItem:
        value = tr(getattr(self, attr))
        return MenuItem(name.format(value=value, self=self))

    def submenu_item_from_attr(
        self,
        name: str,
        attr: str,
        delim: str = "",
        tr: Callable[[str], str] = str,
        sort: Union[bool, Callable[[str], Any]] = False,
        **menu_kwargs: Any,
    ) -> MenuItem:
        """
        create a menuitem from a class attribute
        name: the menu item namte
        attr: the attr name
        delim: split the

        """
        value = getattr(self, attr)
        if isinstance(value, str):
            items = value.split(delim) if delim else [value]
        else:
            items = value
            if not isinstance(items, Iterable):
                items = [items]

        items = [clean for i in items if (clean := tr(i).strip())]

        if sort:
            items.sort(key=(sort if callable(sort) else None))

        return MenuItem(
            f"{name} [{len(items)}]",
            only_if=items,
            **menu_kwargs,
        ).with_submenu(MenuItem(_) for _ in items)


FJ = TypeVar("FJ", bound="JsonItem")


@dataclass
class JsonItem(DataclassItem):
    kwargs: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_json_list(cls: type[FJ], json_str: str, **attrs: Any) -> list[FJ]:
        json_str = json_str.strip()
        if not json_str:
            return []

        if json_str[0] == "[" and json_str[-1] == "]":
            loaded = json.loads(json_str)
        else:
            loaded = [json.loads(_) for _ in json_str.splitlines()]

        return [cls.from_dict(**attrs, **_) for _ in loaded]

    @classmethod
    def from_json_dict(
        cls: type[FJ],
        json_str: Union[str, None],
        subkey: str = "",
        key_as_name: bool = True,
        **attrs: Any,
    ) -> dict[str, FJ]:
        loaded = json.loads(json_str or "{}")
        if subkey:
            loaded = next(get_in(subkey, loaded))

        return {
            k: cls.from_dict(
                **attrs, **loaded[k], **({"name": k} if key_as_name else {})
            )
            for k in loaded
        }

    @classmethod
    def from_json(cls, json_str: str) -> JsonItem:
        loaded = json.loads(json_str)
        return cls.from_dict(**loaded)

    @classmethod
    def from_dict(cls, **kwargs: Any) -> JsonItem:
        return cls(
            **{
                camel_to_snake(k): kwargs[k]
                for k in kwargs
                if camel_to_snake(k) in cls.__dataclass_fields__
            },
            kwargs={k: kwargs[k] for k in kwargs if k not in cls.__dataclass_fields__},
        )

    def with_attrs(self: FJ, **kwargs: Any) -> FJ:
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self
