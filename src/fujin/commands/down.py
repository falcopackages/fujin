from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import cappa
import gevent
from rich.prompt import Confirm

from fujin import caddy
from fujin.commands import BaseCommand


@cappa.command(
    help="Tear down the project by stopping services and cleaning up resources"
)
@dataclass
class Down(BaseCommand):
    full: Annotated[
        bool,
        cappa.Arg(
            short="-f",
            long="--full",
            help="Stop and uninstall proxy as part of teardown",
        ),
    ] = False

    def __call__(self):
        try:
            confirm = Confirm.ask(
                f"""[red]You are about to delete all project files, stop all services, 
                and remove all configurations on the host {self.config.host.ip} for the project {self.config.app_name}. 
                Any assets in your project folder will be lost (sqlite not in there ?). 
                Are you sure you want to proceed? This action is irreversible.[/red]""",
            )
        except KeyboardInterrupt:
            raise cappa.Exit("Teardown aborted", code=0)
        if not confirm:
            return
        with self.connection() as conn:
            conn.run(f"rm -rf {self.config.app_dir}")
            if self.config.webserver.enabled:
                caddy.teardown(conn, self.config)

            service_names = self.config.service_names
            # Stop services
            threads = [
                gevent.spawn(conn.run, f"sudo systemctl stop {name}", warn=True)
                for name in service_names
            ]
            gevent.joinall(threads)
            # Disable services
            threads = [
                gevent.spawn(conn.run, f"sudo systemctl disable {name}", warn=True)
                for name in service_names
            ]
            gevent.joinall(threads)
            # Remove service files
            for name in self.config.get_systemd_units():
                conn.run(f"sudo rm /etc/systemd/system/{name}", warn=True)

            conn.run("sudo systemctl daemon-reload")
            conn.run("sudo systemctl reset-failed")

            if self.full and self.config.webserver.enabled:
                caddy.uninstall(conn)
            self.stdout.output(
                "[green]Project teardown completed successfully![/green]"
            )
