import cappa

from fujin.config import ConfigDep
from .base import BaseCommand
from .deploy import Deploy
from .server import Bootstrap


@cappa.command(help="Set")
class Up(BaseCommand):

    def __call__(self, config: ConfigDep, output: cappa.Output):
        Bootstrap(_host=self._host)(config=config, output=output)
        Deploy(_host=self._host)(config=config, output=output)
