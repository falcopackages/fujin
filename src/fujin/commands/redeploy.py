from __future__ import annotations

import cappa

from fujin.commands.base import HostCommand
from fujin.config import Hook
from .deploy import Deploy


@cappa.command(help="Redeploy the application to apply code and environment changes")
class Redeploy(HostCommand):

    def __call__(self):
        deploy = Deploy(_host=self._host)
        deploy.transfer_files()
        deploy.install_project()
        if pre_deploy := self.config.hooks.get(Hook.PRE_DEPLOY):
            self.host.run(pre_deploy)
        deploy.restart_services()
        self.stdout.output("[green]Redeployment completed successfully![/green]")
