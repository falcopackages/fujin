from __future__ import annotations

from dataclasses import asdict

import cappa
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from fujin.commands.base import BaseCommand


@cappa.command(name="config", help="Config management")
class ConfigCMD(BaseCommand):

    @cappa.command(help="Show parsed configuration")
    def show(self):
        console = Console()

        general_config = {
            "app": self.config.app,
            "app_bin": self.config.app_bin,
            "version": self.config.version,
            "python_version": self.config.python_version,
            "build_command": self.config.build_command,
            "distfile": self.config.distfile,
            "requirements": self.config.requirements,
            "webserver":f"{{ upstream = {self.config.webserver.upstream} }}"
        }
        formatted_text = "\n".join(f"[bold green]{key}:[/bold green] {value}" for key, value in general_config.items())
        console.print(Panel(formatted_text, title="General Configuration", border_style="green", width=100))

        # Hosts Table with headers and each dictionary on its own line
        hosts_table = Table(title="Hosts", header_style="bold cyan")
        hosts_table.add_column("Host", style="dim")
        hosts_table.add_column("ip")
        hosts_table.add_column("domain_name")
        hosts_table.add_column("user")
        hosts_table.add_column("password_env")
        hosts_table.add_column("project_dr")
        hosts_table.add_column("ssh_port")
        hosts_table.add_column("key_filename")
        hosts_table.add_column("envfile")
        hosts_table.add_column("primary", justify="center")

        for host_name, host in self.config.hosts.items():
            host_dict = host.to_dict()
            hosts_table.add_row(
                host_name,
                host_dict["ip"],
                host_dict["domain_name"],
                host_dict["user"],
                str(host_dict["password_env"] or "N/A"),
                host_dict.get("project_dir", "N/A"),
                str(host_dict["ssh_port"]),
                str(host_dict["_key_filename"] or "N/A"),
                host_dict["_envfile"],
                "[green]Yes[/green]" if host_dict["default"] else "[red]No[/red]"
            )

        console.print(hosts_table)

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

    @cappa.command(help="Generate a sample configuration file")
    def init(self):
        pass

    @cappa.command(help="Config documentation")
    def docs(self):
        self.stdout.output(Markdown(docs))


docs = """
# Fujin Configuration - Quick Reference

## Global Options

- `app` - Name of the project (e.g., "bookstore").
- `version` - Project version (e.g., "0.1.0").
- `requirements` - Path to the requirements file (e.g., "requirements.txt").
- `build_command` - Command to build the project (e.g., "uv build").
- `release_command` - Post-deployment command (e.g., migrations).
- `distfile` - Path to the distribution file (e.g., "dist/bookstore-{version}.whl").
- `envfile` - Path to the environment file (e.g., ".env.prod").

## Aliases

- Define shortcuts for commands:
  - `console` = `!bookstore shell_plus`
  - `migrate` = `!bookstore migrate`
  - `shell_plus` = `!bookstore shell_plus`

## Processes

- Web process example:
  - `port = 8000`
  - `command = !bookstore prodserver`
- Worker process example:
  - `command = !bookstore qcluster`

## Hosts

- Host configuration example:
  - `ip = "127.0.0.1"`
  - `domain_name = "mybookstore.com"`
  - `user = "test"`
  - `password_env` (Optional) = `"TEST_PASSWORD"`
  - `key_filename` (Optional) = `"./id_rsa"`
  - `ssh_port` (Optional) = `2222`
"""
