from __future__ import annotations

import subprocess

import cappa

from fujin.commands import BaseCommand
from fujin.connection import Connection


@cappa.command(
    help="Deploy the project by building, transferring files, installing, and configuring services"
)
class Deploy(BaseCommand):
    def __call__(self):
        self.build_app()

        with self.connection() as conn:
            conn.run(f"mkdir -p {self.app_dir}")
            with conn.cd(self.app_dir):
                self.create_hook_manager(conn).pre_deploy()
                self.transfer_files(conn)

        with self.app_environment() as conn:
            process_manager = self.create_process_manager(conn)
            self.install_project(conn)
            self.release(conn)
            process_manager.install_services()
            process_manager.reload_configuration()
            process_manager.restart_services()

            self.create_web_proxy(conn).setup()
            self.create_hook_manager(conn).post_deploy()
        self.stdout.output("[green]Project deployment completed successfully![/green]")
        self.stdout.output(
            f"[blue]Access the deployed project at: https://{self.config.host.domain_name}[/blue]"
        )

    def build_app(self) -> None:
        try:
            subprocess.run(self.config.build_command, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

    @property
    def versioned_assets_dir(self) -> str:
        return f"{self.app_dir}/v{self.config.version}"

    def transfer_files(self, conn: Connection):
        if not self.config.host.envfile.exists():
            raise cappa.Exit(f"{self.config.host.envfile} not found", code=1)

        if not self.config.requirements.exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)
        conn.put(str(self.config.host.envfile), f"{self.app_dir}/.env")
        conn.run(f"mkdir -p {self.versioned_assets_dir}")
        conn.put(
            str(self.config.requirements),
            f"{self.versioned_assets_dir}/requirements.txt",
        )
        conn.put(
            str(self.config.distfile),
            f"{self.versioned_assets_dir}/{self.config.distfile.name}",
        )
        appenv = f"""
set -a  # Automatically export all variables
source .env
set +a  # Stop automatic export
export UV_COMPILE_BYTECODE=1
export UV_PYTHON=python{self.config.python_version}
export PATH=".venv/bin:$PATH"
"""
        conn.run(f"echo '{appenv.strip()}' > .appenv")

    def install_project(self, conn: Connection):
        if self.config.skip_project_install:
            return
        conn.run("uv venv")
        conn.run(f"uv pip install -r v{self.config.version}/requirements.txt")
        conn.run(f"uv pip install v{self.config.version}/{self.config.distfile.name}")

    def release(self, conn: Connection):
        if self.config.release_command:
            conn.run(f"source .env && {self.config.release_command}")
