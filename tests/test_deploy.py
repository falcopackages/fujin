from unittest.mock import patch, call
from fujin.commands.deploy import Deploy


def test_deploy_calls_expected_commands(mock_config, mock_calls):
    deploy = Deploy()

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=""),
        patch("subprocess.run"),
    ):
        deploy()

    # Verify specific commands were run
    assert call(f"mkdir -p {mock_config.host.get_app_dir('testapp')}") in mock_calls
    assert (
        call(f"mkdir -p {mock_config.host.get_app_dir('testapp')}/v0.1.0") in mock_calls
    )

    # Check if services were restarted
    assert call("sudo systemctl restart testapp.service", pty=True) in mock_calls
    # Check replicas
    assert (
        call("sudo systemctl restart testapp-worker@1.service", pty=True) in mock_calls
    )
    assert (
        call("sudo systemctl restart testapp-worker@2.service", pty=True) in mock_calls
    )
