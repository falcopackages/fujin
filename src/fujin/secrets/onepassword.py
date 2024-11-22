from __future__ import annotations
import cappa


from fujin.config import SecretConfig
import subprocess

from contextlib import contextmanager
from typing import Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from . import secret_reader


@contextmanager
def one_password(_: SecretConfig) -> Generator[secret_reader, None, None]:
    def read_secret(name: str) -> str:
        result = subprocess.run(["op", "read", name], capture_output=True, text=True)
        if result.returncode != 0:
            raise cappa.Exit(result.stderr)
        return result.stdout.strip()

    try:
        yield read_secret
    finally:
        pass
