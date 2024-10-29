from __future__ import annotations

from typing import Protocol

from fujin.config import Config
from fujin.config import HostConfig
from fujin.connection import Connection


class WebProxy(Protocol):
    @classmethod
    def create(
        cls, config: Config, host_config: HostConfig, conn: Connection
    ) -> WebProxy: ...

    def install(self) -> None: ...

    def uninstall(self) -> None: ...

    def setup(self) -> None: ...

    def teardown(self) -> None: ...
