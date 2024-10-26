from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from fujin.config import Config
from fujin.host import Host


@dataclass(frozen=True, slots=True)
class SystemdFile:
    name: str
    body: str


@dataclass(frozen=True, slots=True)
class ProcessManager:
    config: Config
    host: Host

    @property
    def service_names(self) -> list[str]:
        return [self.get_service_name(name) for name in self.config.processes]

    def get_service_name(self, name: str):
        if name == "web":
            return self.config.app
        return f"{self.config.app}-{name}.service"

    def install_services(self) -> None:
        conf_files = self.get_configuration_files()
        for conf_file in conf_files:
            self.host.sudo(
                f"echo '{conf_file.body}' | sudo tee /etc/systemd/system/{conf_file.name}",
                hide="out",
            )

        self.host.sudo(f"systemctl enable --now {self.config.app}.socket")
        for name in self.service_names:
            # the main web service is launched by the socket service
            if name != f"{self.config.app}.service":
                self.host.sudo(f"systemctl enable {name}")

    def get_configuration_files(self) -> list[SystemdFile]:
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

        files = []
        for name, command in self.config.processes.items():
            name = self.get_service_name(name)
            if name == "web":
                body = web_service_content.format(**context, command=command)
                files.append(
                    SystemdFile(
                        name=f"{self.config.app}.socket",
                        body=web_socket_content.format(**context),
                    )
                )
            else:
                body = other_service_content.format(**context, command=command)
            files.append(SystemdFile(name=name, body=body))
        return files

    def uninstall_services(self) -> None:
        self.stop_services()
        self.host.sudo(f"systemctl disable {self.config.app}.socket")
        for name in self.service_names:
            # was never enabled in the first place, look at the code above
            if name != f"{self.config.app}.service":
                self.host.sudo(f"systemctl disable {name}")

    def start_services(self, *names) -> None:
        names = names or self.service_names
        for name in names:
            if name in self.service_names:
                self.host.sudo(f"systemctl start {name}")

    def restart_services(self, *names) -> None:
        names = names or self.service_names
        for name in names:
            if name in self.service_names:
                self.host.sudo(f"systemctl restart {name}")

    def stop_services(self, *names) -> None:
        names = names or self.service_names
        for name in names:
            if name in self.service_names:
                self.host.sudo(f"systemctl stop {name}")

    def service_logs(self, name: str, follow: bool = False):
        # TODO: add more options here
        self.host.sudo(f"journalctl -u {name} -r {'-f' if follow else ''}")

    def reload_configuration(self) -> None:
        self.host.sudo(f"systemctl daemon-reload")
