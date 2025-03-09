import pytest
from unittest.mock import patch, MagicMock
import os
import tempfile

from fujin.config import Config
from fujin.commands.up import Up
from fujin.commands.deploy import Deploy


class MockSSHServer:
    """
    A class that simulates a remote SSH server without actually connecting to one.
    This can be used to test commands that interact with a remote host.
    """
    
    def __init__(self):
        self.files = {}
        self.commands_run = []
        self.remote_directories = [
            "/home/testuser",
            "/home/testuser/.local",
            "/home/testuser/.local/share",
            "/home/testuser/.local/share/fujin",
        ]
        
    def run_command(self, command, **kwargs):
        """Simulate running a command on the remote host."""
        self.commands_run.append(command)
        
        # Create a result object similar to what fabric's Connection.run would return
        result = MagicMock()
        result.stdout = f"Simulated output for: {command}"
        
        # Simulate specific command behaviors
        if "mkdir" in command:
            dir_path = command.split(" ")[-1]
            self.remote_directories.append(dir_path)
        elif "systemctl" in command:
            if "status" in command:
                service_name = command.split(" ")[-1]
                result.stdout = f"{service_name} is active (running)"
        
        return result
    
    def put_file(self, local_path, remote_path):
        """Simulate copying a file to the remote host."""
        try:
            with open(local_path, 'r') as f:
                content = f.read()
                self.files[remote_path] = content
        except (FileNotFoundError, IsADirectoryError):
            # Just store the path for testing
            self.files[remote_path] = f"Content from {local_path}"
    
    def directory_exists(self, path):
        """Check if a directory exists on the mock server."""
        return path in self.remote_directories


@pytest.fixture
def mock_ssh_server():
    """Fixture that provides a MockSSHServer instance."""
    return MockSSHServer()


@pytest.fixture
def mock_connection(mock_ssh_server):
    """Create a Connection mock that uses the MockSSHServer for behavior."""
    conn = MagicMock()
    
    # Make run command use the MockSSHServer
    conn.run.side_effect = mock_ssh_server.run_command
    
    # Make put use the MockSSHServer
    conn.put.side_effect = mock_ssh_server.put_file
    
    # Set up cd context manager to return self
    conn.cd.return_value.__enter__.return_value = conn
    conn.prefix.return_value.__enter__.return_value = conn
    
    return conn


@pytest.mark.usefixtures("mock_config")
class TestIntegrationWithMockSSH:
    
    @patch('fujin.commands._base.host_connection')
    def test_up_command_integration(self, mock_host_connection, mock_connection, mock_config):
        """Test the up command using a mocked SSH connection."""
        # Setup the connection mock to be returned by host_connection
        mock_host_connection.return_value.__enter__.return_value = mock_connection
        
        # Create a real UpCommand instance but patch its config property
        command = Up()
        with patch.object(command, 'config', mock_config):
            # Execute the up command
            command()()
            
            # Check that the expected SSH commands were run
            assert any("systemctl enable" in cmd for cmd in mock_connection.run.mock_calls), \
                "systemctl enable should have been called"
            assert any("systemctl start" in cmd for cmd in mock_connection.run.mock_calls), \
                "systemctl start should have been called"
    
    @patch('fujin.commands._base.host_connection')
    @patch('os.path.exists')
    def test_deploy_command_integration(self, mock_exists, mock_host_connection, 
                                        mock_connection, mock_config):
        """Test the deploy command using a mocked SSH connection."""
        # Make os.path.exists return True for the distfile
        mock_exists.return_value = True
        
        # Setup the connection mock to be returned by host_connection
        mock_host_connection.return_value.__enter__.return_value = mock_connection
        
        # Create temporary files that the deploy command will try to use
        with tempfile.NamedTemporaryFile() as temp_distfile:
            # Update the mock config to use our temp file
            mock_config.get_distfile_path.return_value = temp_distfile.name
            
            # Create a real DeployCommand instance but patch its config property
            command = Deploy()
            with patch.object(command, 'config', mock_config):
                # Execute the deploy command
                with patch('fujin.commands.deploy.input', return_value="y"):  # Mock user confirmation
                    command()()
                
                # Check that files were copied to the remote host
                assert mock_connection.put.called, "Connection.put should have been called"
                
                # Check that systemctl commands were run
                assert any("systemctl restart" in str(call) for call in mock_connection.run.mock_calls), \
                    "systemctl restart should have been called"