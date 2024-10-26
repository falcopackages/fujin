from __future__ import annotations

from typing import Annotated

import cappa

from fujin.commands import AppCommand


@cappa.command(help="Manage server operations")
class Server(AppCommand):

    @cappa.command(help="Display information about the host system")
    def info(self):
        self.stdout.output(self.host.sudo("cat /etc/os-release", hide="out"))

    @cappa.command(help="Setup uv, web proxy, and install necessary dependencies")
    def bootstrap(self):
        self.host.sudo("apt update")
        self.host.sudo("apt upgrade -y")
        self.host.sudo("apt install -y sqlite3 curl")
        result = self.host.run("source $HOME/.cargo/env && command -v uv", warn=True)
        if not result.ok:
            self.host.run("curl -LsSf https://astral.sh/uv/install.sh | sh")
            self.host.run_uv("tool update-shell")
        self.web_proxy.install()
        self.stdout.output("[green]Server bootstrap completed successfully![/green]")

    @cappa.command(
        help="Execute an arbitrary command on the server, optionally in interactive mode"
    )
    def exec(
        self,
        command: str,
        interactive: Annotated[bool, cappa.Arg(default=False, short="-i")],
    ):
        if interactive:
            self.host.run(command, pty=interactive)
        else:
            result = self.host.run(command, hide=True)
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
        self.stdout.output(f"[green]New user {name} created successfully![/green]")
