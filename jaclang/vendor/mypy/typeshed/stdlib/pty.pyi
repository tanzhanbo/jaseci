import sys
from collections.abc import Callable, Iterable
from typing import Literal
from typing_extensions import TypeAlias

if sys.platform != "win32":
    __all__ = ["openpty", "fork", "spawn"]
    _Reader: TypeAlias = Callable[[int], bytes]

    STDIN_FILENO: Literal[0]
    STDOUT_FILENO: Literal[1]
    STDERR_FILENO: Literal[2]

    CHILD: Literal[0]
    def openpty() -> tuple[int, int]: ...
    def master_open() -> tuple[int, str]: ...  # deprecated, use openpty()
    def slave_open(tty_name: str) -> int: ...  # deprecated, use openpty()
    def fork() -> tuple[int, int]: ...
    def spawn(
        argv: str | Iterable[str], master_read: _Reader = ..., stdin_read: _Reader = ...
    ) -> int: ...
