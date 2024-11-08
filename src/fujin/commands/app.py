from __future__ import annotations

from typing import Annotated

import cappa

from fujin.commands import BaseCommand
from fujin.config import InstallationMode


@cappa.command(help="Run application-related tasks")
class App(BaseCommand):
    @cappa.command(help="Display information about the application")
    def info(self):
        with self.app_environment() as conn:
            remote_version = (
                conn.run("head -n 1 .versions", warn=True, hide=True).stdout.strip()
                or "N/A"
            )
            rollback_targets = conn.run(
                "sed -n '2,$p' .versions", warn=True, hide=True
            ).stdout.strip()
            infos = {
                "app_name": self.config.app_name,
                "app_dir": self.app_dir,
                "app_bin": self.config.app_bin,
                "local_version": self.config.version,
                "remote_version": remote_version,
                "rollback_targets": ", ".join(rollback_targets.split("\n"))
                if rollback_targets
                else "N/A",
            }
            if self.config.installation_mode == InstallationMode.PY_PACKAGE:
                infos["python_version"] = self.config.python_version
            pm = self.create_process_manager(conn)
            services: dict[str, bool] = pm.is_active()

        infos_text = "\n".join(f"{key}: {value}" for key, value in infos.items())
        from rich.table import Table

        table = Table(title="", header_style="bold cyan")
        table.add_column("Service", style="")
        table.add_column("Running?")
        for service, is_active in services.items():
            table.add_row(
                service,
                "[bold green]Yes[/bold green]"
                if is_active
                else "[bold red]No[/bold red]",
            )

        self.stdout.output(infos_text)
        self.stdout.output(table)

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
