import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from contextlib import contextmanager
from fujin.config import Config, HostConfig, Webserver, ProcessConfig, InstallationMode
from .recorder import MockRecorder


@pytest.fixture
def recorder(request):
    # Store recordings in tests/recordings/<test_name>.json
    test_name = request.node.name
    recording_path = Path(__file__).parent / "recordings" / f"{test_name}.json"
    rec = MockRecorder(recording_path)
    yield rec


@pytest.fixture
def mock_config(request):
    return Config(
        app_name="testapp",
        version="0.1.0",
        build_command="echo build",
        distfile="dist/testapp-{version}.whl",
        installation_mode=InstallationMode.PY_PACKAGE,
        python_version="3.12",
        host=HostConfig(
            domain_name="example.com",
            user="testuser",
            env_content="FOO=bar",
        ),
        webserver=Webserver(upstream="localhost:8000"),
        processes={
            "web": ProcessConfig(command="run web"),
            "worker": ProcessConfig(command="run worker", replicas=2),
        },
        local_config_dir=Path(__file__).parent.parent / "src" / "fujin" / "templates",
    )


@pytest.fixture
def mock_connection(request, recorder):
    with patch("fujin.commands._base.host_connection") as mock:
        conn = MagicMock()
        # Setup context manager behavior for the connection itself
        mock.return_value.__enter__.return_value = conn

        # Setup context manager behavior for conn.cd() and conn.prefix()
        # These methods return context managers that yield the connection (or None)
        conn.cd.return_value.__enter__.return_value = conn
        conn.prefix.return_value.__enter__.return_value = conn

        yield conn

        marker = request.node.get_closest_marker("use_recorder")
        if marker:
            recorder.process_calls(conn.mock_calls)


@pytest.fixture
def mock_calls(mock_connection):
    return mock_connection.run.call_args_list


@pytest.fixture(autouse=True)
def patch_config_read(mock_config):
    """Automatically patch Config.read for all tests."""
    with patch("fujin.config.Config.read", return_value=mock_config):
        yield


@pytest.fixture
def assert_command_called(mock_calls):
    def _assert(cmd, **kwargs):
        assert call(cmd, **kwargs) in mock_calls

    return _assert


@pytest.fixture
def get_commands():
    def _get(mock_calls):
        commands = []
        for c in mock_calls:
            name = c[0]
            if name == "run":
                if c.args:
                    commands.append(str(c.args[0]))
                elif "command" in c.kwargs:
                    commands.append(str(c.kwargs["command"]))
        return commands

    return _get
