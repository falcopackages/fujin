from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from fujin.connection import Connection

from fujin.config import Config, HostConfig


@dataclass(frozen=True, slots=True)
class SystemdFile:
    name: str
    body: str


@dataclass(frozen=True, slots=True)
class ProcessManager:
    conn: Connection
    app_name: str
    processes: dict[str, str]
    project_dir: str
    user: str

    @classmethod
    def create(cls, config: Config, host_config: HostConfig, conn: Connection):
        return cls(
            processes=config.processes,
            app_name=config.app_name,
            project_dir=host_config.project_dir(config.app_name),
            conn=conn,
            user=host_config.user
        )

    @property
    def service_names(self) -> list[str]:
        return [self.get_service_name(name) for name in self.processes]

    def get_service_name(self, process_name: str):
        if process_name == "web":
            return f"{self.app_name}.service"
        return f"{self.app_name}-{process_name}.service"

    def run_pty(self, *args, **kwargs):
        return self.conn.run(*args, **kwargs, pty=True)

    def install_services(self) -> None:
        conf_files = self.get_configuration_files()
        for conf_file in conf_files:
            self.run_pty(
                f"echo '{conf_file.body}' | sudo tee /etc/systemd/system/{conf_file.name}",
                hide="out",
            )

        self.run_pty(f"sudo systemctl enable --now {self.app_name}.socket")
        for name in self.service_names:
            # the main web service is launched by the socket service
            if name != f"{self.app_name}.service":
                self.conn.run_sudo(f"sudo systemctl enable {name}")

    def get_configuration_files(self) -> list[SystemdFile]:
        templates_folder = (
                Path(importlib.util.find_spec("fujin").origin).parent / "templates"
        )
        web_service_content = (templates_folder / "web.service").read_text()
        web_socket_content = (templates_folder / "web.socket").read_text()
        other_service_content = (templates_folder / "other.service").read_text()
        context = {
            "app_name": self.app_name,
            "user": self.user,
            "project_dir": self.project_dir,
        }

        files = []
        for name, command in self.processes.items():
            service_name = self.get_service_name(name)
            if name == "web":
                body = web_service_content.format(**context, command=command)
                files.append(
                    SystemdFile(
                        name=f"{self.app_name}.socket",
                        body=web_socket_content.format(**context),
                    )
                )
            else:
                body = other_service_content.format(**context, command=command)
            files.append(SystemdFile(name=service_name, body=body))
        return files

    def uninstall_services(self) -> None:
        self.stop_services()
        self.conn.run(f"sudo systemctl disable {self.app_name}.socket")
        for name in self.service_names:
            # was never enabled in the first place, look at the code above
            if name != f"{self.app_name}.service":
                self.run_pty(f"sudo systemctl disable {name}")

    def start_services(self, *names) -> None:
        names = names or self.service_names
        for name in names:
            if name in self.service_names:
                self.run_pty(f"sudo systemctl start {name}")

    def restart_services(self, *names) -> None:
        names = names or self.service_names
        for name in names:
            if name in self.service_names:
                self.run_pty(f"sudo systemctl restart {name}")

    def stop_services(self, *names) -> None:
        names = names or self.service_names
        for name in names:
            if name in self.service_names:
                self.run_pty(f"sudo systemctl stop {name}")

    def service_logs(self, name: str, follow: bool = False):
        # TODO: add more options here
        self.run_pty(f"sudo journalctl -u {name} -r {'-f' if follow else ''}")

    def reload_configuration(self) -> None:
        self.run_pty(f"sudo systemctl daemon-reload")
