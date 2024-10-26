import cappa

from .base import HostCommand
from .deploy import Deploy
from .server import Server


@cappa.command(help="Run everything required to deploy an application to a fresh host.")
class Up(HostCommand):

    def __call__(self):
        Server(_host=self._host).bootstrap()
        Deploy(_host=self._host)()
        self.stdout.output("[green]Server bootstrapped and application deployed successfully![/green]")
