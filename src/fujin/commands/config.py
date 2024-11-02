from __future__ import annotations

import cappa
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fujin.commands import BaseCommand


@cappa.command(name="config", help="Display your current configuration")
class ConfigCMD(BaseCommand):
    def __call__(self):
        console = Console()
        general_config = {
            "app": self.config.app_name,
            "app_bin": self.config.app_bin,
            "version": self.config.version,
            "python_version": self.config.python_version,
            "build_command": self.config.build_command,
            "release_command": self.config.release_command,
            "distfile": self.config.distfile,
            "requirements": self.config.requirements,
            "webserver": f"{{ upstream = '{self.config.webserver.upstream}', type = '{self.config.webserver.type}' }}",
        }
        general_config_text = "\n".join(
            f"[bold green]{key}:[/bold green] {value}"
            for key, value in general_config.items()
        )
        console.print(
            Panel(
                general_config_text,
                title="General Configuration",
                border_style="green",
                width=100,
            )
        )

        host_config_text = "\n".join(
            f"[dim]{key}:[/dim] {value}"
            for key, value in self.config.host.to_dict().items()
        )
        console.print(
            Panel(
                host_config_text,
                title="Host Configuration",
                width=100,
            )
        )

        # Processes Table with headers and each dictionary on its own line
        processes_table = Table(title="Processes", header_style="bold cyan")
        processes_table.add_column("Name", style="dim")
        processes_table.add_column("Command")
        for name, command in self.config.processes.items():
            processes_table.add_row(name, command)
        console.print(processes_table)

        aliases_table = Table(title="Aliases", header_style="bold cyan")
        aliases_table.add_column("Alias", style="dim")
        aliases_table.add_column("Command")
        for alias, command in self.config.aliases.items():
            aliases_table.add_row(alias, command)

        console.print(aliases_table)
