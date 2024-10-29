from __future__ import annotations

from fujin.connection import Connection

from fujin.config import Config, HostConfig


class WebProxy:

    @classmethod
    def create(cls, _: Config, __: HostConfig, ___: Connection) -> WebProxy:
        return cls()

    def install(self):
        pass

    def uninstall(self):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass
