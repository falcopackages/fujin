from unittest.mock import patch, call
from fujin.commands.deploy import Deploy


def test_deploy_calls_expected_commands(mock_config, mock_connection):
    # Patch Config.read to return our mock config
    with patch("fujin.config.Config.read", return_value=mock_config):
        deploy = Deploy()

        # Mock internal methods to focus on the main flow if needed,
        # or let them run if they are pure logic.
        # For this example, we'll let them run but mock file operations if any.

        # We need to mock Path operations if the code checks for file existence
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value=""),
            patch("subprocess.run"),
        ):  # Mock build command

            deploy()

    # Assertions
    # Check if connection context was entered
    assert mock_connection.run.called

    # Verify specific commands were run
    # Note: The exact commands depend on your implementation details
    expected_calls = [
        call(f"mkdir -p {mock_config.host.get_app_dir('testapp')}"),
        call(f"mkdir -p {mock_config.host.get_app_dir('testapp')}/v0.1.0"),
    ]

    # Filter calls to run to check if our expected calls are present
    # This is more robust than checking exact order of ALL calls
    mock_calls = mock_connection.run.call_args_list
    for expected in expected_calls:
        assert (
            expected in mock_calls
        ), f"Expected call {expected} not found in {mock_calls}"

    # Check if services were restarted
    assert call("sudo systemctl restart testapp.service", pty=True) in mock_calls
    # Check replicas
    assert (
        call("sudo systemctl restart testapp-worker@1.service", pty=True) in mock_calls
    )
    assert (
        call("sudo systemctl restart testapp-worker@2.service", pty=True) in mock_calls
    )
