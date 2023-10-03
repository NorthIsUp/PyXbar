from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import (
    Any,
    Generator,
    Iterable,
    TypeVar,
    Union,
)

from pyxbar.types import Renderable

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")

T = TypeVar("T")


def get_in(
    keys: str | list[str],
    coll: dict[str | int, Any] | list[Any],
    default: object = (_no_default := object()),
) -> Generator[Any, None, None]:
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


def strify(joiner: str, *args: Any) -> str:
    """joins strings and filters out None values"""
    if len(args) == 1 and not isinstance(args[0], str):
        return strify(joiner, *args[0])
    return joiner.join(str(arg) for arg in args if arg is not None)


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


def check_output(cmd: str, cwd: Union[str, Path, None] = None) -> str:
    logger.debug(f"running: {cmd}")
    return subprocess.check_output(cmd, shell=True, cwd=cwd, encoding="utf-8").strip()
