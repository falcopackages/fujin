from __future__ import annotations
import cappa


import msgspec

from fujin.config import SecretConfig
import subprocess


class OPAdapter(msgspec.Struct, kw_only=True):
    @classmethod
    def create(cls, _: SecretConfig) -> BwAdapter:
        return cls()

    def open(self) -> None:
        pass

    def read_secret(self, name) -> str:
        result = subprocess.run(["op", "read", name], capture_output=True, text=True)
        if result.returncode != 0:
            raise cappa.Exit(result.stderr)
        return result.stdout.strip()

    def close(self) -> None:
        pass
