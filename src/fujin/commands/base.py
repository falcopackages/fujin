from dataclasses import dataclass
from typing import Annotated

import cappa

from fujin.config import Config
from fujin.host import Host


@dataclass
class BaseCommand:
    @property
    def config(self) -> Config:
        return Config.read()

    @property
    def stdout(self) -> cappa.Output:
        return cappa.Output()


@dataclass
class HostCommand(BaseCommand):
    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    # @cache
    @property
    def host(self) -> Host:
        if not self._host:
            return self.config.primary_host
        try:
            return self.config.hosts[self._host]
        except KeyError as e:
            raise cappa.Exit(f"Host {self._host} does not exist", code=1) from e
