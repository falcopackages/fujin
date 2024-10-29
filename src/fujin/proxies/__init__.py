from __future__ import annotations

from fujin.connection import Connection
from typing import Protocol

from fujin.config import Config, HostConfig


class WebProxy(Protocol):

    @classmethod
    def create(cls, config: Config, host_config: HostConfig, conn: Connection) -> WebProxy:
        ...

    def install(self) -> None: ...

    def uninstall(self) -> None: ...

    def setup(self) -> None: ...

    def teardown(self) -> None: ...
