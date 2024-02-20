import abc
import sys
from _typeshed import Incomplete, OpenBinaryMode, OpenTextMode, Unused
from collections.abc import Iterator
from io import TextIOWrapper
from typing import IO, Any, BinaryIO, Literal, NoReturn, overload
from typing_extensions import Never

if sys.version_info >= (3, 11):
    from .abc import Traversable, TraversableResources

    class SimpleReader(abc.ABC):
        @property
        @abc.abstractmethod
        def package(self) -> str: ...
        @abc.abstractmethod
        def children(self) -> list[SimpleReader]: ...
        @abc.abstractmethod
        def resources(self) -> list[str]: ...
        @abc.abstractmethod
        def open_binary(self, resource: str) -> BinaryIO: ...
        @property
        def name(self) -> str: ...

    class ResourceHandle(Traversable, metaclass=abc.ABCMeta):
        parent: ResourceContainer
        def __init__(self, parent: ResourceContainer, name: str) -> None: ...
        def is_file(self) -> Literal[True]: ...
        def is_dir(self) -> Literal[False]: ...
        @overload
        def open(
            self, mode: OpenTextMode = "r", *args: Incomplete, **kwargs: Incomplete
        ) -> TextIOWrapper: ...
        @overload
        def open(
            self, mode: OpenBinaryMode, *args: Unused, **kwargs: Unused
        ) -> BinaryIO: ...
        @overload
        def open(
            self, mode: str, *args: Incomplete, **kwargs: Incomplete
        ) -> IO[Any]: ...
        def joinpath(self, name: Never) -> NoReturn: ...  # type: ignore[override]

    class ResourceContainer(Traversable, metaclass=abc.ABCMeta):
        reader: SimpleReader
        def __init__(self, reader: SimpleReader) -> None: ...
        def is_dir(self) -> Literal[True]: ...
        def is_file(self) -> Literal[False]: ...
        def iterdir(self) -> Iterator[ResourceHandle | ResourceContainer]: ...
        def open(self, *args: Never, **kwargs: Never) -> NoReturn: ...  # type: ignore[override]
        if sys.version_info < (3, 12):
            def joinpath(self, *descendants: str) -> Traversable: ...

    class TraversableReader(TraversableResources, SimpleReader, metaclass=abc.ABCMeta):
        def files(self) -> ResourceContainer: ...
