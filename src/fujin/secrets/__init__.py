from __future__ import annotations

from contextlib import closing
from io import StringIO
from typing import Callable

import gevent
from dotenv import dotenv_values

from fujin.config import SecretAdapter
from fujin.config import SecretConfig
from .bitwarden import bitwarden
from .onepassword import one_password

secret_reader = Callable[[str], str]
secret_adapter_context = Callable[[SecretConfig], secret_reader]

adapter_to_context: dict[SecretAdapter, secret_adapter_context] = {
    SecretAdapter.BITWARDEN: bitwarden,
    SecretAdapter.ONE_PASSWORD: one_password,
}


def resolve_secrets(env_content: str, secret_config: SecretConfig) -> str:
    with closing(StringIO(env_content)) as buffer:
        env_dict = dotenv_values(stream=buffer)
    secrets = {key: value for key, value in env_dict.items() if value.startswith("$")}
    adapter_context = adapter_to_context[secret_config.adapter]
    parsed_secrets = {}
    with adapter_context(secret_config) as secret_reader:
        for key, secret in secrets.items():
            parsed_secrets[key] = gevent.spawn(secret_reader, secret[1:])
        gevent.joinall(parsed_secrets.values())
    env_dict.update({key: thread.value for key, thread in parsed_secrets.items()})
    return "\n".join(f'{key}="{value}"' for key, value in env_dict.items())
