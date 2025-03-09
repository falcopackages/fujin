import pytest
from unittest.mock import patch, MagicMock

import cappa

from fujin.commands.up import Up
from fujin.config import Config


class TestUpCommand:
    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=Config)
        config.app_name = "testapp"
        return config
    
    @pytest.fixture
    def command(self):
        return Up()
    
    @patch.object(Up, 'config', new_callable=MagicMock)
    @patch.object(Up, 'stdout', new_callable=MagicMock)
    @patch.object(Up, 'connection')
    @patch.object(Up, 'create_web_proxy')
    @patch.object(Up, 'create_process_manager')
    @patch.object(Up, 'hook_manager')
    def test_up_command(self, mock_hook_manager, mock_process_manager_factory, 
                          mock_web_proxy_factory, mock_connection, mock_stdout, mock_config):
        # Setup mocks
        mock_connection_cm = MagicMock()
        mock_conn = MagicMock()
        mock_connection.return_value = mock_connection_cm
        mock_connection_cm.__enter__.return_value = mock_conn
        
        mock_process_manager = MagicMock()
        mock_process_manager_factory.return_value = mock_process_manager
        
        mock_web_proxy = MagicMock()
        mock_web_proxy_factory.return_value = mock_web_proxy
        
        # When calling the command
        result = command.up()
        
        # Then the correct methods are called
        mock_hook_manager.before_up.assert_called_once()
        mock_connection.assert_called_once()
        mock_web_proxy_factory.assert_called_once_with(mock_conn)
        mock_process_manager_factory.assert_called_once_with(mock_conn)
        
        # Check web proxy and process manager are configured
        mock_web_proxy.configure.assert_called_once()
        mock_process_manager.enable.assert_called_once()
        mock_process_manager.start.assert_called_once()
        
        mock_hook_manager.after_up.assert_called_once()
        
        # Check the output
        mock_stdout.success.assert_called()


class TestCappaCLI:
    @patch('fujin.commands.up.UpCommand.up')
    def test_cappa_command_registration(self, mock_up_method):
        # Simulate output from cappa.command
        mock_up_method.return_value = cappa.Exit(code=0)
        
        # Create a mock for cappa.app that registers our commands
        with patch('cappa.app') as mock_app:
            # Import a file that registers commands with cappa.command to trigger registration
            from fujin.commands import up
            
            # Check app was configured
            mock_app.assert_called()
            
            # This just tests that the command was registered with cappa
            # A full test would require more complex mocking of the cappa framework