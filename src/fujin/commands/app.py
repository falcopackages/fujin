from __future__ import annotations

from typing import Annotated

import cappa
from fujin.commands import BaseCommand


@cappa.command(help="Run application-related tasks")
class App(BaseCommand):
    @cappa.command(help="Display information about the application")
    def info(self):
        # TODO: add info / details command that will list all services with their current status, if they are installed or running or stopped
        # systemctl is-enabled  to check is a service is enabled
        with self.app_environment() as conn:
            infos = {
                "app_name": self.config.app_name,
                "app_bin": self.config.app_bin,
                "version": self.config.version,
                "python_version": self.config.python_version,
                "services": ", ".join(
                    s for s in self.create_process_manager(conn).service_names
                ),
            }
        formatted_text = "\n".join(
            f"[bold green]{key}:[/bold green] {value}" for key, value in infos.items()
        )
        self.stdout.output(formatted_text)

    @cappa.command(help="Run an arbitrary command via the application binary")
    def exec(
        self,
        command: str,
        interactive: Annotated[bool, cappa.Arg(default=False, short="-i")],
    ):
        with self.app_environment() as conn:
            if interactive:
                conn.run(f"{self.config.app_bin} {command}", pty=interactive, warn=True)
            else:
                self.stdout.output(
                    conn.run(f"{self.config.app_bin} {command}", hide=True).stdout
                )

    @cappa.command(
        help="Start the specified service or all services if no name is provided"
    )
    def start(
        self,
        name: Annotated[
            str | None, cappa.Arg(help="Service name, no value means all")
        ] = None,
    ):
        with self.app_environment() as conn:
            self.create_process_manager(conn).start_services(name)
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
        with self.app_environment() as conn:
            self.create_process_manager(conn).restart_services(name)
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
        with self.app_environment() as conn:
            self.create_process_manager(conn).stop_services(name)
        msg = f"{name} Service" if name else "All Services"
        self.stdout.output(f"[green]{msg} stopped successfully![/green]")

    @cappa.command(help="Show logs for the specified service")
    def logs(
        self, name: Annotated[str, cappa.Arg(help="Service name")], follow: bool = False
    ):
        # TODO: flash out this more
        with self.app_environment() as conn:
            self.create_process_manager(conn).service_logs(name=name, follow=follow)

    @cappa.command(
        name="export-config",
        help="Export the service configuration files locally to the .fujin directory",
    )
    def export_config(
        self,
        overwrite: Annotated[
            bool, cappa.Arg(help="overwrite any existing config file")
        ] = False,
    ):
        with self.connection() as conn:
            for filename, content in self.create_process_manager(
                conn
            ).get_configuration_files(ignore_local=True):
                local_config = self.config.local_config_dir / filename
                if local_config.exists() and not overwrite:
                    self.stdout.output(
                        f"[blue]Skipping {filename}, file already exists. Use --overwrite to replace it.[/blue]"
                    )
                    continue
                local_config.write_text(content)
                self.stdout.output(f"[green]{filename} exported successfully![/green]")
