from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import cappa

from fujin.commands.base import HostCommand

OutputDep = Annotated[cappa.Output, cappa.Dep(cappa.output.Output)]


@cappa.command(help="Run app related tasks")
@dataclass
class App(HostCommand):

    @cappa.command(help="Run arbitrary command via the app binary")
    def exec(self, command: str, interactive: Annotated[bool, cappa.Arg(default=False, short="-i")]):
        host = self.host(self.config)
        app_bin = f"{self.config.bin_dir}{self.config.app}"
        with host.cd_project_dir():
            if interactive:
                host.connection.run(f"{app_bin} {command}", pty=interactive)
            else:
                result = host.connection.run(f"{app_bin} {command}", hide=True)
                self.stdout.output(result)

    @cappa.command(help="Logs")
    def start(self):
        pass

    @cappa.command(help="Logs")
    def restart(self):
        pass

    @cappa.command(help="Logs")
    def stop(self):
        pass

    @cappa.command(help="Logs")
    def logs(self):
        pass
