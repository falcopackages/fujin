from __future__ import annotations

import importlib.util
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cappa

from fujin.commands.base import HostCommand
from fujin.config import ConfigDep, ImproperlyConfiguredError, Config, Host, Process


@cappa.command(help="Deploy project")
class Deploy(HostCommand):

    def __call__(self, config: ConfigDep, output: cappa.Output):
        host = self.host(config)
        try:
            subprocess.run(config.release_command.split(), check=True)
        except subprocess.CalledProcessError as e:
            raise cappa.Exit(f"build command failed: {e}", code=1) from e

        host.connection.run(f"mkdir -p {host.project_dir}")
        self.transfer_files(host, config)
        self.install_project(host, config)

        systemd_files = self.get_systemd_files(host=host, config=config)
        for systemd_file in systemd_files:
            host.connection.sudo(
                f"echo '{systemd_file.content}' > {systemd_file.filepath}"
            )

        host.connection.sudo(f"systemctl enable --now {config.app}.socket")
        host.connection.sudo(f"systemctl daemon-reload")
        self.restart_all_services(
            *(service.name for service in systemd_files), host=host
        )

        with host.connection.cd(host.project_dir):
            host.run(
                f"echo '{json.dumps(self.get_caddy_config(host=host, config=config))} > caddy.json"
            )
            host.run(
                f"curl localhost:2019/load -H 'Content-Type: application/json' -d @caddy.json"
            )

    @classmethod
    def transfer_files(cls, host: Host, config: Config):
        envfile = host.envfile or config.envfile
        if not envfile:
            raise ImproperlyConfiguredError(
                f"Missing envfile in both top config and {host.name} configuration"
            )
        if not envfile.exists():
            raise cappa.Exit(f"{envfile} not found", code=1)

        if not config.requirements.exists():
            raise cappa.Exit(f"{config.requirements} not found", code=1)
        host.connection.put(
            str(config.requirements), f"{host.project_dir}/requirements.txt"
        )
        host.connection.put(str(envfile), f"{host.project_dir}/.env")
        host.connection.put(
            str(config.distfile), f"{host.project_dir}/{config.distfile.name}"
        )
        host.connection.run(f"echo {config.python_version} > .python-version")

    @classmethod
    def install_project(cls, host: Host, config: Config):
        with host.connection.cd(host.project_dir):
            host.run_uv("sync")
            host.run_uv(f"pip install {config.distfile.name}")
            if config.release_command:
                host.run(config.release_command)

    @classmethod
    def get_caddy_config(cls, host: Host, config: Config) -> dict:
        upstream = f"localhost:{config.web_process.port}" if config.web_process.port else config.web_process.bind
        return {
            "apps": {
                "http": {
                    "servers": {
                        config.app: {
                            "listen": [":443"],
                            "routes": [
                                {
                                    "match": [{
                                        "host": [host.domain_name]
                                    }],
                                    "handle": [
                                        {
                                            "handler": "reverse_proxy",
                                            "upstreams": [
                                                {
                                                    "dial": upstream
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

    @classmethod  # TODO probably cache this
    def get_systemd_files(cls, host: Host, config: Config) -> list[SystemdFile]:

        templates_folder = (
                Path(importlib.util.find_spec("fujin").origin).parent / "templates"
        )
        web_service_content = (templates_folder / "web.service").read_text()
        web_socket_content = (templates_folder / "web.socket").read_text()
        other_service_content = (templates_folder / "other.service").read_text()
        context = {
            "app": config.app,
            "user": host.user,
            "project_dir": host.project_dir,
        }
        files = [
            SystemdFile(
                name=f"{Process.service_name(app=config.app, name='web')}.service",
                content=web_service_content.format(
                    **context, command=config.web_process.command
                ),
            ),
            SystemdFile(
                name=f"{config.app}.socket",
                content=web_socket_content.format(**context),
            ),
        ]
        for name, process in config.processes.items():
            if name != "web":
                files.append(
                    SystemdFile(
                        name=f"{Process.service_name(app=config.app, name='web')}.service",
                        content=other_service_content.format(
                            **context, command=process.command
                        ),
                    )
                )
        return files

    @classmethod
    def restart_all_services(cls, *names, host: Host) -> None:
        for name in names:
            host.connection.sudo(f"systemctl restart {name}")


@dataclass
class SystemdFile:
    name: str
    content: str

    @property
    def filepath(self) -> str:
        return f"/etc/systemd/system/{self.name}"
