import pytest
from fujin.commands.app import App


@pytest.mark.use_recorder
def test_app_start_resolves_process_name(mock_connection):
    app = App()
    app.start("web")


@pytest.mark.use_recorder
def test_app_start_resolves_worker_replicas(mock_connection):
    app = App()
    app.start("worker")


@pytest.mark.use_recorder
def test_app_start_fallback_to_service_name(mock_connection):
    app = App()
    app.start("custom.service")
