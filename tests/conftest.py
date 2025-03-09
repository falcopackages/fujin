import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from fujin.config import Config, HostConfig, Webserver, SecretConfig, SecretAdapter


@pytest.fixture
def temp_test_dir(tmp_path):
    """Fixture to create a temporary test directory."""
    return tmp_path


@pytest.fixture
def sample_fujin_toml(temp_test_dir):
    """Create a sample fujin.toml file in a temp directory."""
    toml_content = """
    app = "testapp"
    version = "0.1.0"
    build_command = "python -m build ."
    installation_mode = "python-package"
    distfile = "dist/testapp-{version}-py3-none-any.whl"
    python_version = "3.12"
    
    [host]
    domain_name = "example.com"
    user = "testuser"
    
    [webserver]
    type = "fujin.proxies.dummy"
    upstream = "localhost:8000"
    
    [processes]
    web = ".venv/bin/uvicorn testapp.main:app"
    """
    
    fujin_toml = temp_test_dir / "fujin.toml"
    fujin_toml.write_text(toml_content)
    return fujin_toml


@pytest.fixture
def mock_connection():
    """Create a mock Connection object."""
    conn = MagicMock()
    
    # Set up run method to return a mock result
    mock_result = MagicMock()
    mock_result.stdout = "command output"
    conn.run.return_value = mock_result
    
    # Set up put method
    conn.put.return_value = None
    
    # Set up context managers
    conn.cd.return_value.__enter__.return_value = conn
    conn.prefix.return_value.__enter__.return_value = conn
    
    return conn


@pytest.fixture
def mock_config():
    """Create a mock Config object with all necessary properties."""
    config = MagicMock(spec=Config)
    config.app_name = "testapp"
    config.version = "0.1.0"
    config.installation_mode = "python-package"
    config.python_version = "3.12"
    config.distfile = "dist/testapp-{version}-py3-none-any.whl"
    config.build_command = "python -m build ."
    
    # Host config
    host = MagicMock(spec=HostConfig)
    host.domain_name = "example.com"
    host.user = "testuser"
    host.ip = "127.0.0.1"
    host.ssh_port = 22
    host.get_app_dir.return_value = "/home/testuser/.local/share/fujin/testapp"
    config.host = host
    
    # Webserver config
    webserver = MagicMock(spec=Webserver)
    webserver.type = "fujin.proxies.dummy"
    webserver.upstream = "localhost:8000"
    config.webserver = webserver
    
    # Processes
    config.processes = {"web": ".venv/bin/uvicorn testapp.main:app"}
    
    # Secrets
    config.secret_config = MagicMock(spec=SecretConfig)
    config.secret_config.adapter = SecretAdapter.SYSTEM
    
    return config