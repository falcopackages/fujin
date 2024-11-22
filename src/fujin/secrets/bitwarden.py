from __future__ import annotations
import cappa


from fujin.config import SecretConfig
import subprocess
from contextlib import contextmanager
from typing import Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from . import secret_reader


@contextmanager
def bitwarden(secret_config: SecretConfig) -> Generator[secret_reader, None, None]:
    if not secret_config.password_env:
        raise cappa.Exit(
            "You need to set the password_env to use the bitwarden adapter", code=1
        )
    sync_result = subprocess.run(["bw", "sync"], capture_output=True, text=True)
    if sync_result.returncode != 0:
        raise cappa.Exit(f"Bitwarden sync failed: {sync_result.stdout}", code=1)
    unlock_result = subprocess.run(
        [
            "bw",
            "unlock",
            "--nointeraction",
            "--passwordenv",
            secret_config.password_env,
            "--raw",
        ],
        capture_output=True,
        text=True,
    )
    if unlock_result.returncode != 0:
        raise cappa.Exit(f"Bitwarden unlock failed {unlock_result.stderr}", code=1)

    session = unlock_result.stdout.strip()

    def read_secret(name: str) -> str:
        result = subprocess.run(
            ["bw", "get", "password", name, "--raw", "--session", session],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise cappa.Exit(f"Password not found for {name}")
        return result.stdout.strip()

    try:
        yield read_secret
    finally:
        subprocess.run(["bw", "lock"], capture_output=True)
