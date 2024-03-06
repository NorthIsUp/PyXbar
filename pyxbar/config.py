from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from inspect import getfile
from pathlib import Path
from typing import ClassVar, Iterable, Type, TypeVar, cast, get_type_hints

from pyxbar.types import Renderable, RenderableGenerator
from pyxbar.utils import cache_dir

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")


@dataclass
class Config(Renderable):
    DEBUG: bool = False
    MONO_FONT: str = "Andale Mono"
    CACHE_DIR: Path = field(default_factory=cache_dir, repr=False)

    _errors: list[str] = field(default_factory=list, init=False, repr=False)
    _warnings: list[str] = field(default_factory=list, init=False, repr=False)

    prefix: ClassVar[str] = "VAR_"

    def __post_init__(self):
        for k in self.config_fields():
            v = getattr(self, k)
            if isinstance(v, Path):
                setattr(self, k, v.expanduser().resolve())
            if self.DEBUG:
                logger.debug(f"{k}: {getattr(self, k)}")

    @classmethod
    def config_fields(cls) -> Iterable[str]:
        return [k for k in cls.__dataclass_fields__ if k.isupper()]

    @classmethod
    def config_path(cls) -> Path:
        return Path(f"{getfile(cls)}.vars.json")

    @classmethod
    def from_config_file(cls):
        loaded = json.loads(cls.config_path().read_text() if cls.config_path().exists() else "{}")
        return cls.from_config_dict(loaded)

    @classmethod
    def from_config_dict(cls, config_dict: dict[str, str]):
        hints = get_type_hints(cls)
        return cls(
            **{
                k: hints[k](config_dict[f"VAR_{k}"])
                for k in cls.config_fields()
                if f"VAR_{k}" in config_dict
            }
        )

    @classmethod
    def get_config(cls):
        return cls.from_config_file()

    def as_config_dict(self) -> dict[str, str]:
        return {
            f"{self.prefix}{k}": str(getattr(self, k)) for k in self.config_fields()
        }

    def save(self):
        self.config_path().write_text(json.dumps(self.as_config_dict(), indent=4))

    def render(self, depth: int = 0) -> RenderableGenerator:
        from pyxbar import Divider, MenuItem

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
            yield from MenuItem(f"🐍 {sys.version}").render()
            yield from MenuItem("Vars").with_submenu(
                MenuItem(f"{k}: {getattr(self, k)}") for k in self.__dataclass_fields__
            ).render(depth)
            # yield Cmd(f"📝 Edit Vars", f"open '{__file__}.vars.json'", depth=2)

    def error(self, msg: str):
        if msg not in self._errors:
            self._errors.append(msg)

    def warn(self, msg: str):
        if msg not in self._warnings:
            self._warnings.append(msg)


ConfigT = TypeVar("ConfigT", bound=Config)

CONFIG_CLS: Type[Config]
CONFIG: Config


def get_config(config_cls: Type[ConfigT] = Config) -> ConfigT:
    global CONFIG_CLS, CONFIG

    if config_cls is globals().get("CONFIG_CLS") is None:
        raise RuntimeError("CONFIG_CLS is not set")

    if config_cls:
        CONFIG_CLS = config_cls  # type: ignore

    if "CONFIG" in globals() and isinstance(CONFIG, CONFIG_CLS):
        return cast(ConfigT, CONFIG)

    globals()["CONFIG"] = CONFIG_CLS.get_config()

    return get_config(config_cls=config_cls)
