from __future__ import annotations

from typing import Annotated

import cappa
import gevent
from rich.table import Table


from fujin.commands import BaseCommand
from fujin.config import InstallationMode, ProcessConfig


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
                "rollback_targets": (
                    ", ".join(rollback_targets.split("\n"))
                    if rollback_targets
                    else "N/A"
                ),
            }
            if self.config.installation_mode == InstallationMode.PY_PACKAGE:
                infos["python_version"] = self.config.python_version

            services_status = self._get_services_status(conn)

            services = {}
            for process_name in self.config.processes:
                service_names = self.config.get_process_service_names(process_name)
                running_count = sum(
                    1 for name in service_names if services_status.get(name, False)
                )
                total_count = len(service_names)

                if total_count == 1:
                    services[process_name] = services_status.get(
                        service_names[0], False
                    )
                else:
                    services[process_name] = f"{running_count}/{total_count}"

            socket_name = f"{self.config.app_name}.socket"
            if socket_name in services_status:
                services["socket"] = services_status[socket_name]

        infos_text = "\n".join(f"{key}: {value}" for key, value in infos.items())

        table = Table(title="", header_style="bold cyan")
        table.add_column("Process", style="")
        table.add_column("Running?")
        for service, status in services.items():
            if isinstance(status, bool):
                status_str = (
                    "[bold green]Yes[/bold green]"
                    if status
                    else "[bold red]No[/bold red]"
                )
            else:
                running, total = map(int, status.split("/"))
                if running == total:
                    status_str = f"[bold green]{status}[/bold green]"
                elif running == 0:
                    status_str = f"[bold red]{status}[/bold red]"
                else:
                    status_str = f"[bold yellow]{status}[/bold yellow]"

            table.add_row(service, status_str)

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
            names = self._resolve_service_names(name)
            threads = [
                gevent.spawn(conn.run, f"sudo systemctl start {name}", pty=True)
                for name in names
            ]
            gevent.joinall(threads)
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
            names = self._resolve_service_names(name)
            threads = [
                gevent.spawn(conn.run, f"sudo systemctl restart {name}", pty=True)
                for name in names
            ]
            gevent.joinall(threads)
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
            names = self._resolve_service_names(name)
            threads = [
                gevent.spawn(conn.run, f"sudo systemctl stop {name}", pty=True)
                for name in names
            ]
            gevent.joinall(threads)
        msg = f"{name} Service" if name else "All Services"
        self.stdout.output(f"[green]{msg} stopped successfully![/green]")

    @cappa.command(help="Show logs for the specified service")
    def logs(
        self, name: Annotated[str, cappa.Arg(help="Service name")], follow: bool = False
    ):
        # TODO: flash out this more
        with self.app_environment() as conn:
            names = self._resolve_service_names(name)
            if names:
                conn.run(
                    f"sudo journalctl -u {names[0]} {'-f' if follow else ''}",
                    warn=True,
                    pty=True,
                )

    def _resolve_service_names(self, name: str | None) -> list[str]:
        if not name:
            return self.config.service_names

        if name in self.config.processes:
            return self.config.get_process_service_names(name)

        if name == "socket":
            has_socket = any(config.socket for config in self.config.processes.values())
            if has_socket:
                return [f"{self.config.app_name}.socket"]

        return [name]

    def _get_services_status(self, conn) -> dict[str, bool]:
        names = self.config.service_names
        threads = {
            name: gevent.spawn(
                conn.run,
                f"sudo systemctl is-active {name}",
                warn=True,
                hide=True,
            )
            for name in names
        }
        gevent.joinall(threads.values())
        return {
            name: thread.value.stdout.strip() == "active"
            for name, thread in threads.items()
        }
