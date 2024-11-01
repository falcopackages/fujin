from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import cappa
from rich.prompt import Prompt

from fujin.commands import BaseCommand


@cappa.command(
    help="Tear down the project by stopping services and cleaning up resources"
)
@dataclass
class Down(BaseCommand):
    full: Annotated[
        bool, cappa.Arg(short="-f", long="--full", help="Stop and uninstall proxy as part of teardown")] = False
    def __call__(self):
        confirm = Prompt.ask(
            f"""[red]You are about to delete all project files, stop all services, and remove all configurations on the host {self.config.host.ip} for the project {self.config.app_name}. Any assets in your project folder will be lost (sqlite not in there ?). Are you sure you want to proceed? This action is irreversible.[/red]""",
            choices=["no", "yes"],
            default="no",
        )
        if confirm == "no":
            return
        with self.connection() as conn:
            hook_manager = self.create_hook_manager(conn)
            hook_manager.pre_teardown()
            process_manager = self.create_process_manager(conn)
            conn.run(f"rm -rf {self.app_dir}")
            self.create_web_proxy(conn).teardown()
            process_manager.uninstall_services()
            process_manager.reload_configuration()
            if self.full:
                self.create_web_proxy(conn).uninstall()
            hook_manager.post_teardown()
            self.stdout.output(
                "[green]Project teardown completed successfully![/green]"
            )
