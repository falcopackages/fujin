from dataclasses import dataclass
from functools import cache
from typing import Annotated

import cappa

from fujin.config import Config, Host


@dataclass(frozen=True)
class BaseCommand:
    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    # @cache
    def host(self, config: Config) -> Host:
        if not self._host:
            return config.primary_host
        try:
            return config.hosts[self._host]
        except KeyError as e:
            raise cappa.Exit(f"Host {self._host} does not exist", code=1) from e
