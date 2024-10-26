from __future__ import annotations

import subprocess

import cappa

from fujin.commands import AppCommand


@cappa.command(
    help="Deploy the project by building, transferring files, installing, and configuring services"
)
class Deploy(AppCommand):

    def __call__(self):
        try:
            subprocess.run(self.config.build_command.split(), check=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

        self.host.make_project_dir(project_name=self.config.app)
        self.transfer_files()
        self.install_project()
        self.hook_manager.pre_deploy()

        self.process_manager.install_services()
        self.process_manager.reload_configuration()
        self.process_manager.restart_services()

        self.web_proxy.setup()
        self.stdout.output("[green]Project deployment completed successfully![/green]")
        self.stdout.output(
            f"[blue]Access the deployed project at: https://{self.host.config.domain_name}[/blue]"
        )

    def transfer_files(self):
        if not self.host.config.envfile.exists():
            raise cappa.Exit(f"{self.host.config.envfile} not found", code=1)

        if not self.config.requirements.exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)
        project_dir = self.host.project_dir(self.config.app)
        self.host.put(str(self.config.requirements), f"{project_dir}/requirements.txt")
        self.host.put(str(self.host.config.envfile), f"{project_dir}/.env")
        self.host.put(
            str(self.config.distfile), f"{project_dir}/{self.config.distfile.name}"
        )
        self.host.run(f"echo {self.config.python_version} > .python-version")

    def install_project(self):
        with self.host.cd_project_dir(self.config.app):
            self.host.run_uv("venv")
            self.host.run_uv("pip install -r requirements.txt")
            self.host.run_uv(f"pip install {self.config.distfile.name}")
