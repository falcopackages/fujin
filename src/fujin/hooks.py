import subprocess
from dataclasses import dataclass

import cappa
from rich import print as rich_print

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum


    class StrEnum(str, Enum):
        pass


class Hook(StrEnum):
    PRE_BUILD = "pre_build"
    PRE_DEPLOY = "pre_deploy"
    POST_DEPLOY = "post_deploy"


HooksDict = dict[Hook, str]


@dataclass(frozen=True, slots=True)
class HookManager:
    app_name: str
    hooks: HooksDict

    def _run_hook(self, type_: Hook) -> None:
        if cmd := self.hooks.get(type_):
            rich_print(f"[blue]Running {type_} hook[/blue]")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                raise cappa.Exit(result.stderr)

    def pre_build(self) -> None:
        self._run_hook(Hook.PRE_BUILD)

    def pre_deploy(self) -> None:
        self._run_hook(Hook.PRE_DEPLOY)

    def post_deploy(self) -> None:
        self._run_hook(Hook.POST_DEPLOY)
