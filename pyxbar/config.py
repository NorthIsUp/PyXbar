from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from inspect import getfile
from pathlib import Path
from typing import (
    Type,
    TypeVar,
    cast,
    get_type_hints,
)

from pyxbar.types import RenderableGenerator

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")


@dataclass
class Config:
    DEBUG: bool = False
    MONO_FONT: str = "Andale Mono"

    _errors: list[str] = field(default_factory=list)
    _warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        config_path = Path(f"{getfile(self.__class__)}.vars.json")
        if not config_path.exists():
            self.warn(f"{config_path.name} is missing, using defaults")

        else:
            config = json.loads(config_path.read_text())
            hints = get_type_hints(self.__class__)
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
            MenuItem("Vars").with_submenu(
                MenuItem(f"{k}: {getattr(self, k)}") for k in self.__dataclass_fields__
            ).render(depth + 1)
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


def get_config(config_cls: Type[ConfigT] | None = None) -> ConfigT:
    global CONFIG_CLS, CONFIG

    if config_cls is globals().get("CONFIG_CLS") is None:
        raise RuntimeError("CONFIG_CLS is not set")

    if config_cls:
        CONFIG_CLS = config_cls  # type: ignore

    if globals().get("CONFIG"):
        return CONFIG_CLS(**asdict(CONFIG))  # type: ignore

    return cast(ConfigT, CONFIG_CLS())
