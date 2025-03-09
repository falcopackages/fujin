import pytest
from unittest.mock import patch, MagicMock

from fujin.commands._base import BaseCommand
from fujin.config import Config, HostConfig


class TestBaseCommand:
    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=Config)
        config.app_name = "testapp"
        config.host = MagicMock(spec=HostConfig)
        config.host.get_app_dir.return_value = "/home/testuser/.local/share/fujin/testapp"
        config.webserver.type = "fujin.proxies.dummy"
        return config
    
    @pytest.fixture
    def command(self):
        return BaseCommand()
    
    @patch('fujin.commands._base.Config')
    def test_config_property(self, mock_config_class, command):
        # Mock the Config.read() method
        mock_config = MagicMock()
        mock_config_class.read.return_value = mock_config
        
        # When accessing the config property
        result = command.config
        
        # Then Config.read() is called and returns the mock
        mock_config_class.read.assert_called_once()
        assert result is mock_config
    
    @patch('fujin.commands._base.cappa.Output')
    def test_stdout_property(self, mock_output_class, command):
        # Mock the Output constructor
        mock_output = MagicMock()
        mock_output_class.return_value = mock_output
        
        # When accessing the stdout property
        result = command.stdout
        
        # Then a new Output is created
        mock_output_class.assert_called_once()
        assert result is mock_output
    
    @patch.object(BaseCommand, 'config', new_callable=MagicMock)
    def test_app_dir_property(self, mock_config, command):
        # Setup the config mock
        mock_config.app_name = "testapp"
        mock_config.host.get_app_dir.return_value = "/path/to/app"
        
        # When accessing the app_dir property
        result = command.app_dir
        
        # Then get_app_dir is called with the app name
        mock_config.host.get_app_dir.assert_called_once_with(app_name="testapp")
        assert result == "/path/to/app"
    
    @patch.object(BaseCommand, 'config', new_callable=MagicMock)
    @patch('fujin.commands._base.host_connection')
    def test_connection_contextmanager(self, mock_host_connection, mock_config, command):
        # Setup mocks
        mock_conn = MagicMock()
        mock_host_connection.return_value.__enter__.return_value = mock_conn
        
        # When using the connection context manager
        with command.connection() as conn:
            # Then host_connection is called with the host config
            mock_host_connection.assert_called_once_with(host=mock_config.host)
            # And the connection is returned
            assert conn is mock_conn