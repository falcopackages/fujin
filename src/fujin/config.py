from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec

from .errors import ImproperlyConfiguredError
from .proxies import WebProxy

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


if TYPE_CHECKING:
    from .host import Host


class Hook(StrEnum):
    PRE_DEPLOY = "pre_deploy"



def read_version_from_pyproject():
    try:
        return tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    except (FileNotFoundError, KeyError) as e:
        raise msgspec.ValidationError(
            "Project version was not found in the pyproject.toml file, define it manually"
        ) from e


def find_python_version():
    py_version_file = Path(".python-version")
    if not py_version_file.exists():
        raise msgspec.ValidationError(
            f"Add a python_version key or a .python-version file"
        )
    return py_version_file.read_text().strip()


class Config(msgspec.Struct, kw_only=True):
    app: str
    app_bin: str = ".venv/bin/{app}"
    version: str = msgspec.field(default_factory=read_version_from_pyproject)
    python_version: str = msgspec.field(default_factory=find_python_version)
    build_command: str
    _distfile: str = msgspec.field(name="distfile")
    aliases: dict[str, str]
    hosts: dict[str, HostConfig]
    processes: dict[str, str]
    webserver: Webserver
    _requirements: str = msgspec.field(name="requirements", default="requirements.txt")
    hooks: dict[Hook, str] = msgspec.field(default=dict)

    def __post_init__(self):
        self.app_bin = self.app_bin.format(app=self.app)
        self._distfile = self._distfile.format(version=self.version)

        if "web" not in self.processes and self.webserver.type != "fujin.proxies.dummy":
            raise ValueError(
                "Missing web process or set the proxy to 'fujin.proxies.dummy' to disable the use of a proxy"
            )

    @property
    def distfile(self) -> Path:
        return Path(self._distfile)

    @property
    def requirements(self) -> Path:
        return Path(self._requirements)

    @property
    def web_process(self) -> str:
        return [value for key, value in self.processes.items() if key == "web"][0]

    def get_service_name(self, name: str):
        if name == "web":
            return self.app
        return f"{self.app}-{name}"

    @property
    def services(self) -> list[str]:
        return [self.get_service_name(name) for name in self.processes]

    @classmethod
    def read(cls) -> Config:
        fujin_toml = Path("fujin.toml")
        if not fujin_toml.exists():
            raise ImproperlyConfiguredError(
                "No fujin.toml file found in the current directory"
            )
        try:
            return msgspec.toml.decode(fujin_toml.read_text(), type=cls)
        except msgspec.ValidationError as e:
            raise ImproperlyConfiguredError(str(e)) from e


class HostConfig(msgspec.Struct, kw_only=True):
    ip: str
    domain_name: str
    user: str
    _envfile: str = msgspec.field(name="envfile")
    projects_dir: str = "/home/{user}/.local/share/fujin"
    password_env: str | None = None
    ssh_port: int = 22
    _key_filename: str | None = msgspec.field(name="key_filename", default=None)
    default: bool = False

    def __post_init__(self):
        self.projects_dir = self.projects_dir.format(user=self.user)

    def to_dict(self):
        return {f: getattr(self, f) for f in self.__struct_fields__}

    @property
    def envfile(self) -> Path:
        return Path(self._envfile)

    @property
    def key_filename(self) -> Path | None:
        if self._key_filename:
            return Path(self._key_filename)

    @property
    def password(self) -> str | None:
        if not self.password_env:
            return
        password = os.getenv(self.password_env)
        if not password:
            msg = f"Env {self.password_env} can not be found"
            raise ImproperlyConfiguredError(msg)
        return password


class Webserver(msgspec.Struct):
    upstream: str
    type: str = "fujin.proxies.caddy"

    def get_proxy(self, host: Host, config: Config) -> WebProxy:
        module = importlib.import_module(self.type)
        try:
            return getattr(module, "WebProxy")(host=host, config=config)
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing proxy class in {self.type}"
            ) from e
