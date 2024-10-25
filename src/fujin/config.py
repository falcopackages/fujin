from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property, cache
from pathlib import Path
from typing import Annotated, ClassVar

import cappa
from tomlkit import parse

from .errors import ImproperlyConfiguredError

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum


    class StrEnum(str, Enum):
        pass

from .host import Host
class Hook(StrEnum):
    PRE_DEPLOY = "pre_deploy"


@dataclass(frozen=True)
class Config:
    app: str
    version: str
    python_version: str
    build_command: str
    distfile: Path
    aliases: dict[str, str]
    hosts: dict[str, Host]
    processes: dict[str, str]
    webserver: Webserver
    envfile: Path | None = None
    requirements: Path = field(default=lambda: Path("requirements.txt"))
    hooks: dict[Hook, str] = field(default=dict)
    # custom_commands: list[str, str] = field(default_factory=list) # list of capp command modules

    bin_dir: ClassVar[str] = ".venv/bin/"
    bin_dir_placeholder: ClassVar[str] = "!"

    @cached_property
    def primary_host(self) -> Host:
        return [host for host in self.hosts.values() if host.primary][0]

    @cached_property
    def web_process(self) -> str:
        return [value for key, value in self.processes.items() if key == "web"][0]

    def get_service_name(self, name: str):
        if name == "web":
            return self.app
        return f"{self.app}-{name}"

    @cached_property
    def services(self) -> list[str]:
        return [self.get_service_name(name) for name in self.processes]

    @classmethod
    def expand_command(cls, command: str) -> str:
        if command.startswith(cls.bin_dir_placeholder):
            return command.replace(cls.bin_dir_placeholder, cls.bin_dir, 1)
        return command

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
            distfile = Path(toml_data["distfile"].format(version=version))
            envfile = Path(toml_data["envfile"])
            hooks = toml_data.get("hooks", {})
            hosts = Host.parse(toml_data["hosts"], app=app)
            processes = toml_data["processes"]
            webserver = toml_data["webserver"]
            # TODO: do something with tasks
        except KeyError as e:
            raise ImproperlyConfiguredError(str(e)) from e

        if "web" not in processes:
            raise ImproperlyConfiguredError("You need to define a web process")

        python_version = toml_data.get("python_version")
        if not python_version:
            py_version_file = Path(".python-version")
            if not py_version_file.exists():
                raise ImproperlyConfiguredError(f"Add a python_version key or a .python-version file")
            python_version = py_version_file.read_text().strip()

        aliases = {
            name: cls.expand_command(command)
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
            hooks=hooks,
            distfile=distfile,
            envfile=envfile,
            webserver=webserver
        )




ConfigDep = Annotated[Config, cappa.Dep(Config.read)]


@dataclass(frozen=True)
class Webserver:
    upstream: str
