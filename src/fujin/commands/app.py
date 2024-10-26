from __future__ import annotations

from typing import Annotated

import cappa

from fujin.commands import AppCommand


@cappa.command(help="Run application-related tasks")
class App(AppCommand):

    @cappa.command(help="Run an arbitrary command via the application binary")
    def exec(
        self,
        command: str,
        interactive: Annotated[bool, cappa.Arg(default=False, short="-i")],
    ):
        with self.host.cd_project_dir(self.config.app):
            if interactive:
                self.host.run(f"{self.config.app_bin} {command}", pty=interactive)
            else:
                result = self.host.run(f"{self.config.app_bin} {command}", hide=True)
                self.stdout.output(result)

    @cappa.command(
        help="Start the specified service or all services if no name is provided"
    )
    def start(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        self.process_manager.start_services(name)
        msg = f"{name} Service" if name else "All Services"
        self.stdout.output(f"[green]{msg} started successfully![/green]")

    @cappa.command(
        help="Restart the specified service or all services if no name is provided"
    )
    def restart(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        self.process_manager.restart_services(name)
        msg = f"{name} Service" if name else "All Services"
        self.stdout.output(f"[green]{msg} restarted successfully![/green]")

    @cappa.command(
        help="Stop the specified service or all services if no name is provided"
    )
    def stop(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        self.process_manager.stop_services(name)
        msg = f"{name} Service" if name else "All Services"
        self.stdout.output(f"[green]{msg} stopped successfully![/green]")

    @cappa.command(help="Show logs for the specified service")
    def logs(
        self, name: Annotated[str, cappa.Arg(help="Service name")], follow: bool = False
    ):
        # TODO: flash out this more
        self.process_manager.service_logs(name=name, follow=follow)
