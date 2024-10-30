from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING

import cappa
from fabric import Connection
from invoke import Responder
from invoke.exceptions import UnexpectedExit
from paramiko.ssh_exception import (
    AuthenticationException,
    NoValidConnectionsError,
    SSHException,
)

if TYPE_CHECKING:
    from fujin.config import HostConfig


def _get_watchers(host_config: HostConfig) -> list[Responder]:
    if not host_config.password:
        return []
    return [
        Responder(
            pattern=r"\[sudo\] password:",
            response=f"{host_config.password}\n",
        ),
        Responder(
            pattern=rf"\[sudo\] password for {host_config.user}:",
            response=f"{host_config.password}\n",
        ),
    ]


@contextmanager
def host_connection(host_config: HostConfig) -> Connection:
    connect_kwargs = None
    if host_config.key_filename:
        connect_kwargs = {"key_filename": str(host_config.key_filename)}
    elif host_config.password:
        connect_kwargs = {"password": host_config.password}
    conn = Connection(
        host_config.ip,
        user=host_config.user,
        port=host_config.ssh_port,
        connect_kwargs=connect_kwargs,
    )
    try:
        conn.run = partial(
            conn.run,
            env={
                "PATH": f"/home/{host_config.user}/.cargo/bin:/home/{host_config.user}/.local/bin:$PATH"
            },
            watchers=_get_watchers(host_config),
        )
        yield conn
    except AuthenticationException as e:
        msg = f"Authentication failed for {host_config.user}@{host_config.ip} -p {host_config.ssh_port}.\n"
        if host_config.key_filename:
            msg += f"An SSH key was provided at {host_config.key_filename.resolve()}. Please verify its validity and correctness."
        elif host_config.password:
            msg += f"A password was provided through the environment variable {host_config.password_env}. Please ensure it is correct for the user {host_config.user}."
        else:
            msg += "No password or SSH key was provided. Ensure your current host has SSH access to the target host."
        raise cappa.Exit(msg, code=1) from e
    except (UnexpectedExit, NoValidConnectionsError) as e:
        raise cappa.Exit(str(e), code=1) from e
    except SSHException as e:
        raise cappa.Exit(
            f"{e}, possible causes: incorrect user, or either you or the server may be offline",
            code=1,
        ) from e
    finally:
        conn.close()
