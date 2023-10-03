from __future__ import annotations

from typing import (
    Generator,
    Optional,
    Protocol,
)

BoolNone = Optional[bool]

RenderableGenerator = Generator[str, None, None]


class Renderable(Protocol):
    def render(self, depth: int = 0) -> RenderableGenerator:
        ...
