import importlib
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated

import cappa
from fabric import Connection
from invoke import Responder
from invoke.exceptions import UnexpectedExit
from paramiko.ssh_exception import (
    AuthenticationException,
    NoValidConnectionsError,
    SSHException,
)

from fujin.config import Config, HostConfig
from fujin.errors import ImproperlyConfiguredError
from fujin.hooks import HookManager
from fujin.process_managers import ProcessManager
from fujin.proxies import WebProxy


@dataclass
class BaseCommand:
    @cached_property
    def config(self) -> Config:
        return Config.read()

    @cached_property
    def stdout(self) -> cappa.Output:
        return cappa.Output()


@dataclass
class AppCommand(BaseCommand):
    """
    A command that provides access to the selected host and provide a connection to interact with it,
    including configuring the web proxy and managing systemd services.
    """

    _host: Annotated[str | None, cappa.Arg(long="--host", value_name="HOST")]

    @cached_property
    def host_config(self) -> HostConfig:
        if not self._host:
            host_config = next(
                (hc for hc in self.config.hosts.values() if hc.default), None
            )
            if not host_config:
                raise ImproperlyConfiguredError(
                    "No default host has been configured, either pass --host or set the default in your fujin.toml file"
                )
        else:
            host_config = next(
                (
                    hc
                    for name, hc in self.config.hosts.items()
                    if self._host in [name, hc.ip]
                ),
                None,
            )
        if not host_config:
            raise cappa.Exit(f"Host {self._host} does not exist", code=1)
        return host_config

    @cached_property
    def project_dir(self) -> str:
        return f"{self.host_config.projects_dir}/{self.config.app}"

    @cached_property
    def watchers(self) -> list[Responder]:
        if not self.host_config.password:
            return []
        return [
            Responder(
                pattern=r"\[sudo\] password:",
                response=f"{self.host_config.password}\n",
            )
        ]

    @contextmanager
    def connection(self) -> Connection:
        connect_kwargs = None
        if self.host_config.key_filename:
            connect_kwargs = {"key_filename": str(self.host_config.key_filename)}
        elif self.host_config.password:
            connect_kwargs = {"password": self.host_config.password}
        conn = Connection(
            self.host_config.ip,
            user=self.host_config.user,
            port=self.host_config.ssh_port,
            connect_kwargs=connect_kwargs,
        )
        try:
            with conn.prefix(
                f'export PATH="/home/{self.host_config.user}/.cargo/bin:/home/{self.host_config.user}/.local/bin:$PATH"'
            ):
                yield conn
        except AuthenticationException as e:
            msg = f"Authentication failed for {self.host_config.user}@{self.host_config.ip} -p {self.host_config.ssh_port}.\n"
            if self.host_config.key_filename:
                msg += f"An SSH key was provided at {self.host_config.key_filename.resolve()}. Please verify its validity and correctness."
            elif self.host_config.password:
                msg += f"A password was provided through the environment variable {self.host_config.password_env}. Please ensure it is correct for the user {self.host_config.user}."
            else:
                msg += "No password or SSH key was provided. Ensure your current host has SSH access to the target host."
            raise cappa.Exit(msg, code=1) from e
        except (UnexpectedExit, NoValidConnectionsError) as e:
            raise cappa.Exit(str(e), code=1) from e
        except SSHException as e:
            raise cappa.Exit(f"{e}, are you using the correct user?", code=1) from e

    @contextmanager
    def app_environment(self) -> Connection:
        with self.connection() as conn:
            with conn.cd(self.project_dir):
                with conn.prefix("source envrun"):
                    yield conn

    @cached_property
    def web_proxy_class(self) -> type:
        module = importlib.import_module(self.config.webserver.type)
        try:
            return getattr(module, "WebProxy")
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing WebProxy class in {self.config.webserver.type}"
            ) from e

    def web_proxy(self, conn: Connection) -> WebProxy:
        return self.web_proxy_class(
            conn=conn, config=self.config, domain_name=self.host_config.domain_name
        )

    @cached_property
    def process_manager_class(self) -> type:
        module = importlib.import_module(self.config.process_manager)
        try:
            return getattr(module, "ProcessManager")
        except KeyError as e:
            raise ImproperlyConfiguredError(
                f"Missing ProcessManager class in {self.config.process_manager}"
            ) from e

    def process_manager(self, conn: Connection) -> ProcessManager:
        return self.process_manager_class(
            conn=conn,
            config=self.config,
            user=self.host_config.user,
            project_dir=self.project_dir,
        )

    def hook_manager(self, conn: Connection) -> HookManager:
        return HookManager(conn=conn, hooks=self.config.hooks, app=self.config.app)
