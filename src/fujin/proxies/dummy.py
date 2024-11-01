from __future__ import annotations

from fujin.config import Config
from fujin.config import HostConfig
from fujin.connection import Connection


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
    
    def export_config(self):
        pass
