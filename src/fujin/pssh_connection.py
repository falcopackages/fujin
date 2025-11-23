from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

import cappa
from pssh.clients import ParallelSSHClient
from pssh.exceptions import (
    AuthenticationException,
    ConnectionErrorException,
    SSHException,
)

if TYPE_CHECKING:
    from fujin.config import HostConfig


class PSSHResult:
    def __init__(self, output, exit_code):
        self.stdout = "\n".join(output.stdout) if output.stdout else ""
        self.stderr = "\n".join(output.stderr) if output.stderr else ""
        self.return_code = exit_code
        self.ok = exit_code == 0


class PSSHConnectionWrapper:
    def __init__(self, client: ParallelSSHClient, host_ip: str):
        self.client = client
        self.host_ip = host_ip
        self._cwd = None

    def run(
        self,
        command: str,
        warn: bool = False,
        hide: bool | str = False,
        pty: bool = False,
    ) -> PSSHResult:
        if self._cwd:
            command = f"cd {self._cwd} && {command}"

        # pssh run_command returns a dictionary of host_output
        output_dict = self.client.run_command(command, use_pty=pty)

        # Since we have only one host
        if isinstance(output_dict, list):
            host_output = output_dict[0]
        else:
            host_output = output_dict[self.host_ip]

        # Wait for completion
        self.client.join(output_dict)

        result = PSSHResult(host_output, host_output.exit_code)

        if not result.ok and not warn:
            # If hide is True, we might want to show stderr in the exception
            msg = f"Command failed: {command}"
            if result.stderr:
                msg += f"\n{result.stderr}"
            raise cappa.Exit(msg, code=result.return_code or 1)

        return result

    def put(self, local: str, remote: str):
        # copy_file copies to all hosts
        self.client.copy_file(local, remote)

    @contextmanager
    def cd(self, path: str):
        prev_cwd = self._cwd
        if self._cwd:
            self._cwd = f"{self._cwd}/{path}" if not path.startswith("/") else path
        else:
            self._cwd = path
        try:
            yield
        finally:
            self._cwd = prev_cwd


@contextmanager
def pssh_host_connection(
    host: HostConfig,
) -> Generator[PSSHConnectionWrapper, None, None]:
    try:
        client = ParallelSSHClient(
            [host.ip],
            user=host.user,
            password=host.password,
            pkey=str(host.key_filename) if host.key_filename else None,
            port=host.ssh_port,
        )
        yield PSSHConnectionWrapper(client, host.ip)
    except AuthenticationException as e:
        msg = f"Authentication failed for {host.user}@{host.ip} -p {host.ssh_port}.\n"
        raise cappa.Exit(msg, code=1) from e
    except (ConnectionErrorException, SSHException) as e:
        raise cappa.Exit(
            f"{e}, possible causes: incorrect user, or either you or the server may be offline",
            code=1,
        ) from e
