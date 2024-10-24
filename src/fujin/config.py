from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property, cache
from pathlib import Path
from typing import Annotated

import cappa
from fabric import Connection
from invoke import Responder
from tomlkit import parse


class ImproperlyConfiguredError(cappa.Exit):
    code = 1


# TODO: move these dataclasses to attrs or msgspec, should simplify some part of the logic and do type conversion in a declarative way

@dataclass(frozen=True)
class Config:
    app: str
    version: str
    python_version: str
    build_command: str
    distfile: Path
    aliases: dict[str, str]
    hosts: dict[str, Host]
    processes: dict[str, Process]
    tasks: dict[str, str] = field(default_factory=dict)
    release_command: str | None = None
    envfile: Path | None = None
    requirements: Path = Path("requirements.txt")

    @cached_property
    def primary_host(self) -> Host:
        return [host for host in self.hosts.values() if host.primary][0]

    @cached_property
    def web_process(self) -> Process:
        return [process for name, process in self.processes.items() if name == "web"][0]

    @classmethod
    @cache
    def read(cls) -> Config:
        fujin_toml = Path("fujin.toml")
        if not fujin_toml.exists():
            raise ImproperlyConfiguredError(
                "No fujin.toml file found in the current directory"
            )

        toml_data = parse(fujin_toml.read_text())
        app = toml_data.get("app")
        if not app:
            try:
                app = parse(Path("pyproject.toml").read_text())["project"]["name"]
            except (FileNotFoundError, KeyError) as e:
                raise ImproperlyConfiguredError(
                    f"Add an app key or a pyproject.toml file with a key project.name") from e

        version = toml_data.get("version")
        if not version:
            try:
                version = parse(Path("pyproject.toml").read_text())["project"]["version"]
            except (FileNotFoundError, KeyError) as e:
                raise ImproperlyConfiguredError(
                    f"Add a version key or a pyproject.toml file with a key project.version") from e

        try:
            requirements = toml_data["requirements"]
            build_command = toml_data["build_command"]
            release_command = _expand_command(toml_data["release_command"])
            distfile = Path(toml_data["distfile"].format(version=version))
            envfile = Path(toml_data["envfile"])
            hosts = Host.parse(toml_data["hosts"], app=app)
            processes = Process.parse(toml_data["processes"])
            # TODO: do something with tasks
        except KeyError as e:
            raise ImproperlyConfiguredError(str(e)) from e

        python_version = toml_data.get("python_version")
        if not python_version:
            py_version_file = Path(".python-version")
            if not py_version_file.exists():
                raise ImproperlyConfiguredError(f"Add a python_version key or a .python-version file")
            python_version = py_version_file.read_text().strip()

        aliases = {
            name: _expand_command(command)
            for name, command in toml_data.get("aliases", {}).items()
        }

        return cls(
            app=app,
            version=version,
            python_version=python_version,
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
        self.connection.run(args, **kwargs)

    def run_uv(self, args: str, **kwargs):
        self.connection.run(f"/home/{self.user}/.cargo/bin/uv {args}", **kwargs)

    def run_caddy(self, args: str, **kwargs):
        self.connection.run(f"/home/{self.user}/.local/bin/caddy {args}", **kwargs)

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
            # if "ssh_port" in data:
            data["ssh_port"] = 3000  # int(data.get("ssh_port"))
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


@dataclass(frozen=True)
class Process:
    command: str
    port: int | None = None
    bind: str | None = None

    @classmethod
    def parse(cls, processes: dict) -> [str, Process]:
        parsed_processes = {}
        for name, data in processes.items():
            try:
                p = cls(bind=data.get("bind"), port=data.get("port"), command=_expand_command(data["command"]))
            except TypeError as e:
                msg = f"Process {name} misconfigured: {e}"
                raise ImproperlyConfiguredError(msg) from e
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
