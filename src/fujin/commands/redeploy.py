from __future__ import annotations

import cappa

from fujin.commands.base import HostCommand
from fujin.config import ConfigDep, Process
from .deploy import Deploy


@cappa.command(help="Redeploy for code changes and env change")
class Redeploy(HostCommand):

    def __call__(self, config: ConfigDep, output: cappa.Output):
        host = self.host(config)
        Deploy.transfer_files(host, config)
        Deploy.install_project(host, config)
        Deploy.restart_all_services(
            *(Process.service_name(app=config.app, name=p) for p in config.processes), host=host
        )
        output.output("[green]Redeploy complete[/green]")
