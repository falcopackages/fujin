import importlib
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated

import cappa
from fujin.config import Config, HostConfig
from fujin.connection import host_connection, Connection
from fujin.errors import ImproperlyConfiguredError
from fujin.hooks import HookManager
from fujin.process_managers import ProcessManager
from fujin.proxies import WebProxy


@dataclass
class BaseCommand:
    @cached_property
    def config(self) -> Config:
        return Config.read()

    @cached_property
    def stdout(self) -> cappa.Output:
        return cappa.Output()


@dataclass
class AppCommand(BaseCommand):
    """
    A command that provides access to the selected host and provide a connection to interact with it,
    including configuring the web proxy and managing systemd services.
    """

    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    @cached_property
    def host_config(self) -> HostConfig:
        if not self._host:
            host_config = next(
                (hc for hc in self.config.hosts.values() if hc.default), None
            )
            if not host_config:
                raise ImproperlyConfiguredError(
                    "No default host has been configured, either pass --host or set the default in your fujin.toml file"
                )
        else:
            host_config = next(
                (
                    hc
                    for name, hc in self.config.hosts.items()
                    if self._host in [name, hc.ip]
                ),
                None,
            )
        if not host_config:
            raise cappa.Exit(f"Host {self._host} does not exist", code=1)
        return host_config

    @cached_property
    def project_dir(self) -> str:
        return self.host_config.project_dir(app_name=self.config.app_name)

    @contextmanager
    def connection(self):
        with host_connection(host_config=self.host_config) as conn:
            yield conn

    @contextmanager
    def app_environment(self) -> Connection:
        with self.connection() as conn:
            with conn.cd(self.project_dir):
                with conn.prefix("source envrun"):
                    yield conn

    @cached_property
    def web_proxy_class(self) -> type[WebProxy]:
        module = importlib.import_module(self.config.webserver.type)
        try:
            return getattr(module, "WebProxy")
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing WebProxy class in {self.config.webserver.type}"
            ) from e

    def create_web_proxy(self, conn: Connection) -> WebProxy:
        return self.web_proxy_class.create(
            conn=conn, config=self.config, host_config=self.host_config
        )

    @cached_property
    def process_manager_class(self) -> type[ProcessManager]:
        module = importlib.import_module(self.config.process_manager)
        try:
            return getattr(module, "ProcessManager")
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing ProcessManager class in {self.config.process_manager}"
            ) from e

    def create_process_manager(self, conn: Connection) -> ProcessManager:
        return self.process_manager_class.create(
            conn=conn, config=self.config, host_config=self.host_config
        )

    def create_hook_manager(self, conn: Connection) -> HookManager:
        return HookManager(
            conn=conn, hooks=self.config.hooks, app_name=self.config.app_name
        )
