from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import cappa
import gevent

from fujin import caddy
from fujin.commands import BaseCommand
from fujin.config import InstallationMode, ProcessConfig
from fujin.connection import Connection
from fujin.secrets import resolve_secrets


@cappa.command(
    help="Deploy the project by building, transferring files, installing, and configuring services"
)
class Deploy(BaseCommand):
    def __call__(self):
        # parse and resolve secrets in .env file
        if self.config.secret_config:
            self.stdout.output("[blue]Reading secrets....[/blue]")
            parsed_env = resolve_secrets(
                self.config.host.env_content, self.config.secret_config
            )
        else:
            parsed_env = self.config.host.env_content

        # run build command
        try:
            subprocess.run(self.config.build_command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e
        # the build commands might be responsible for creating the requirements file
        if self.config.requirements and not Path(self.config.requirements).exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)

        with self.connection() as conn:
            conn.run(f"mkdir -p {self.config.app_dir}")
            # copy env file
            conn.run(f"echo '{parsed_env}' > {self.config.app_dir}/.env")
            self.install_project(conn)
            self.install_services(conn)
            self.restart_services(conn)
            if self.config.webserver.enabled:
                caddy.setup(conn, self.config)

            # prune old versions
            with conn.cd(self.config.app_dir):
                if self.config.versions_to_keep:
                    result = conn.run(
                        f"sed -n '{self.config.versions_to_keep + 1},$p' .versions",
                        hide=True,
                    ).stdout.strip()
                    result_list = result.split("\n")
                    if result != "":
                        to_prune = [f"{self.config.app_dir}/v{v}" for v in result_list]
                        conn.run(f"rm -r {' '.join(to_prune)}", warn=True)
                        conn.run(
                            f"sed -i '{self.config.versions_to_keep + 1},$d' .versions",
                            warn=True,
                        )
        self.stdout.output("[green]Project deployment completed successfully![/green]")
        self.stdout.output(
            f"[blue]Access the deployed project at: https://{self.config.host.domain_name}[/blue]"
        )

    def install_services(self, conn: Connection) -> None:
        units = self.config.get_systemd_units()
        for filename, content in units.items():
            conn.run(
                f"echo '{content}' | sudo tee /etc/systemd/system/{filename}",
                hide="out",
                pty=True,
            )

        threads = []
        for name in self.config.processes:
            service_name = self.config.get_service_name(name)
            config = self.config.processes[name]
            if isinstance(config, ProcessConfig) and config.socket and name == "web":
                threads.append(
                    gevent.spawn(
                        conn.run,
                        f"sudo systemctl enable --now {self.config.app_name}.socket",
                        pty=True,
                    )
                )
            else:
                threads.append(
                    gevent.spawn(
                        conn.run,
                        f"sudo systemctl enable {service_name}",
                        pty=True,
                    )
                )
        threads.append(
            gevent.spawn(
                conn.run,
                "sudo systemctl daemon-reload",
            )
        )
        gevent.joinall(threads)

    def restart_services(self, conn: Connection) -> None:
        threads = [
            gevent.spawn(conn.run, f"sudo systemctl restart {name}", pty=True)
            for name in self.config.service_names
        ]
        gevent.joinall(threads)

    def install_project(
        self,
        conn: Connection,
        *,
        version: str | None = None,
        rolling_back: bool = False,
    ):
        version = version or self.config.version

        # transfer binary or package file
        release_dir = self.config.get_release_dir(version)
        conn.run(f"mkdir -p {release_dir}")

        distfile_path = self.config.get_distfile_path(version)
        remote_package_path = f"{release_dir}/{distfile_path.name}"
        if not rolling_back:
            conn.put(str(distfile_path), remote_package_path)

        # install project
        with conn.cd(self.config.app_dir):
            if self.config.installation_mode == InstallationMode.PY_PACKAGE:
                self._install_python_package(
                    conn,
                    remote_package_path=remote_package_path,
                    version=version,
                    release_dir=release_dir,
                )
            else:
                self._install_binary(conn, remote_package_path)

        # run release command
        if self.config.release_command:
            conn.run(f"source .appenv && {self.config.release_command}")

        # update version history
        with conn.cd(self.config.app_dir):
            result = conn.run(
                "head -n 1 .versions", warn=True, hide=True
            ).stdout.strip()
            if result == version:
                return
            if result == "":
                conn.run(f"echo '{version}' > .versions")
            else:
                conn.run(f"sed -i '1i {version}' .versions")

    def _install_python_package(
        self,
        conn: Connection,
        *,
        remote_package_path: str,
        version: str,
        release_dir: str,
    ):
        appenv = f"""
set -a  # Automatically export all variables
source .env
set +a  # Stop automatic export
export UV_COMPILE_BYTECODE=1
export UV_PYTHON=python{self.config.python_version}
export PATH=".venv/bin:$PATH"
"""
        conn.run(f"echo '{appenv.strip()}' > {self.config.app_dir}/.appenv")

        # Decision: Do we need to rebuild the virtualenv?
        rebuild_venv = False
        if self.config.requirements:
            local_reqs_path = Path(self.config.requirements)
            curr_release_reqs = f"{release_dir}/requirements.txt"

            # Get the version currently running on the host to find previous requirements
            prev_version = conn.run(
                "head -n 1 .versions", warn=True, hide=True
            ).stdout.strip()
            prev_release_reqs = (
                f"{self.config.get_release_dir(prev_version)}/requirements.txt"
            )

            local_hash = hashlib.md5(local_reqs_path.read_bytes()).hexdigest()
            remote_hash = ""

            if prev_version:
                res = conn.run(f"md5sum {prev_release_reqs}", warn=True, hide=True)
                if res.ok:
                    remote_hash = res.stdout.strip().split()[0]

            if local_hash == remote_hash:
                rebuild_venv = False
                # Even if we don't rebuild, we copy the reqs file to the new folder
                # so the new release folder is complete and self-contained.
                if prev_release_reqs != curr_release_reqs:
                    conn.run(f"cp {prev_release_reqs} {curr_release_reqs}")
            else:
                # Hashes differ or previous file didn't exist -> Upload new one
                conn.put(str(local_reqs_path), curr_release_reqs)

        # Execution
        if not rebuild_venv:
            conn.run("sudo rm -rf .venv")
            conn.run(f"uv python install {self.config.python_version}")
            conn.run("uv venv")
            if self.config.requirements:
                conn.run(f"uv pip install -r {release_dir}/requirements.txt")
        conn.run(f"uv pip install {remote_package_path}")

    def _install_binary(self, conn: Connection, remote_package_path: str):
        appenv = f"""
set -a  # Automatically export all variables
source .env
set +a  # Stop automatic export
export PATH="{self.config.app_dir}:$PATH"
"""
        conn.run(f"echo '{appenv.strip()}' > {self.config.app_dir}/.appenv")
        full_path_app_bin = f"{self.config.app_dir}/{self.config.app_bin}"
        conn.run(f"rm {full_path_app_bin}", warn=True)
        conn.run(f"ln -s {remote_package_path} {full_path_app_bin}")
