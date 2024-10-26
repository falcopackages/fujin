import importlib
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated

import cappa

from fujin.config import Config
from fujin.errors import ImproperlyConfiguredError
from fujin.hooks import HookManager
from fujin.host import Host
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
    A command that provides access to the current host and allows interaction with it,
    including configuring the web proxy and managing systemd services.
    """

    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    # TODO: add info / details command that will list all services with their current status, if they are installed or running or stopped

    @cached_property
    def host(self) -> Host:
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
        return Host(config=host_config)

    @cached_property
    def web_proxy(self) -> WebProxy:
        module = importlib.import_module(self.config.webserver.type)
        try:
            return getattr(module, "WebProxy")(host=self.host, config=self.config)
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing WebProxy class in {self.config.webserver.type}"
            ) from e

    @cached_property
    def process_manager(self) -> ProcessManager:
        module = importlib.import_module(self.config.process_manager)
        try:
            return getattr(module, "ProcessManager")(host=self.host, config=self.config)
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing ProcessManager class in {self.config.process_manager}"
            ) from e

    @cached_property
    def hook_manager(self) -> HookManager:
        return HookManager(host=self.host, config=self.config)
