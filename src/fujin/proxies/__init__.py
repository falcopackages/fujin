from __future__ import annotations

from pathlib import Path
from typing import Protocol

from fujin.config import Config
from fujin.config import HostConfig
from fujin.connection import Connection


class WebProxy(Protocol):
    config_file: Path

    @classmethod
    def create(cls, config: Config, conn: Connection) -> WebProxy: ...

    def install(self) -> None: ...

    def uninstall(self) -> None: ...

    def setup(self) -> None: ...

    def teardown(self) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def status(self) -> None: ...

    def restart(self) -> None: ...

    def logs(self) -> None: ...

    def export_config(self) -> None: ...
