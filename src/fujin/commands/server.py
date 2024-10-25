from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import cappa
from cappa.output import Output

from fujin.commands.base import HostCommand
from fujin.config import ConfigDep


@cappa.command(help="Server management")
class Server:
    subcommands: cappa.Subcommands[Bootstrap | Exec | CreateUser]


@cappa.command(help="Setup uv, caddy and install some dependencies")
@dataclass
class Bootstrap(HostCommand):
    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    def __call__(self, config: ConfigDep, output: Output):
        host = self.host(config)
        host.connection.sudo("apt update", watchers=host.watchers)
        host.connection.sudo("apt upgrade -y", watchers=host.watchers)
        host.connection.sudo("apt install -y sqlite3 curl", watchers=host.watchers)
        r = host.connection.run("whereis uv").stdout.strip()[2:]
        print(r)
        uv_is_installed = r != ""
        if not uv_is_installed:
            host.connection.run("curl -LsSf https://astral.sh/uv/install.sh | sh")
            host.run_uv("tool update-shell")
        host.run_uv("tool install caddy-bin")
        host.run_caddy("start", pty=True)
        output.output("[green]Server bootstrap Done![/green]")


@cappa.command(help="Run arbitrary command on the server")
@dataclass
class Exec(HostCommand):
    command: str
    interactive: Annotated[bool, cappa.Arg(default=False, short="-i")]

    def __call__(self, config: ConfigDep, output: Output):
        host = self.host(config)
        if self.interactive:
            host.connection.run(self.command, pty=self.interactive)
        else:
            result = host.connection.run(self.command, hide=True)
            output.output(result)


@cappa.command(help="Create a new user with sudo and ssh access")
@dataclass
class CreateUser(HostCommand):
    name: str

    def __call__(self, config: ConfigDep, output: Output):
        # TODO not working right now, ssh key not working
        host = self.host(config)
        host.connection.sudo(f"adduser --disabled-password --gecos '' {self.name}")
        host.connection.sudo(f"mkdir -p /home/{self.name}/.ssh")
        host.connection.sudo(f"cp ~/.ssh/authorized_keys /home/{self.name}/.ssh/")
        host.connection.sudo(f"chown -R {self.name}:{self.name} /home/{self.name}/.ssh")
        host.connection.sudo(f"chmod 700 /home/{self.name}/.ssh")
        host.connection.sudo(f"chmod 600 /home/{self.name}/.ssh/authorized_keys")
        host.connection.sudo(f"echo '{self.name} ALL=(ALL) NOPASSWD:ALL' | sudo tee -a /etc/sudoers")
        output.output(f"[green]New user {self.name} created[/green]")
