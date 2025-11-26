import pytest
from inline_snapshot import snapshot
from fujin.commands.app import App


def test_app_info_functional(mock_connection, get_commands):
    """
    This test runs 'fujin app info' against the example project.
    """
    app = App()
    app.info()

    assert get_commands(mock_connection.mock_calls) == snapshot(
        [
            "head -n 1 .versions",
            "sed -n '2,$p' .versions",
            "sudo systemctl is-active testapp.service testapp-worker@1.service testapp-worker@2.service",
        ]
    )


def test_app_restart_functional(mock_connection, get_commands):
    """
    This test runs 'fujin app restart' against the example project.
    """
    app = App()
    app.restart()

    assert get_commands(mock_connection.mock_calls) == snapshot(
        [
            "sudo systemctl restart testapp.service testapp-worker@1.service testapp-worker@2.service"
        ]
    )
