from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

import cappa
from fabric import Connection
from invoke import Responder
from invoke.exceptions import UnexpectedExit
from paramiko.ssh_exception import AuthenticationException

if TYPE_CHECKING:
    from .config import HostConfig


@dataclass(frozen=True)
class Host:
    app: str
    config: HostConfig

    def __str__(self):
        return self.config.ip

    @cached_property
    def project_dir(self) -> str:
        return f"{self.config.projects_dir}/{self.app}"

    @cached_property
    def watchers(self) -> list[Responder]:
        if not self.config.password:
            return []
        return [
            Responder(
                pattern=r"\[sudo\] password:",
                response=f"{self.config.password}\n",
            )
        ]

    @cached_property
    def connection(self) -> Connection:
        connect_kwargs = None
        if self.config.key_filename:
            connect_kwargs = {"key_filename": str(self.config.key_filename)}
        elif self.config.password:
            connect_kwargs = {"password": self.config.password}

        return Connection(
            self.config.ip,
            user=self.config.user,
            port=self.config.ssh_port,
            connect_kwargs=connect_kwargs,
        )

    def run(self, args: str, **kwargs):
        try:
            return self.connection.run(args, **kwargs, watchers=self.watchers)
        except AuthenticationException as e:
            msg = f"Authentication failed for {self.config.user}@{self.config.ip} -p {self.config.ssh_port}.\n"
            if self.config.key_filename:
                msg += f"An SSH key was provided at {self.config.key_filename.resolve()}. Please verify its validity and correctness."
            elif self.config.password:
                msg += f"A password was provided through the environment variable {self.config.password_env}. Please ensure it is correct for the user {self.config.user}."
            else:
                msg += "No password or SSH key was provided. Ensure your current host has SSH access to the target host."
            raise cappa.Exit(msg, code=1) from e
        except UnexpectedExit as e:
            raise cappa.Exit(str(e), code=1) from e

    def put(self, *args, **kwargs):
        return self.connection.put(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.connection.get(*args, **kwargs)

    def sudo(self, args: str, **kwargs):
        return self.connection.sudo(args, **kwargs)

    def run_uv(self, args: str, **kwargs):
        return self.run(f"/home/{self.config.user}/.cargo/bin/uv {args}", **kwargs)

    def make_project_dir(self):
        self.run(f"mkdir -p {self.project_dir}")

    @contextmanager
    def cd_project_dir(self):
        with self.connection.cd(self.project_dir):
            yield
