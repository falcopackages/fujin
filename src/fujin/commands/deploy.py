from __future__ import annotations

import subprocess

import cappa
from fujin.commands import AppCommand
from fujin.connection import Connection


@cappa.command(
    help="Deploy the project by building, transferring files, installing, and configuring services"
)
class Deploy(AppCommand):

    def __call__(self):
        try:
            subprocess.run(self.config.build_command.split(), check=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

        with self.connection() as conn:
            conn.run(f"mkdir -p {self.project_dir}")
            with conn.cd(self.project_dir):
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
            f"[blue]Access the deployed project at: https://{self.host_config.domain_name}[/blue]"
        )

    def transfer_files(self, conn: Connection):
        if not self.host_config.envfile.exists():
            raise cappa.Exit(f"{self.host_config.envfile} not found", code=1)

        if not self.config.requirements.exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)
        conn.put(str(self.config.requirements), f"{self.project_dir}/requirements.txt")
        conn.put(str(self.host_config.envfile), f"{self.project_dir}/.env")
        conn.put(
            str(self.config.distfile),
            f"{self.project_dir}/{self.config.distfile.name}",
        )
        envrun = f"""
source .env
export UV_COMPILE_BYTECODE=1
export UV_PYTHON=python{self.config.python_version}
export PATH=".venv/bin:$PATH"
"""
        conn.run(f"echo '{envrun.strip()}' > envrun")

    def install_project(self, conn: Connection):
        if self.config.skip_project_install:
            return
        conn.run("uv venv")
        conn.run("uv pip install -r requirements.txt")
        conn.run(f"uv pip install {self.config.distfile.name}")

    def release(self, conn: Connection):
        if self.config.release_command:
            conn.run(f"source .env && {self.config.release_command}")
