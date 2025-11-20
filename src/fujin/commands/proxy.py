from dataclasses import dataclass
from typing import Annotated

import cappa
from rich.prompt import Confirm

from fujin.commands import BaseCommand


@cappa.command(help="Manage web proxy.")
@dataclass
class Proxy(BaseCommand):
    def _get_proxy(self, conn):
        proxy = self.create_web_proxy(conn)
        if not proxy:
            raise cappa.Exit("No proxy configured", code=1)
        return proxy

    @cappa.command(help="Install the proxy on the remote host")
    def install(self):
        with self.connection() as conn:
            self._get_proxy(conn).install()
        self.stdout.output("[green]Proxy installed successfully![/green]")

    @cappa.command(help="Uninstall the proxy from the remote host")
    def uninstall(self):
        try:
            confirm = Confirm.ask(
                f"[red]Uninstalling the proxy will remove all current configurations. Are you sure you want to proceed?"
            )
        except KeyboardInterrupt:
            raise cappa.Exit("Teardown aborted", code=0)
        if not confirm:
            return
        with self.connection() as conn:
            self._get_proxy(conn).uninstall()
        self.stdout.output("[green]Proxy uninstalled successfully![/green]")

    @cappa.command(help="Start the proxy on the remote host")
    def start(self):
        with self.connection() as conn:
            self._get_proxy(conn).start()
        self.stdout.output("[green]Proxy started successfully![/green]")

    @cappa.command(help="Stop the proxy on the remote host")
    def stop(self):
        with self.connection() as conn:
            self._get_proxy(conn).stop()
        self.stdout.output("[green]Proxy stopped successfully![/green]")

    @cappa.command(help="Restart the proxy on the remote host")
    def restart(self):
        with self.connection() as conn:
            self._get_proxy(conn).restart()
        self.stdout.output("[green]Proxy restarted successfully![/green]")

    @cappa.command(help="Check the status of the proxy on the remote host")
    def status(self):
        with self.connection() as conn:
            self._get_proxy(conn).status()

    @cappa.command(help="View the logs of the proxy on the remote host")
    def logs(self):
        with self.connection() as conn:
            self._get_proxy(conn).logs()
