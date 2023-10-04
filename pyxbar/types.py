from __future__ import annotations

from typing import (
    Generator,
    Optional,
    Protocol,
    Union,
)


class HasBool(Protocol):
    def __bool__(self) -> bool:
        ...


class HasLen(Protocol):
    def __len__(self) -> int:
        ...


Boolable = Union[HasBool, HasLen]


RenderableGenerator = Generator[str, None, None]


class Renderable(Protocol):
    def render(self, depth: int = 0) -> RenderableGenerator:
        ...
