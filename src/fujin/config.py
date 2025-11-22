"""
Fujin uses a **fujin.toml** file at the root of your project for configuration. Below are all available configuration options.

app
---
The name of your project or application. Must be a valid Python package name.

version
--------
The version of your project to build and deploy. If not specified, automatically parsed from **pyproject.toml** under *project.version*.

python_version
--------------
The Python version for your virtualenv. If not specified, automatically parsed from **.python-version** file. This is only
required if the installation mode is set to **python-package**

requirements
------------
Optional path to your requirements file. This will only be used when the installation mode is set to *python-package*

versions_to_keep
----------------
The number of versions to keep on the host. After each deploy, older versions are pruned based on this setting. By default, it keeps the latest 5 versions,
set this to `None` to never automatically prune.

build_command
-------------
The command to use to build your project's distribution file.

distfile
--------
Path to your project's distribution file. This should be the main artifact containing everything needed to run your project on the server.
Supports version placeholder, e.g., **dist/app_name-{version}-py3-none-any.whl**

installation_mode
-----------------

Indicates whether the *distfile* is a Python package or a self-contained executable. The possible values are *python-package* and *binary*.
The *binary* option disables specific Python-related features, such as virtual environment creation and requirements installation. ``fujin`` will assume the provided
*distfile* already contains all the necessary dependencies to run your program.

release_command
---------------
Optional command to run at the end of deployment (e.g., database migrations) before your application is started.

secrets
-------

Optional secrets configuration. If set, ``fujin`` will load secrets from the specified secret management service.
Check out the `secrets </secrets.html>`_ page for more information.

adapter
~~~~~~~
The secret management service to use. The currently available options are *bitwarden*, *1password*, *doppler*

password_env
~~~~~~~~~~~~
Environment variable containing the password for the service account. This is only required for certain adapters.

Webserver
---------

Web server configurations.

type
~~~~
The reverse proxy implementation to use. Available options:

- *fujin.proxies.caddy* (default)
- *fujin.proxies.nginx*
- *fujin.proxies.dummy* (disables proxy)

upstream
~~~~~~~~
The address where your web application listens for requests. Supports any value compatible with your chosen web proxy:

- HTTP address (e.g., *localhost:8000* )
- Unix socket caddy (e.g., *unix//run/project.sock* )
- Unix socket nginx (e.g., *http://unix:/run/project.sock* )

certbot_email
~~~~~~~~~~~~~
Required when Nginx is used as a proxy to obtain SSL certificates.

statics
~~~~~~~

Defines the mapping of URL paths to local directories for serving static files. The syntax and support for static
file serving depend on the selected reverse proxy. The directories you map should be accessible by the web server, meaning
with read permissions for the *www-data* group; a reliable choice is **/var/www**.

Example:

.. code-block:: toml
    :caption: fujin.toml

    [webserver]
    upstream = "unix//run/project.sock"
    type = "fujin.proxies.caddy"
    statics = { "/static/*" = "/var/www/myproject/static/" }

processes
---------

A mapping of process names to commands that will be managed by the process manager. Define as many processes as needed, but
when using any proxy other than *fujin.proxies.dummy*, a *web* process must be declared.

Example:

.. code-block:: toml
    :caption: fujin.toml

    [processes]
    web = ".venv/bin/gunicorn myproject.wsgi:application"


.. note::

    Commands are relative to your *app_dir*. When generating systemd service files, the full path is automatically constructed.
    Refer to the *apps_dir* setting on the host to understand how *app_dir* is determined.
    Here are the templates for the service files:

    - `web.service <https://github.com/falcopackages/fujin/blob/main/src/fujin/templates/web.service>`_
    - `web.socket <https://github.com/falcopackages/fujin/blob/main/src/fujin/templates/web.socket>`_
    - `simple.service <https://github.com/falcopackages/fujin/blob/main/src/fujin/templates/simple.service>`_ (for all additional processes)

Host Configuration
-------------------

ip
~~
The IP address or anything that resolves to the remote host IP's. This is use to communicate via ssh with the server, if omitted it's value will default to the one of the *domain_name*.

domain_name
~~~~~~~~~~~
The domain name pointing to this host. Used for web proxy configuration.

user
~~~~
The login user for running remote tasks. Should have passwordless sudo access for optimal operation.

.. note::

    You can create a user with these requirements using the ``fujin server create-user`` command.

envfile
~~~~~~~
Path to the production environment file that will be copied to the host.

env
~~~
A string containing the production environment variables. In combination with the secrets manager, this is most useful when
you want to automate deployment through a CI/CD platform like GitLab CI or GitHub Actions. For an example of how to do this,
check out the `integrations guide </integrations.html>`_

.. important::

    *envfile* and *env* are mutually exclusive—you can define only one.

apps_dir
~~~~~~~~

Base directory for project storage on the host. Path is relative to user's home directory.
Default: **.local/share/fujin**. This value determines your project's **app_dir**, which is **{apps_dir}/{app}**.

password_env
~~~~~~~~~~~~

Environment variable containing the user's password. Only needed if the user cannot run sudo without a password.

ssh_port
~~~~~~~~

SSH port for connecting to the host. Default to **22**.

key_filename
~~~~~~~~~~~~

Path to the SSH private key file for authentication. Optional if using your system's default key location.

aliases
-------

A mapping of shortcut names to Fujin commands. Allows you to create convenient shortcuts for commonly used commands.

Example:

.. code-block:: toml
    :caption: fujin.toml

    [aliases]
    console = "app exec -i shell_plus" # open an interactive django shell
    dbconsole = "app exec -i dbshell" # open an interactive django database shell
    shell = "server exec --appenv -i bash" # SSH into the project directory with environment variables loaded

hooks
-----
Run custom scripts at specific points with hooks. Check out the `hooks </hooks.html>`_ page for more information.

"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import msgspec
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from .errors import ImproperlyConfiguredError

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


class InstallationMode(StrEnum):
    PY_PACKAGE = "python-package"
    BINARY = "binary"


class SecretAdapter(StrEnum):
    BITWARDEN = "bitwarden"
    ONE_PASSWORD = "1password"
    DOPPLER = "doppler"
    SYSTEM = "system"


class SecretConfig(msgspec.Struct):
    adapter: SecretAdapter
    password_env: str | None = None


class ProcessConfig(msgspec.Struct):
    command: str
    replicas: int = 1
    socket: bool = False
    timer: str | None = None

    def __post_init__(self):
        if self.socket and self.timer:
            raise ImproperlyConfiguredError(
                "A process cannot have both 'socket' and 'timer' enabled."
            )


class Config(msgspec.Struct, kw_only=True):
    app_name: str = msgspec.field(name="app")
    version: str = msgspec.field(default_factory=lambda: read_version_from_pyproject())
    versions_to_keep: int | None = 5
    python_version: str | None = None
    build_command: str
    release_command: str | None = None
    installation_mode: InstallationMode
    distfile: str
    aliases: dict[str, str] = msgspec.field(default_factory=dict)
    host: HostConfig
    processes: dict[str, ProcessConfig] = msgspec.field(default_factory=dict)
    webserver: Webserver
    requirements: str | None = None
    local_config_dir: Path = Path(".fujin")
    secret_config: SecretConfig | None = msgspec.field(
        name="secrets",
        default_factory=lambda: SecretConfig(adapter=SecretAdapter.SYSTEM),
    )

    def __post_init__(self):
        if self.installation_mode == InstallationMode.PY_PACKAGE:
            if not self.python_version:
                self.python_version = find_python_version()

        if "web" not in self.processes and self.webserver.enabled:
            raise ImproperlyConfiguredError(
                "Missing web process or set the proxy enabled to False to disable the use of a proxy"
            )

    @property
    def app_bin(self) -> str:
        if self.installation_mode == InstallationMode.PY_PACKAGE:
            return f".venv/bin/{self.app_name}"
        return self.app_name

    @property
    def app_dir(self) -> str:
        return f"{self.host.apps_dir}/{self.app_name}"

    def get_release_dir(self, version: str | None = None) -> str:
        return f"{self.app_dir}/v{version or self.version}"

    def get_distfile_path(self, version: str | None = None) -> Path:
        version = version or self.version
        return Path(self.distfile.format(version=version))

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

    def get_service_name(self, process_name: str) -> str:
        config = self.processes[process_name]
        suffix = "@.service" if config.replicas > 1 else ".service"
        if process_name == "web":
            return f"{self.app_name}{suffix}"
        return f"{self.app_name}-{process_name}{suffix}"

    def get_process_service_names(self, process_name: str) -> list[str]:
        config = self.processes[process_name]
        service_name = self.get_service_name(process_name)
        if config.replicas > 1:
            base = service_name.replace("@.service", "")
            return [f"{base}@{i}.service" for i in range(1, config.replicas + 1)]
        return [service_name]

    @property
    def service_names(self) -> list[str]:
        services = []
        for name in self.processes:
            services.extend(self.get_process_service_names(name))
        for name, config in self.processes.items():
            if config.socket:
                services.append(f"{self.app_name}.socket")
            if config.timer:
                service_name = self.get_service_name(name)
                services.append(f"{service_name.replace('.service', '')}.timer")
        return services

    def get_systemd_units(self) -> dict[str, str]:
        package_templates = (
            Path(importlib.util.find_spec("fujin").origin).parent / "templates"
        )
        search_paths = [self.local_config_dir, package_templates]
        env = Environment(loader=FileSystemLoader(search_paths))

        context = {
            "app_name": self.app_name,
            "user": self.host.user,
            "app_dir": self.app_dir,
        }

        files = {}
        for name, config in self.processes.items():
            service_name = self.get_service_name(name)
            process_name = service_name.replace(".service", "")
            command = config.command
            process_config = config

            # Try to find a specific template for the process, otherwise use default
            try:
                template = env.get_template(f"{name}.service.j2")
            except TemplateNotFound:
                template = env.get_template("default.service.j2")

            body = template.render(
                **context,
                command=command,
                process_name=process_name,
                process=process_config,
            )
            files[service_name] = body

            if process_config.socket:
                socket_name = f"{self.app_name}.socket"
                try:
                    template = env.get_template(f"{name}.socket.j2")
                except TemplateNotFound:
                    template = env.get_template("default.socket.j2")
                body = template.render(**context)
                files[socket_name] = body

            if process_config.timer:
                timer_name = f"{service_name.replace('.service', '')}.timer"
                try:
                    template = env.get_template(f"{name}.timer.j2")
                except TemplateNotFound:
                    template = env.get_template("default.timer.j2")
                body = template.render(
                    **context,
                    process_name=process_name,
                    process=process_config,
                )
                files[timer_name] = body

        return files

    def get_caddyfile(self) -> str:
        package_templates = (
            Path(importlib.util.find_spec("fujin").origin).parent / "templates"
        )
        search_paths = [self.local_config_dir, package_templates]
        env = Environment(loader=FileSystemLoader(search_paths))
        template = env.get_template("Caddyfile.j2")
        return template.render(
            domain_name=self.host.domain_name,
            upstream=self.webserver.upstream,
            statics=self.webserver.statics,
        )


class HostConfig(msgspec.Struct, kw_only=True):
    ip: str | None = None
    domain_name: str
    user: str
    _env_file: str | None = msgspec.field(name="envfile", default=None)
    env_content: str | None = msgspec.field(name="env", default=None)
    apps_dir: str = ".local/share/fujin"
    password_env: str | None = None
    ssh_port: int = 22
    _key_filename: str | None = msgspec.field(name="key_filename", default=None)

    def __post_init__(self):
        if self._env_file and self.env_content:
            raise ImproperlyConfiguredError(
                "Cannot set both 'env' and 'envfile' properties."
            )
        if self._env_file:
            envfile = Path(self._env_file)
            if not envfile.exists():
                raise ImproperlyConfiguredError(f"{self._env_file} not found")
            self.env_content = envfile.read_text()
        self.env_content = self.env_content.strip() if self.env_content else ""
        self.apps_dir = f"/home/{self.user}/{self.apps_dir}"
        self.ip = self.ip or self.domain_name

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
    enabled: bool = True
    statics: dict[str, str] = msgspec.field(default_factory=dict)


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
