from __future__ import annotations

import cappa
from fujin.commands import AppCommand

from .deploy import Deploy


@cappa.command(help="Redeploy the application to apply code and environment changes")
class Redeploy(AppCommand):
    def __call__(self):
        deploy = Deploy(_host=self._host)
        with self.app_environment() as conn:
            hook_manager = self.create_hook_manager(conn)
            hook_manager.pre_deploy()
            deploy.transfer_files(conn)
            deploy.install_project(conn)
            deploy.release(conn)
            self.create_process_manager(conn).restart_services()
            hook_manager.post_deploy()
            self.stdout.output("[green]Redeployment completed successfully![/green]")
