from __future__ import annotations

import importlib.util
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cappa

from fujin.commands.base import HostCommand
from fujin.config import ImproperlyConfiguredError, Hook


@cappa.command(help="Deploy project")
class Deploy(HostCommand):

    def __call__(self):
        try:
            subprocess.run(self.config.build_command.split(), check=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

        self.host.run(f"mkdir -p {self.host.project_dir}")
        self.transfer_files()
        self.install_project()

        systemd_files = self.get_systemd_files()
        for systemd_file in systemd_files:
            self.host.connection.sudo(
                f"echo '{systemd_file.content}' > {systemd_file.filepath}"
            )

        self.host.connection.sudo(f"systemctl enable --now {self.config.app}.socket")
        self.host.connection.sudo(f"systemctl daemon-reload")
        self.restart_services()

        with self.host.connection.cd(self.host.project_dir):
            self.host.run(
                f"echo '{json.dumps(self.get_caddy_config())}' > caddy.json"
            )
            self.host.run(
                f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
            )

    def transfer_files(self):
        envfile = self.host.envfile or self.config.envfile
        if not envfile:
            raise ImproperlyConfiguredError(
                f"Missing envfile in both top config and {self.host.name} configuration"
            )
        if not envfile.exists():
            raise cappa.Exit(f"{envfile} not found", code=1)

        if not self.config.requirements.exists():
            raise cappa.Exit(f"{self.config.requirements} not found", code=1)
        self.host.connection.put(
            str(self.config.requirements), f"{self.host.project_dir}/requirements.txt"
        )
        self.host.connection.put(str(envfile), f"{self.host.project_dir}/.env")
        self.host.connection.put(
            str(self.config.distfile), f"{self.host.project_dir}/{self.config.distfile.name}"
        )
        self.host.connection.run(f"echo {self.config.python_version} > .python-version")

    def install_project(self):
        with self.host.connection.cd(self.host.project_dir):
            self.host.run_uv("sync")
            self.host.run_uv(f"pip install {self.config.distfile.name}")
            if pre_deploy := self.config.hooks.get(Hook.PRE_DEPLOY):
                self.host.run(pre_deploy)

    def get_caddy_config(self) -> dict:
        return {
            "apps": {
                "http": {
                    "servers": {
                        self.config.app: {
                            "listen": [":443"],
                            "routes": [
                                {
                                    "match": [{
                                        "self.host": [self.host.domain_name]
                                    }],
                                    "handle": [
                                        {
                                            "handler": "reverse_proxy",
                                            "upstreams": [
                                                {
                                                    "dial": self.config.webserver.upstream
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                }
            }
        }

    # TODO probably cache this
    def get_systemd_files(self) -> list[SystemdFile]:

        templates_folder = (
                Path(importlib.util.find_spec("fujin").origin).parent / "templates"
        )
        web_service_content = (templates_folder / "web.service").read_text()
        web_socket_content = (templates_folder / "web.socket").read_text()
        other_service_content = (templates_folder / "other.service").read_text()
        context = {
            "app": self.config.app,
            "user": self.host.user,
            "project_dir": self.host.project_dir,
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
            self.host.connection.sudo(f"systemctl restart {name}")


@dataclass
class SystemdFile:
    name: str
    content: str

    @property
    def filepath(self) -> str:
        return f"/etc/systemd/system/{self.name}"
