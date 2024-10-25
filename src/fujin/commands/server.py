from __future__ import annotations

from typing import Annotated

import cappa

from fujin.commands.base import HostCommand


@cappa.command(help="Server management")
class Server(HostCommand):

    @cappa.command(help="Show host info")
    def info(self):
        self.stdout.output(self.host.sudo("cat /etc/os-release", hide="out"))

    @cappa.command(help="Setup uv, caddy and install some dependencies")
    def bootstrap(self):
        self.host.sudo("apt update")
        self.host.sudo("apt upgrade -y")
        self.host.sudo("apt install -y sqlite3 curl")
        result = self.host.run("source $HOME/.cargo/env && command -v uv", warn=True)
        if not result.ok:
            self.host.run("curl -LsSf https://astral.sh/uv/install.sh | sh")
            self.host.run_uv("tool update-shell")
        self.config.webserver.get_proxy(host=self.host, config=self.config).install()
        self.stdout.output("[green]Server bootstrap Done![/green]")

    @cappa.command(help="Run arbitrary command on the server")
    def exec(
        self,
        command: str,
        interactive: Annotated[bool, cappa.Arg(default=False, short="-i")],
    ):
        if interactive:
            self.host.connection.run(command, pty=interactive)
        else:
            result = self.host.connection.run(command, hide=True)
            self.stdout.output(result)

    @cappa.command(
        name="create-user", help="Create a new user with sudo and ssh access"
    )
    def create_user(self, name: str):
        # TODO not working right now, ssh key not working
        self.host.sudo(f"adduser --disabled-password --gecos '' {name}")
        self.host.sudo(f"mkdir -p /home/{name}/.ssh")
        self.host.sudo(f"cp ~/.ssh/authorized_keys /home/{name}/.ssh/")
        self.host.sudo(f"chown -R {name}:{name} /home/{name}/.ssh")
        self.host.sudo(f"chmod 700 /home/{name}/.ssh")
        self.host.sudo(f"chmod 600 /home/{name}/.ssh/authorized_keys")
        self.host.sudo(
            f"echo '{name} ALL=(ALL) NOPASSWD:ALL' | sudo tee -a /etc/sudoers"
        )
        self.stdout.output(f"[green]New user {name} created[/green]")
