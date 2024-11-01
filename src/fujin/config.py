"""
Fujin uses a ``fujin.toml`` file at the root of your project for configuration. Below are all available configuration options.

app
---
The name of your project or application. Must be a valid Python package name.

app_bin
-------
Path to your application's executable. Used by the **app** subcommand for remote execution.
Default: ``.venv/bin/{app}``

version
--------
The version of your project to build and deploy. If not specified, automatically parsed from ``pyproject.toml`` under ``project.version``.

python_version
--------------
The Python version for your virtualenv. If not specified, automatically parsed from ``.python-version`` file.

build_command
-------------
The command used to build your project's distribution file.

distfile
--------
Path to your project's distribution file. This should be the main artifact containing everything needed to run your project on the server.
Supports version placeholder, e.g., ``dist/app_name-{version}-py3-none-any.whl``

release_command
---------------
Optional command to run at the end of deployment (e.g., database migrations).

skip_project_install
--------------------
If ``true``, skips virtualenv creation and project installation. Useful when customizing project installation via hooks.

requirements
------------
Path to your requirements file.
Default: ``requirements.txt``

Webserver
---------

type
~~~~
The reverse proxy implementation to use. Available options:

- ``fujin.proxies.caddy`` (default)
- ``fujin.proxies.nginx``
- ``fujin.proxies.dummy`` (disables proxy functionality)

upstream
~~~~~~~~
The address where your web application listens for requests. Supports any value compatible with your chosen web proxy:

- HTTP address (e.g., ``localhost:8000``)
- Unix socket (e.g., ``unix:/run/project.sock``)

Example:

.. code-block:: toml

    [webserver]
    upstream = "unix:/run/project.sock"
    type = "fujin.proxies.caddy"

processes
---------

A mapping of process names to commands that will be managed by your process manager. Define as many processes as needed, but
when using any proxy other than ``fujin.proxies.dummy``, a ``web`` process must be declared.

Example:

.. code-block:: toml

    [processes]
    web = ".venv/bin/gunicorn myproject.wsgi:application"


.. note::

    Commands are relative to your ``app_dir``. When generating systemd service files, the full path is automatically constructed.

Host Configuration
-------------------

ip
~~
The IP address or hostname of the remote host.

domain_name
~~~~~~~~~~~
The domain name pointing to this host. Used for web proxy configuration.

user
~~~~
The login user for running remote tasks. Should have passwordless sudo access for optimal operation.

envfile
~~~~~~~
Path to the production environment file that will be copied to the host.

apps_dir
~~~~~~~~
Base directory for project storage on the host. Path is relative to user's home directory.
Default: ``.local/share/fujin``

password_env
~~~~~~~~~~~~
Environment variable containing the user's password. Only needed if the user cannot run sudo without a password.

ssh_port
~~~~~~~~
SSH port for connecting to the host.
Default: ``22``

key_filename
~~~~~~~~~~~~
Path to SSH private key file for authentication.

default
~~~~~~~
Marks this host as the default when ``--host`` option isn't provided. Automatically set to ``true`` if only one host is configured.

aliases
-------

A mapping of shortcut names to Fujin commands. Allows you to create convenient shortcuts for commonly used commands.

Example:

.. code-block:: toml

    [aliases]
    console = "app exec -i shell_plus" # open an interactive django shell
    dbconsole = "app exec -i dbshell" # open an interactive django database shell
    shell = "server exec --appenv -i bash" # SSH into the project directory with environment variables loaded


"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import msgspec

from .errors import ImproperlyConfiguredError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .hooks import HooksDict


class Config(msgspec.Struct, kw_only=True):
    app_name: str = msgspec.field(name="app")
    app_bin: str = ".venv/bin/{app}"
    version: str = msgspec.field(default_factory=lambda: read_version_from_pyproject())
    python_version: str = msgspec.field(default_factory=lambda: find_python_version())
    build_command: str
    release_command: str | None = None
    skip_project_install: bool = False
    _distfile: str = msgspec.field(name="distfile")
    aliases: dict[str, str] = msgspec.field(default=dict)
    hosts: dict[str, HostConfig]
    processes: dict[str, str] = msgspec.field(default=dict)
    process_manager: str = "fujin.process_managers.systemd"
    webserver: Webserver
    _requirements: str = msgspec.field(name="requirements", default="requirements.txt")
    hooks: HooksDict = msgspec.field(default=dict)
    local_config_dir: Path = Path(".fujin")

    def __post_init__(self):
        self.app_bin = self.app_bin.format(app=self.app_name)
        self._distfile = self._distfile.format(version=self.version)

        if len(self.hosts) == 1:
            host = next(iter(self.hosts.values()))
            host.default = True

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
            raise ImproperlyConfiguredError(f"Improperly configured, {e}") from e


class HostConfig(msgspec.Struct, kw_only=True):
    ip: str
    domain_name: str
    user: str
    _envfile: str = msgspec.field(name="envfile")
    apps_dir: str = ".local/share/fujin"
    password_env: str | None = None
    ssh_port: int = 22
    _key_filename: str | None = msgspec.field(name="key_filename", default=None)
    default: bool = False

    def __post_init__(self):
        self.apps_dir = f"/home/{self.user}/{self.apps_dir}"

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

    def get_app_dir(self, app_name: str) -> str:
        return f"{self.apps_dir}/{app_name}"


class Webserver(msgspec.Struct):
    upstream: str
    type: str = "fujin.proxies.caddy"


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
