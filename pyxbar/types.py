from __future__ import annotations

from typing import Generator, Literal, Protocol, Union


class HasBool(Protocol):
    def __bool__(self) -> bool: ...


class HasLen(Protocol):
    def __len__(self) -> int: ...


class Renderable(Protocol):
    def render(self, depth: int = 0) -> RenderableGenerator: ...


RenderableGenerator = Generator[str, None, None]

Boolable = Union[HasBool, HasLen]

Numeric = Union[int, float]

DividerLiteral = Literal["---"]
