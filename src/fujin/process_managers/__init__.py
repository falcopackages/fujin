from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fujin.config import Config
    from fujin.host import Host


class ProcessManager(Protocol):
    host: Host
    config: Config
    service_names: list[str]

    def get_service_name(self, name: str): ...

    def install_services(self) -> None: ...

    def uninstall_services(self) -> None: ...

    def start_services(self, *names) -> None: ...

    def restart_services(self, *names) -> None: ...

    def stop_services(self, *names) -> None: ...

    def service_logs(self, name: str, follow: bool = False): ...

    def reload_configuration(self) -> None: ...
