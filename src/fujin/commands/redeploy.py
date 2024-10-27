from __future__ import annotations

import cappa

from fujin.commands import AppCommand

from .deploy import Deploy


@cappa.command(help="Redeploy the application to apply code and environment changes")
class Redeploy(AppCommand):

    def __call__(self):
        self.hook_manager.pre_deploy()
        deploy = Deploy(_host=self._host)
        deploy.transfer_files()
        deploy.install_project()
        deploy.release()
        self.process_manager.restart_services()
        self.stdout.output("[green]Redeployment completed successfully![/green]")
