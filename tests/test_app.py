from unittest.mock import call
from fujin.commands.app import App


def test_app_start_resolves_process_name(mock_calls):
    app = App()
    app.start("web")
    assert call("sudo systemctl start testapp.service", pty=True) in mock_calls


def test_app_start_resolves_worker_replicas(mock_calls):
    app = App()
    app.start("worker")
    assert call("sudo systemctl start testapp-worker@1.service", pty=True) in mock_calls
    assert call("sudo systemctl start testapp-worker@2.service", pty=True) in mock_calls


def test_app_start_fallback_to_service_name(mock_calls):
    app = App()
    app.start("custom.service")
    assert call("sudo systemctl start custom.service", pty=True) in mock_calls
