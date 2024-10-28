from __future__ import annotations

from dataclasses import dataclass

import cappa
from rich.prompt import Prompt

from fujin.commands import AppCommand


@cappa.command(
    help="Tear down the project by stopping services and cleaning up resources"
)
@dataclass
class Down(AppCommand):

    def __call__(self):
        confirm = Prompt.ask(
            f"""[red]You are about to delete all project files, stop all services, and remove all configurations on the host {self.host} for the project {self.config.app}. Any assets in your project folder will be lost (sqlite not in there ?). Are you sure you want to proceed? This action is irreversible.[/red]""",
            choices=["no", "yes"],
            default="no",
        )
        if confirm == "no":
            return
        with self.connection() as conn:
            self.hook_manager(conn).pre_teardown()
            conn.run(f"rm -rf {self.project_dir}")
            self.web_proxy(conn).teardown()
            self.process_manager(conn).uninstall_services()
            self.process_manager(conn).reload_configuration()
            self.hook_manager(conn).post_teardown()
            self.stdout.output(
                "[green]Project teardown completed successfully![/green]"
            )
