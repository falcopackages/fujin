from __future__ import annotations

from pathlib import Path
from typing import Protocol

from dotenv import dotenv_values

from fujin.config import SecretConfig, SecretAdapter
from .bitwarden import BwAdapter
from .onepassword import OPAdapter
import gevent


class AdapterImpl(Protocol):
    @classmethod
    def create(cls, secret_config: SecretConfig) -> AdapterImpl: ...

    def open(self) -> None: ...

    def read_secret(self, name) -> str | None: ...

    def close(self) -> str | None: ...


adapter_to_class: dict[SecretAdapter, AdapterImpl] = {
    SecretAdapter.BITWARDEN: BwAdapter,
    SecretAdapter.ONE_PASSWORD: OPAdapter,
}


def patch_secrets(envfile: Path, secret_config: SecretConfig) -> str:
    env_dict = dotenv_values(envfile)
    secrets = {key: value for key, value in env_dict.items() if value.startswith("$")}
    adapter = adapter_to_class[secret_config.adapter].create(secret_config)
    adapter.open()
    parsed_secrets = {}
    for key, secret in secrets.items():
        parsed_secrets[key] = gevent.spawn(adapter.read_secret, secret[1:])
    gevent.joinall(parsed_secrets.values())
    adapter.close()
    env_dict.update({key: thread.value for key, thread in parsed_secrets.items()})
    return "\n".join(f'{key}="{value}"' for key, value in env_dict.items())
