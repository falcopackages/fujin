from unittest.mock import patch, call, MagicMock
from fujin.commands.rollback import Rollback


def test_rollback_flow(mock_config, mock_connection, mock_calls):
    def run_side_effect(command, **kwargs):
        mock = MagicMock()
        if "sed -n '2,$p' .versions" in command:
            mock.stdout = "0.0.9\n0.0.8"
        elif "head -n 1 .versions" in command:
            mock.stdout = "0.1.0"
        else:
            mock.stdout = ""
        return mock

    mock_connection.run.side_effect = run_side_effect

    with (
        patch("rich.prompt.Prompt.ask", return_value="0.0.9"),
        patch("rich.prompt.Confirm.ask", return_value=True),
        patch("fujin.commands.deploy.Deploy.install_project") as mock_install,
        patch("fujin.commands.deploy.Deploy.restart_services") as mock_restart,
    ):
        rollback = Rollback()
        rollback()

        mock_install.assert_called_with(mock_connection, "0.0.9")
        mock_restart.assert_called_with(mock_connection)
        # Should remove newer versions (0.1.0 is current, rolling back to 0.0.9, so 0.1.0 is removed)
        assert call("rm -r v0.1.0", warn=True) in mock_calls
