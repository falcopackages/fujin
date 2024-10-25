from dataclasses import dataclass
from functools import cached_property
from typing import Annotated

import cappa

from fujin.config import Config
from fujin.errors import ImproperlyConfiguredError
from fujin.host import Host


@dataclass
class BaseCommand:
    @cached_property
    def config(self) -> Config:
        return Config.read()

    @cached_property
    def stdout(self) -> cappa.Output:
        return cappa.Output()


@dataclass
class HostCommand(BaseCommand):
    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    @cached_property
    def host(self) -> Host:
        host_config = None
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
