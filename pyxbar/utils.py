from __future__ import annotations

import logging
import re
from typing import (
    Any,
    Generator,
    Iterable,
    TypeVar,
    Union,
)

from .types import Numeric, Renderable

logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format="=====> %(message)s")

T = TypeVar("T")


def get_in(
    keys: Union[str, list[str]],
    coll: Union[dict[Union[str, int], Any], list[Any]],
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


def camel_to_snake(
    s: str, _cache: dict[str, Any] = {"ID": "id", "_re": re.compile(r"(?<!^)(?=[A-Z])")}
) -> str:
    if s in _cache:
        return _cache[s]
    return _cache.setdefault(s, _cache["_re"].sub("_", s).lower())


def with_something(
    ret: T,
    key: list[Renderable],
    *children: Union[Renderable, Iterable[Renderable]],
) -> T:
    for child in children:
        if isinstance(child, Iterable):
            key.extend(child)
        else:
            key.append(child)
    return ret


def threshold_icons(level: Numeric, *icons: tuple[str, int], default: str = "") -> str:
    """return icons based on where a number falls in a list"""
    icon = default
    for icon, limit in icons:
        if level >= limit:
            return icon
    else:
        return default or icon


def threshold_traffic_icons(
    level: Numeric,
    blue: int,
    green: int,
    yellow: int,
    red: int,
    zero: str = "",
):
    return threshold_icons(
        level,
        ("🔵", blue),
        ("🟢", green),
        ("🟡", yellow),
        ("🔴", red),
        default=zero,
    )
