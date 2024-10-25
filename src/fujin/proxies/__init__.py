from __future__ import  annotations
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from fujin.config import Config
    from fujin.host import Host


class WebProxy(Protocol):
    host: Host
    config: Config

    def install(self) -> None:
        ...

    def configure(self) -> None:
        ...
