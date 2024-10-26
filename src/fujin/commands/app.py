from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import cappa

from fujin.commands.base import HostCommand


@cappa.command(help="Run app related tasks")
@dataclass
class App(HostCommand):

    @cappa.command(help="Run arbitrary command via the app binary")
    def exec(
        self,
        command: str,
        interactive: Annotated[bool, cappa.Arg(default=False, short="-i")],
    ):
        with self.host.cd_project_dir(self.config.app):
            if interactive:
                self.host.connection.run(
                    f"{self.config.app_bin} {command}", pty=interactive
                )
            else:
                result = self.host.connection.run(
                    f"{self.config.app_bin} {command}", hide=True
                )
                self.stdout.output(result)

    def _service_run(self, action: str, name: str | None):
        options = [*self.config.services, "all"]
        if name and name not in options:
            raise cappa.Exit(
                f"{name} is not a valid service name, available options: {options}",
                code=1,
            )
        if name == "all":
            for name_ in self.config.services:
                self.host.sudo(f"systemctl {action} {name_}")
        else:
            self.host.sudo(f"systemctl {action} {name}")

    @cappa.command(help="Logs")
    def start(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        self._service_run(action="start", name=name)

    @cappa.command(help="Logs")
    def restart(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        self._service_run(action="restart", name=name)

    @cappa.command(help="Logs")
    def stop(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        self._service_run(action="stop", name=name)

    @cappa.command(help="Logs")
    def logs(
        self, name: Annotated[str, cappa.Arg(help="Service name")], follow: bool = False
    ):
        # TODO: flash out this more
        self.host.sudo(f"journalctl -u {name} -r {'-f' if follow else ''}")
