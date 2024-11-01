from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cappa
import tomli_w
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import fujin.config
from fujin.commands import BaseCommand
from fujin.config import tomllib


@cappa.command(name="config", help="Manage application configuration")
class ConfigCMD(BaseCommand):
    @cappa.command(help="Display the parsed configuration")
    def show(self):
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

    @cappa.command(help="Generate a sample configuration file")
    def init(
        self,
        profile: Annotated[
            str, cappa.Arg(choices=["simple", "falco"], short="-p", long="--profile")
        ] = "simple",
    ):
        fujin_toml = Path("fujin.toml")
        if fujin_toml.exists():
            raise cappa.Exit("fujin.toml file already exists", code=1)
        profile_to_func = {"simple": simple_config, "falco": falco_config}
        app_name = Path().resolve().stem.replace("-", "_").replace(" ", "_").lower()
        config = profile_to_func[profile](app_name)
        fujin_toml.write_text(tomli_w.dumps(config))
        self.stdout.output(
            "[green]Sample configuration file generated successfully![/green]"
        )

    @cappa.command(help="Config documentation")
    def docs(self):
        docs = f"""
        # Fujin Configuration
        {fujin.config.__doc__}
        """
        self.stdout.output(docs)


def simple_config(app_name: str) -> dict:
    config = {
        "app": app_name,
        "version": "0.1.0",
        "build_command": "uv build && uv pip compile pyproject.toml -o requirements.txt",
        "distfile": f"dist/{app_name}-{{version}}-py3-none-any.whl",
        "webserver": {
            "upstream": "localhost:8000",
            "type": "fujin.proxies.caddy",
        },
        "release_command": f"{app_name} migrate",
        "processes": {
            "web": f".venv/bin/gunicorn {app_name}.wsgi:app --bind 0.0.0.0:8000"
        },
        "aliases": {"shell": "server exec --appenv -i bash"},
        "host": {
            "ip": "127.0.0.1",
            "user": "root",
            "domain_name": f"{app_name}.com",
            "envfile": ".env.prod",
        },
    }
    if not Path(".python-version").exists():
        config["python_version"] = "3.12"
    pyproject_toml = Path("pyproject.toml")
    if pyproject_toml.exists():
        pyproject = tomllib.loads(pyproject_toml.read_text())
        config["app"] = pyproject.get("project", {}).get("name", app_name)
        if pyproject.get("project", {}).get("version"):
            # fujin will read the version itself from the pyproject
            config.pop("version")
    return config


def falco_config(app_name: str) -> dict:
    config = simple_config(app_name)
    config.update(
        {
            "release_command": f"{config['app']} setup",
            "processes": {
                "web": f".venv/bin/{config['app']} prodserver",
                "worker": f".venv/bin/{config['app']} qcluster",
            },
            "aliases": {
                "console": "app exec -i shell_plus",
                "dbconsole": "app exec -i dbshell",
                "print_settings": "app exec print_settings --format=pprint",
                "shell": "server exec --appenv -i bash",
            },
        }
    )
    return config
