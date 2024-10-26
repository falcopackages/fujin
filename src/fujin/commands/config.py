from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cappa
import tomli_w
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from fujin.commands import BaseCommand
from fujin.config import tomllib


@cappa.command(name="config", help="Manage application configuration")
class ConfigCMD(BaseCommand):

    @cappa.command(help="Display the parsed configuration")
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
        config = profile_to_func[profile]()
        fujin_toml.write_text(tomli_w.dumps(config))
        self.stdout.output(
            "[green]Sample configuration file generated successfully![/green]"
        )

    @cappa.command(help="Config documentation")
    def docs(self):
        self.stdout.output(Markdown(docs))


def simple_config() -> dict:
    app = Path().resolve().stem.replace("-", "_").replace(" ", "_").lower()

    config = {
        "app": app,
        "version": "0.1.0",
        "build_command": "uv build",
        "distfile": f"dist/{app}-{{version}}-py3-none-any.whl",
        "webserver": {
            "upstream": "localhost:8000",
            "type": "fujin.proxies.caddy",
        },
        "hooks": {"pre_deploy": f".venv/bin/{app} migrate"},
        "processes": {"web": f".venv/bin/gunicorn {app}.wsgi:app --bind 0.0.0.0:8000"},
        "aliases": {"shell": "server exec -i bash"},
        "hosts": {
            "primary": {
                "ip": "127.0.0.1",
                "user": "root",
                "domain_name": f"{app}.com",
                "envfile": ".env.prod",
                "default": True,
            }
        },
    }
    if not Path(".python-version").exists():
        config["python_version"] = "3.12"
    pyproject_toml = Path("pyproject.toml")
    if pyproject_toml.exists():
        pyproject = tomllib.loads(pyproject_toml.read_text())
        config["app"] = pyproject.get("project", {}).get("name", app)
        if pyproject.get("project", {}).get("version"):
            # fujin will read the version itself from the pyproject
            config.pop("version")
    return config


def falco_config() -> dict:
    config = simple_config()
    config.update(
        {
            "hooks": {"pre_deploy": f".venv/bin/{config['app']} setup"},
            "processes": {
                "web": f".venv/bin/{config['app']} prodserver",
                "worker": f".venv/bin/{config['app']} qcluster",
            },
            "aliases": {
                "console": "app exec -i shell_plus",
                "dbconsole": "app exec -i dbshell",
                "print_settings": "app exec print_settings --format=pprint",
                "shell": "server exec -i bash",
            },
        }
    )
    return config


docs = """
# Fujin Configuration
"""
