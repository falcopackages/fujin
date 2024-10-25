from __future__ import annotations

from pathlib import Path

import cappa
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from fujin.commands.base import BaseCommand
import tomli_w
from fujin.config import tomllib

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
            "webserver": f"{{ upstream = '{self.config.webserver.upstream}', type = '{self.config.webserver.type}' }}",
        }
        formatted_text = "\n".join(
            f"[bold green]{key}:[/bold green] {value}"
            for key, value in general_config.items()
        )
        console.print(
            Panel(
                formatted_text,
                title="General Configuration",
                border_style="green",
                width=100,
            )
        )

        # Hosts Table with headers and each dictionary on its own line
        hosts_table = Table(title="Hosts", header_style="bold cyan")
        hosts_table.add_column("Host", style="dim")
        hosts_table.add_column("ip")
        hosts_table.add_column("domain_name")
        hosts_table.add_column("user")
        hosts_table.add_column("password_env")
        hosts_table.add_column("projects_dr")
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
                host_dict["projects_dir"],
                str(host_dict["ssh_port"]),
                str(host_dict["_key_filename"] or "N/A"),
                host_dict["_envfile"],
                "[green]Yes[/green]" if host_dict["default"] else "[red]No[/red]",
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
        fujin_toml = Path("fujin.toml")
        if fujin_toml.exists():
            raise cappa.Exit("fujin.toml file already exists", code=1)
        # fujin_toml.touch()
        config = {}
        pyproject_toml = Path("pyproject.toml")
        guessed_app = Path().resolve().stem.replace("-", "_").replace(" ", "_").lower()
        if pyproject_toml.exists():
            pyproject = tomllib.loads(pyproject_toml.read_text())
            app = pyproject.get("project", {}).get("name")
            if not app:
                config["app"] = guessed_app
            if not pyproject.get("project", {}).get("version"):
                config["version"] = "0.1.0"
        else:
            config['app'] = guessed_app
            config["version"] = "0.1.0"
        config["build_command"] = "uv build"
        config["distfile"] = f"dist/{guessed_app}" + "-{version}-py3-none-any.whl"
        if not Path(".python-version").exists():
            config["python_version"] = "3.12"
        config["webserver"] = {"upstream": "localhost:8000", "type": "fujin.proxies.caddy"}
        config["hooks"] = {"pre_deploy": f".venv/bin/{guessed_app} migrate"}
        config["processes"] = {"web": f".venv/bin/gunicorn {guessed_app}.wsgi:app --bind 0.0.0.0:8000"}
        config["aliases"] = {"shell": "server exec -i bash"}
        config["hosts"] = {"primary": {"ip": "127.0.0.1", "user": "root", "domain_name": f"{guessed_app}.com", "envfile": ".env.prod", "default": True}}
        fujin_toml.write_text(tomli_w.dumps(config))
        self.stdout.output("[green]Sample configuration file generated[/green]")


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
