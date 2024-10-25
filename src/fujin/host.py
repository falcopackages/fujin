from __future__ import annotations
from pathlib import Path
import os

from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property

from fabric import Connection
from invoke import Responder

from .errors import ImproperlyConfiguredError

@dataclass(frozen=True)
class Host:
    ip: str
    domain_name: str
    user: str
    project_dir: str | None = None
    password: str | None = field(default=None, init=False)
    password_env: str | None = None
    ssh_port: int = 22
    key_filename: Path | None = None
    envfile: Path | None = None
    primary: bool = False

    @property
    def watchers(self) -> list[Responder]:
        if not self.password:
            return []
        return [Responder(
            pattern=r"\[sudo\] password:",
            response=f"{self.password}\n",
        )]

    @cached_property
    def connection(self) -> Connection:
        connect_kwargs = None
        if self.key_filename:
            connect_kwargs = {"key_filename": str(self.key_filename)}
        elif self.password:
            connect_kwargs = {"password": self.password}
        return Connection(
            self.ip, user=self.user, port=self.ssh_port, connect_kwargs=connect_kwargs
        )

    def run(self, args: str, **kwargs):
        return self.connection.run(args, **kwargs)

    def sudo(self, args: str, **kwargs):
        return self.connection.sudo(args, **kwargs, watchers=self.watchers)

    def run_uv(self, args: str, **kwargs):
        return self.connection.run(f"/home/{self.user}/.cargo/bin/uv {args}", **kwargs)

    def run_caddy(self, args: str, **kwargs):
        return self.connection.run(f"/home/{self.user}/.local/bin/caddy {args}", **kwargs)

    @contextmanager
    def cd_project_dir(self):
        with self.connection.cd(self.project_dir):
            yield

    @classmethod
    def parse(cls, hosts: dict, app: str) -> dict[str, Host]:
        default_project_dir = "/home/{user}/.local/share/fujin/{app}"
        parsed_hosts = {}
        single_host = len(hosts) == 1
        for name, data_ in hosts.items():
            data = data_.copy()
            if password_env := data.get("password_env"):
                password = os.getenv(password_env)
                if not password:
                    msg = f"Env {password_env} can not be found"
                    raise ImproperlyConfiguredError(msg)
            if "ssh_port" in data:
                data["ssh_port"] = int(data.get("ssh_port"))
            if not data.get("project_dir"):
                data["project_dir"] = default_project_dir.format(user=data["user"], app=app)
            if single_host:
                data["primary"] = True
            try:
                print(data)
                parsed_hosts[name] = Host(**data)
            except TypeError as e:
                msg = f"Host {name} misconfigured: {e}"
                raise ImproperlyConfiguredError(msg) from e

        return parsed_hosts
