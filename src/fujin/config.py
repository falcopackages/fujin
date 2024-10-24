from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Annotated

import cappa
from fabric import Connection
from invoke import Responder
from tomlkit import parse


class ImproperlyConfiguredError(Exception):
    pass


@dataclass
class Config:
    app: str
    version: str
    build_command: str
    distfile: str
    envfile: Path
    aliases: dict[str, str]
    hosts: dict[str, Host]
    processes: dict[str, Process]
    tasks: dict[str, str] = field(default_factory=dict)
    release_command: str | None = None
    requirements: Path = Path("requirements.txt")

    @cached_property
    def primary_host(self) -> Host:
        return [host for host in self.hosts.values() if host.primary][0]

    @classmethod
    @lru_cache
    def read(cls) -> Config:
        fujin_toml = Path("fujin.toml")
        if not fujin_toml.exists():
            raise ImproperlyConfiguredError(
                "No fujin.toml file found in the current directory"
            )

        toml_data = parse(fujin_toml.read_text())

        try:
            app = toml_data["app"]
            version = toml_data["version"]
            requirements = toml_data["requirements"]
            build_command = toml_data["build_command"]
            release_command = _expand_command(toml_data["release_command"])
            distfile = toml_data["distfile"].format(version=version)
            envfile = Path(toml_data["envfile"])
            hosts = Host.parse(toml_data["hosts"], app=app)
            processes = Process.parse(toml_data["processes"])
            # TODO: do something with tasks
        except KeyError as e:
            raise ImproperlyConfiguredError(str(e)) from e

        aliases = {
            name: _expand_command(command)
            for name, command in toml_data.get("aliases", {}).items()
        }

        return cls(
            app=app,
            version=version,
            aliases=aliases,
            processes=processes,
            hosts=hosts,
            requirements=requirements,
            build_command=build_command,
            release_command=release_command,
            distfile=distfile,
            envfile=envfile,
        )


ConfigDep = Annotated[Config, cappa.Dep(Config.read)]


@dataclass
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

    def run_uv(self, args: str, **kwargs):
        self.connection.run(f"/home/{self.user}/.cargo/bin/uv {args}", **kwargs)

    def run_caddy(self, args: str, **kwargs):
        self.connection.run(f"/home/{self.user}/.local/bin/caddy {args}", **kwargs)

    @classmethod
    def parse(cls, hosts: dict, app: str) -> dict[str, Host]:
        default_project_dir = "/home/{user}/.local/share/fujin/{app}"
        parsed_hosts = {}
        single_host = len(hosts) == 1
        for name, data in hosts.items():
            try:
                h = Host(**data)
            except TypeError as e:
                msg = f"Host {name} misconfigured: {e}"
                raise ImproperlyConfiguredError(msg) from e
            if h.password_env:
                password = os.getenv(h.password_env)
                if not password:
                    msg = f"Env {h.password_env} can not be found"
                    raise ImproperlyConfiguredError(msg)
                h.password = password
            h.ssh_port = int(h.ssh_port)
            if not h.project_dir:
                h.project_dir = default_project_dir.format(user=h.user, app=app)
            if single_host:
                h.primary = True
            parsed_hosts[name] = h
        return parsed_hosts


@dataclass
class Process:
    command: str
    port: int | None = None
    bind: str | None = None

    @classmethod
    def parse(cls, processes: dict) -> [str, Process]:
        parsed_processes = {}
        for name, data in processes.items():
            try:
                p = cls(**data)
            except TypeError as e:
                msg = f"Process {name} misconfigured: {e}"
                raise ImproperlyConfiguredError(msg) from e
            p.command = _expand_command(p.command)
            if p.bind and p.port:
                msg = f"Process {name} misconfigured: cannot have both bind and port property set at the same time"
                raise ImproperlyConfiguredError(msg)
            if name == "web" and (not p.bind and not p.port):
                msg = f"Process {name} misconfigured: need to have at least on of port or bind property set for the web process"
                raise ImproperlyConfiguredError(msg)
            parsed_processes[name] = p
        if "web" not in parsed_processes:
            msg = "You need to have at least one process name web"
            raise ImproperlyConfiguredError(msg)
        return parsed_processes


bin_dir = ".venv/bin/"
bin_dir_placeholder = "!"


def _expand_command(command: str):
    if command.startswith(bin_dir_placeholder):
        return command.replace(bin_dir_placeholder, bin_dir, 1)
    return command
