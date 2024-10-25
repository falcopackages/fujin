import cappa

from fujin.config import ConfigDep
from .base import HostCommand
from .deploy import Deploy
from .server import Bootstrap


@cappa.command(help="Set")
class Up(HostCommand):

    def __call__(self, config: ConfigDep, output: cappa.Output):
        Bootstrap(_host=self._host)(config=config, output=output)
        Deploy(_host=self._host)(config=config, output=output)
