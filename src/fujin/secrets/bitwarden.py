from __future__ import annotations
import cappa


import msgspec

from fujin.config import SecretConfig
import subprocess


class BwAdapter(msgspec.Struct, kw_only=True):
    password_env: str
    _session: str | None = None

    @classmethod
    def create(cls, secret_config: SecretConfig) -> BwAdapter:
        if not secret_config.password_env:
            raise cappa.Exit(
                "You need to set the password_env to use the bitwarden adapter", code=1
            )
        return cls(
            password_env=secret_config.password_env,
        )

    def open(self) -> None:
        sync_result = subprocess.run(["bw", "sync"], capture_output=True, text=True)
        if sync_result.returncode != 0:
            raise cappa.Exit(f"Bitwarden sync failed: {sync_result.stdout}", code=1)
        unlock_result = subprocess.run(
            [
                "bw",
                "unlock",
                "--nointeraction",
                "--passwordenv",
                self.password_env,
                "--raw",
            ],
            capture_output=True,
            text=True,
        )
        if unlock_result.returncode != 0:
            raise cappa.Exit(f"Bitwarden unlock failed {unlock_result.stderr}", code=1)
        self._session = unlock_result.stdout.strip()

    def read_secret(self, name) -> str:
        result = subprocess.run(
            ["bw", "get", "password", name, "--raw", "--session", self._session],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise cappa.Exit(f"Password not found for {name}")
        return result.stdout.strip()

    def close(self) -> None:
        subprocess.run(["bw", "lock"], capture_output=True)
