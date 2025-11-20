from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Generator

import cappa

from fujin.config import Config
from fujin.connection import Connection
from fujin.connection import host_connection
from fujin.hooks import HookManager


@dataclass
class BaseCommand:
    """
    A command that provides access to the host config and provide a connection to interact with it,
    including configuring the web proxy and managing systemd services.
    """

    @cached_property
    def config(self) -> Config:
        return Config.read()

    @cached_property
    def stdout(self) -> cappa.Output:
        return cappa.Output()

    @cached_property
    def app_dir(self) -> str:
        return self.config.host.get_app_dir(app_name=self.config.app_name)

    @cached_property
    def hook_manager(self) -> HookManager:
        return HookManager(
            hooks=self.config.hooks,
            app_name=self.config.app_name,
            local_config_dir=self.config.local_config_dir,
        )

    @contextmanager
    def connection(self):
        with host_connection(host=self.config.host) as conn:
            yield conn

    @contextmanager
    def app_environment(self) -> Generator[Connection, None, None]:
        with self.connection() as conn:
            with conn.cd(self.app_dir):
                with conn.prefix("source .appenv"):
                    yield conn

