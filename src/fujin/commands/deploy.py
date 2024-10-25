from __future__ import annotations

import importlib.util
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cappa

from fujin.commands.base import HostCommand
from fujin.config import Hook


@cappa.command(help="Deploy project")
class Deploy(HostCommand):

    def __call__(self):
        try:
            subprocess.run(self.config.build_command.split(), check=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

        self.host.make_project_dir(project_name=self.config.app)
        self.transfer_files()
        self.install_project()
        if pre_deploy := self.config.hooks.get(Hook.PRE_DEPLOY):
            self.host.run(pre_deploy)

        systemd_files = self.get_systemd_files()
        for systemd_file in systemd_files:
            self.host.sudo(
                f"echo '{systemd_file.content}' | sudo tee {systemd_file.filepath}",
                hide="out",
            )

        self.host.sudo(f"systemctl enable --now {self.config.app}.socket")
        self.host.sudo(f"systemctl daemon-reload")
        self.restart_services()

        self.config.webserver.get_proxy(host=self.host, config=self.config).configure()
        self.stdout.output("[green]Deployment completed![/green]")

    def transfer_files(self):
        if not self.host.config.envfile.exists():
            raise cappa.Exit(f"{self.host.config.envfile} not found", code=1)

        if not self.config.requirements.exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)
        project_dir = self.host.project_dir(self.config.app)
        self.host.connection.put(
            str(self.config.requirements), f"{project_dir}/requirements.txt"
        )
        self.host.connection.put(str(self.host.config.envfile), f"{project_dir}/.env")
        self.host.connection.put(
            str(self.config.distfile), f"{project_dir}/{self.config.distfile.name}"
        )
        self.host.run(f"echo {self.config.python_version} > .python-version")

    def install_project(self):
        with self.host.cd_project_dir(self.config.app):
            self.host.run_uv("venv")
            self.host.run_uv("pip install -r requirements.txt")
            self.host.run_uv(f"pip install {self.config.distfile.name}")

    def get_systemd_files(self) -> list[SystemdFile]:
        templates_folder = (
            Path(importlib.util.find_spec("fujin").origin).parent / "templates"
        )
        web_service_content = (templates_folder / "web.service").read_text()
        web_socket_content = (templates_folder / "web.socket").read_text()
        other_service_content = (templates_folder / "other.service").read_text()
        context = {
            "app": self.config.app,
            "user": self.host.config.user,
            "project_dir": self.host.project_dir(self.config.app),
        }
        files = [
            SystemdFile(
                name=f"{self.config.get_service_name('web')}.service",
                content=web_service_content.format(
                    **context, command=self.config.web_process
                ),
            ),
            SystemdFile(
                name=f"{self.config.app}.socket",
                content=web_socket_content.format(**context),
            ),
        ]
        for name, command in self.config.processes.items():
            if name != "web":
                files.append(
                    SystemdFile(
                        name=f"{self.config.get_service_name(name)}.service",
                        content=other_service_content.format(
                            **context, command=command
                        ),
                    )
                )
        return files

    def restart_services(self, *names) -> None:
        names = names or self.config.services
        for name in names:
            self.host.sudo(f"systemctl restart {name}")


@dataclass
class SystemdFile:
    name: str
    content: str

    @property
    def filepath(self) -> str:
        return f"/etc/systemd/system/{self.name}"
