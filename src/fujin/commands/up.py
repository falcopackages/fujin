import cappa
from fujin.commands import BaseCommand

from .deploy import Deploy
from .server import Server


@cappa.command(help="Run everything required to deploy an application to a fresh host.")
class Up(BaseCommand):
    def __call__(self):
        Server().bootstrap()
        Deploy()()
        self.stdout.output(
            "[green]Server bootstrapped and application deployed successfully![/green]"
        )
