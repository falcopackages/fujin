from dataclasses import dataclass

from fujin.config import Config
from fujin.host import Host
from fujin.config import Hook


@dataclass(frozen=True, slots=True)
class HookManager:
    config: Config
    host: Host

    def pre_deploy(self):
        if pre_deploy := self.config.hooks.get(Hook.PRE_DEPLOY):
            self.host.run(pre_deploy)
