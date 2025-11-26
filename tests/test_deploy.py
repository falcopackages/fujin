import hashlib
from unittest.mock import MagicMock, patch

import pytest
from fujin.commands.deploy import Deploy
from fujin.config import InstallationMode


@pytest.mark.use_recorder
def test_deploy_binary_mode(mock_config, mock_connection):
    mock_config.installation_mode = InstallationMode.BINARY
    mock_config.app_name = "myapp"

    # Mock subprocess to avoid actual build
    with patch("subprocess.run"):
        deploy = Deploy()
        deploy()


@pytest.mark.use_recorder
def test_deploy_python_rebuild_venv(mock_config, mock_connection, tmp_path):
    mock_config.installation_mode = InstallationMode.PY_PACKAGE
    mock_config.requirements = "requirements.txt"

    # Create dummy requirements file
    req_path = tmp_path / "requirements.txt"
    req_path.write_text("django")
    mock_config.requirements = str(req_path)

    # Mock remote state: No previous version, so hash check fails/skipped
    def run_side_effect(cmd, **kwargs):
        mock_res = MagicMock()
        mock_res.ok = True
        mock_res.stdout = ""
        if "head -n 1 .versions" in cmd:
            mock_res.stdout = ""
        return mock_res

    mock_connection.run.side_effect = run_side_effect

    with patch("subprocess.run"):
        deploy = Deploy()
        deploy()


@pytest.mark.use_recorder
def test_deploy_python_reuse_venv(mock_config, mock_connection, tmp_path):
    mock_config.installation_mode = InstallationMode.PY_PACKAGE
    mock_config.requirements = "requirements.txt"

    # Create dummy requirements file
    req_path = tmp_path / "requirements.txt"
    content = b"django"
    req_path.write_bytes(content)
    mock_config.requirements = str(req_path)
    local_hash = hashlib.md5(content).hexdigest()

    # Mock remote state: Previous version exists, hashes match
    def run_side_effect(cmd, **kwargs):
        mock_res = MagicMock()
        mock_res.ok = True
        mock_res.stdout = ""
        if "head -n 1 .versions" in cmd:
            mock_res.stdout = "0.0.1"
        if "md5sum" in cmd:
            mock_res.stdout = f"{local_hash}  requirements.txt"
        return mock_res

    mock_connection.run.side_effect = run_side_effect

    with patch("subprocess.run"):
        deploy = Deploy()
        deploy()


@pytest.mark.use_recorder
def test_deploy_version_update(mock_config, mock_connection):
    # Mock remote state: .versions file exists
    def run_side_effect(cmd, **kwargs):
        mock_res = MagicMock()
        mock_res.ok = True
        mock_res.stdout = ""
        if "head -n 1 .versions" in cmd:
            mock_res.stdout = "0.0.1"  # Different from current version
        return mock_res

    mock_connection.run.side_effect = run_side_effect

    with patch("subprocess.run"):
        deploy = Deploy()
        deploy()


@pytest.mark.use_recorder
def test_deploy_pruning(mock_config, mock_connection):
    mock_config.versions_to_keep = 2

    # Mock remote state: return list of versions to prune
    def run_side_effect(cmd, **kwargs):
        mock_res = MagicMock()
        mock_res.ok = True
        mock_res.stdout = ""
        if "sed -n" in cmd:
            # Simulate 3 versions existing, keeping 2, so 1 to prune
            mock_res.stdout = "0.0.1"
        return mock_res

    mock_connection.run.side_effect = run_side_effect

    with patch("subprocess.run"):
        deploy = Deploy()
        deploy()
