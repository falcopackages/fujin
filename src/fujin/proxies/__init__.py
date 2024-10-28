from __future__ import annotations

from multiprocessing.connection import Connection
from typing import Protocol

from fujin.config import Config


class WebProxy(Protocol):
    conn: Connection
    config: Config

    def install(self) -> None: ...

    def uninstall(self) -> None: ...

    def setup(self) -> None: ...

    def teardown(self) -> None: ...
