from dataclasses import dataclass

from fujin.config import Config
from fujin.config import Hook
from fujin.host import Host


@dataclass(frozen=True, slots=True)
class HookManager:
    config: Config
    host: Host

    def pre_deploy(self):
        if pre_deploy := self.config.hooks.get(Hook.PRE_DEPLOY):
            with self.host.cd_project_dir(self.config.app):
                self.host.run(f"source .env && {pre_deploy}")
