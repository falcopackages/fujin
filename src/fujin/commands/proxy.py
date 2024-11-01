from dataclasses import dataclass
from pathlib import Path

import cappa

from fujin.commands import AppCommand


@cappa.command(
    help="Manage web proxy."
)
@dataclass
class Proxy(AppCommand):

    @cappa.command(help="Install the proxy on the remote host")
    def install(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).install()

    @cappa.command(help="Uninstall the proxy from the remote host")
    def uninstall(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).uninstall()

    @cappa.command(help="Start the proxy on the remote host")
    def start(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).start()
        self.stdout.output("[green]Proxy started successfully![/green]")

    @cappa.command(help="Stop the proxy on the remote host")
    def stop(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).stop()
        self.stdout.output("[green]Proxy stopped successfully![/green]")

    @cappa.command(help="Restart the proxy on the remote host")
    def restart(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).restart()
        self.stdout.output("[green]Proxy restarted successfully![/green]")

    @cappa.command(help="Check the status of the proxy on the remote host")
    def status(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).status()

    @cappa.command(help="View the logs of the proxy on the remote host")
    def logs(self):
        with self.connection() as conn:
            self.create_web_proxy(conn).logs()

    @cappa.command(name="export-config", help="Export the proxy configuration file locally to the .fujin directory")
    def export_config(self):
        Path(".fujin").mkdir(exist_ok=True)
        with self.connection() as conn:
            self.create_web_proxy(conn).export_config()
