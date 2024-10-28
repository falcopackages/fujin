from __future__ import annotations

import secrets
from typing import Annotated

import cappa

from fujin.commands import AppCommand


@cappa.command(help="Manage server operations")
class Server(AppCommand):

    @cappa.command(help="Display information about the host system")
    def info(self):
        with self.connection() as conn:
            result = conn.run(f"command -v fastfetch", warn=True, hide=True)
            if result.ok:
                conn.run("fastfetch", pty=True)
            else:
                self.stdout.output(conn.run("cat /etc/os-release", hide=True).stdout)

    @cappa.command(help="Setup uv, web proxy, and install necessary dependencies")
    def bootstrap(self):
        with self.connection() as conn:
            self.hook_manager.pre_bootstrap()
            conn.run("sudo apt update")
            conn.run("sudo apt upgrade -y")
            conn.run("sudo apt install -y sqlite3 curl")
            result = conn.run("command -v uv", warn=True)
            if not result.ok:
                conn.run("curl -LsSf https://astral.sh/uv/install.sh | sh")
                conn.run("uv tool update-shell")
            conn.run("uv tool install fastfetch-bin-edge")
            self.web_proxy(conn).install()
            self.hook_manager.post_bootstrap()
            self.stdout.output(
                "[green]Server bootstrap completed successfully![/green]"
            )

    @cappa.command(help="Stop and uninstall the web proxy")
    def uninstall_proxy(self):
        with self.connection() as conn:
            self.web_proxy(conn).uninstall()

    @cappa.command(
        help="Execute an arbitrary command on the server, optionally in interactive mode"
    )
    def exec(
        self,
        command: str,
        interactive: Annotated[bool, cappa.Arg(default=False, short="-i")],
    ):
        with self.connection() as conn:
            if interactive:
                conn.run(command, pty=interactive, warn=True)
            else:
                self.stdout.output(conn.run(command, hide=True).stdout)

    @cappa.command(
        name="create-user", help="Create a new user with sudo and ssh access"
    )
    def create_user(
        self,
        name: str,
        with_password: Annotated[bool, cappa.Arg(long="--with-password")] = False,
    ):
        with self.connection() as conn:
            conn.run(f"sudo adduser --disabled-password --gecos '' {name}")
            conn.run(f"sudo mkdir -p /home/{name}/.ssh")
            conn.run(f"sudo cp ~/.ssh/authorized_keys /home/{name}/.ssh/")
            conn.run(f"sudo chown -R {name}:{name} /home/{name}/.ssh")
            if with_password:
                password = secrets.token_hex(8)
                conn.run(f"echo '{name}:{password}' | sudo chpasswd")
                self.stdout.output(f"[green]Generated password: [/green]{password}")
            conn.run(f"sudo chmod 700 /home/{name}/.ssh")
            conn.run(f"sudo chmod 600 /home/{name}/.ssh/authorized_keys")
            conn.run(f"echo '{name} ALL=(ALL) NOPASSWD:ALL' | sudo tee -a /etc/sudoers")
            self.stdout.output(f"[green]New user {name} created successfully![/green]")
