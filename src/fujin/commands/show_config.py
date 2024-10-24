from dataclasses import asdict

import cappa
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fujin.config import ConfigDep


@cappa.command(help="Show parsed configuration")
class ShowConfig:

    def __call__(self, config: ConfigDep):
        console = Console()

        general_config = {
            "app": config.app,
            "version": config.version,
            "build_command": config.build_command,
            "distfile": config.distfile,
            "envfile": config.envfile,
            "release_command": config.release_command or "N/A",
            "requirements": config.requirements
        }
        formatted_text = "\n".join(f"[bold green]{key}:[/bold green] {value}" for key, value in general_config.items())
        console.print(Panel(formatted_text, title="General Configuration", border_style="green", width=100))

        # Hosts Table with headers and each dictionary on its own line
        hosts_table = Table(title="Hosts", header_style="bold cyan")
        hosts_table.add_column("Host", style="dim")
        hosts_table.add_column("ip")
        hosts_table.add_column("domain_name")
        hosts_table.add_column("user")
        hosts_table.add_column("password")
        hosts_table.add_column("project_dr")
        hosts_table.add_column("ssh_port")
        hosts_table.add_column("key_filename")
        hosts_table.add_column("envfile")
        hosts_table.add_column("primary", justify="center")

        for host_name, host in config.hosts.items():
            host_dict = asdict(host)
            hosts_table.add_row(
                host_name,
                host_dict["ip"],
                host_dict["domain_name"],
                host_dict["user"],
                str(host_dict["password"] or "N/A"),
                host_dict.get("project_dir", "N/A"),
                str(host_dict["ssh_port"]),
                str(host_dict["key_filename"] or "N/A"),
                str(host_dict["envfile"] or "N/A"),
                "[green]Yes[/green]" if host_dict["primary"] else "[red]No[/red]"
            )

        console.print(hosts_table)

        # Processes Table with headers and each dictionary on its own line
        processes_table = Table(title="Processes", header_style="bold cyan")
        processes_table.add_column("Process", style="dim")
        processes_table.add_column("Command")
        processes_table.add_column("Port")
        processes_table.add_column("Bind Address")

        for process_name, process in config.processes.items():
            process_dict = asdict(process)
            processes_table.add_row(
                process_name,
                process_dict["command"],
                str(process_dict["port"] or "N/A"),
                process_dict["bind"] or "N/A"
            )

        console.print(processes_table)

        # Aliases Table with one row for headers and one row per dictionary entry
        aliases_table = Table(title="Aliases", header_style="bold cyan")
        aliases_table.add_column("Alias", style="dim")
        aliases_table.add_column("Command")
        for alias, command in config.aliases.items():
            aliases_table.add_row(alias, command)

        console.print(aliases_table)
