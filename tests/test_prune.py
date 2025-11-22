from unittest.mock import patch, call
from fujin.commands.prune import Prune


def test_prune_flow(mock_config, mock_connection, mock_calls):
    mock_connection.run.return_value.stdout = "0.0.8\n0.0.7"

    with patch("rich.prompt.Confirm.ask", return_value=True):
        prune = Prune(keep=2)
        prune()

        app_dir = mock_config.host.apps_dir + "/testapp"
        assert call(f"rm -r {app_dir}/v0.0.8 {app_dir}/v0.0.7", warn=True) in mock_calls
