from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fujin.config import Config
    from fujin.host import Host


class WebProxy(Protocol):
    host: Host
    config: Config

    def install(self) -> None: ...

    def setup(self) -> None: ...

    def teardown(self) -> None: ...
