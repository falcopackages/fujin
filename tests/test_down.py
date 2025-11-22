from unittest.mock import patch, call
from fujin.commands.down import Down


def test_down_aborts_if_not_confirmed(mock_calls):
    with patch("rich.prompt.Confirm.ask", return_value=False):
        down = Down()
        down()
        assert len(mock_calls) == 0


def test_down_removes_files_and_stops_services(mock_config, mock_calls):
    with patch("rich.prompt.Confirm.ask", return_value=True):
        down = Down()
        down()

        assert call(f"rm -rf {mock_config.app_dir}") in mock_calls
        assert call("sudo systemctl stop testapp.service", warn=True) in mock_calls
        assert call("sudo systemctl disable testapp.service", warn=True) in mock_calls
        assert (
            call("sudo rm /etc/systemd/system/testapp.service", warn=True) in mock_calls
        )
        assert call("sudo systemctl daemon-reload") in mock_calls


def test_down_full_uninstall_proxy(mock_config, mock_calls):
    with (
        patch("rich.prompt.Confirm.ask", return_value=True),
        patch("fujin.caddy.uninstall") as mock_uninstall,
    ):
        down = Down(full=True)
        down()

        assert mock_uninstall.called
