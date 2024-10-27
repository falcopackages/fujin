from __future__ import annotations

import subprocess

import cappa

from fujin.commands import AppCommand


@cappa.command(
    help="Deploy the project by building, transferring files, installing, and configuring services"
)
class Deploy(AppCommand):

    def __call__(self):
        self.hook_manager.pre_deploy()
        try:
            subprocess.run(self.config.build_command.split(), check=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

        self.host.make_project_dir()
        self.transfer_files()
        self.install_project()
        self.release()

        self.process_manager.install_services()
        self.process_manager.reload_configuration()
        self.process_manager.restart_services()

        self.web_proxy.setup()
        self.hook_manager.post_deploy()
        self.stdout.output("[green]Project deployment completed successfully![/green]")
        self.stdout.output(
            f"[blue]Access the deployed project at: https://{self.host.config.domain_name}[/blue]"
        )

    def transfer_files(self):
        if not self.host.config.envfile.exists():
            raise cappa.Exit(f"{self.host.config.envfile} not found", code=1)

        if not self.config.requirements.exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)
        self.host.put(
            str(self.config.requirements), f"{self.host.project_dir}/requirements.txt"
        )
        self.host.put(str(self.host.config.envfile), f"{self.host.project_dir}/.env")
        self.host.put(
            str(self.config.distfile),
            f"{self.host.project_dir}/{self.config.distfile.name}",
        )
        with self.host.cd_project_dir():
            self.host.run(f"echo {self.config.python_version} > .python-version")

    def install_project(self):
        if self.config.skip_project_install:
            return
        with self.host.cd_project_dir():
            self.host.run_uv("venv")
            self.host.run_uv("pip install -r requirements.txt")
            self.host.run_uv(f"pip install {self.config.distfile.name}")

    def release(self):
        with self.host.cd_project_dir():
            if self.config.release_command:
                self.host.run(f"source .env && {self.config.release_command}")
