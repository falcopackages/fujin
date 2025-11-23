import hashlib
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from fujin.commands.deploy import Deploy
from fujin.config import InstallationMode


def test_deploy_binary_mode(mock_config, mock_connection, assert_command_called):
    mock_config.installation_mode = InstallationMode.BINARY
    mock_config.app_bin = "myapp"

    # Mock subprocess to avoid actual build
    with patch("subprocess.run"):
        deploy = Deploy(config=mock_config)
        deploy()

    # Verify binary specific steps
    release_dir = mock_config.get_release_dir()
    distfile = mock_config.get_distfile_path()

    # Symlink creation
    full_path_app_bin = f"{mock_config.app_dir}/{mock_config.app_bin}"
    assert_command_called(f"rm {full_path_app_bin}", warn=True)
    assert_command_called(f"ln -s {release_dir}/{distfile.name} {full_path_app_bin}")

    # Verify .appenv for binary (PATH export)
    # We check that we didn't call python install steps
    assert call("uv python install", pty=True) not in mock_connection.run.mock_calls


def test_deploy_python_rebuild_venv(
    mock_config, mock_connection, assert_command_called, tmp_path
):
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
        deploy = Deploy(config=mock_config)
        deploy()

    # Verify venv rebuild commands
    assert_command_called("sudo rm -rf .venv")
    assert_command_called(f"uv python install {mock_config.python_version}")
    assert_command_called("uv venv")
    assert_command_called(
        f"uv pip install -r {mock_config.get_release_dir()}/requirements.txt"
    )


def test_deploy_python_reuse_venv(
    mock_config, mock_connection, assert_command_called, tmp_path
):
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
        deploy = Deploy(config=mock_config)
        deploy()

    # Verify NO venv rebuild
    assert call("sudo rm -rf .venv") not in mock_connection.run.mock_calls
    assert call("uv venv") not in mock_connection.run.mock_calls

    # Verify requirements copy
    prev_reqs = f"{mock_config.app_dir}/v0.0.1/requirements.txt"
    curr_reqs = f"{mock_config.get_release_dir()}/requirements.txt"
    assert_command_called(f"cp {prev_reqs} {curr_reqs}")


def test_deploy_version_update(mock_config, mock_connection, assert_command_called):
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
        deploy = Deploy(config=mock_config)
        deploy()

    # Verify version update
    assert_command_called(f"sed -i '1i {mock_config.version}' .versions")


def test_deploy_pruning(mock_config, mock_connection, assert_command_called):
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
        deploy = Deploy(config=mock_config)
        deploy()

    # Verify pruning
    assert_command_called(f"rm -r {mock_config.app_dir}/v0.0.1", warn=True)
    assert_command_called(
        f"sed -i '{mock_config.versions_to_keep + 1},$d' .versions", warn=True
    )
