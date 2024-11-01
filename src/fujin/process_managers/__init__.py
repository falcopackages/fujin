from __future__ import annotations

from typing import Protocol
from typing import TYPE_CHECKING

from fujin.connection import Connection

if TYPE_CHECKING:
    from fujin.config import Config, HostConfig


class ProcessManager(Protocol):
    service_names: list[str]

    @classmethod
    def create(
        cls, config: Config, host_config: HostConfig, conn: Connection
    ) -> ProcessManager: ...

    def get_service_name(self, process_name: str): ...

    def install_services(self) -> None: ...

    def uninstall_services(self) -> None: ...

    def start_services(self, *names) -> None: ...

    def restart_services(self, *names) -> None: ...

    def stop_services(self, *names) -> None: ...

    def service_logs(self, name: str, follow: bool = False): ...

    def reload_configuration(self) -> None: ...

    def get_configuration_files(
        self, ignore_local: bool = False
    ) -> list[tuple[str, str]]: ...
