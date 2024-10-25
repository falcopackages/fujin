from __future__ import annotations

import cappa

from fujin.commands.base import HostCommand
from .deploy import Deploy


@cappa.command(help="Redeploy for code changes and env change")
class Redeploy(HostCommand):

    def __call__(self):
        deploy = Deploy(_host=self._host)
        deploy.transfer_files()
        deploy.install_project()
        deploy.restart_services()
        self.stdout.output("[green]Redeploy complete[/green]")
