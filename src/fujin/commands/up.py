import cappa

from .base import HostCommand
from .deploy import Deploy
from .server import Server


@cappa.command(help="Set")
class Up(HostCommand):

    def __call__(self):
        Server(_host=self._host).bootstrap()
        Deploy(_host=self._host)()
