import pytest
from unittest.mock import patch, MagicMock

from fujin.config import HostConfig
from fujin.connection import host_connection, _get_watchers


class TestConnection:
    @pytest.fixture
    def host_config(self):
        return HostConfig(
            ip="127.0.0.1",
            domain_name="example.com",
            user="testuser",
        )
    
    @pytest.fixture
    def host_with_key(self, host_config):
        host_config._key_filename = "/path/to/key"
        return host_config
    
    @pytest.fixture
    def host_with_password(self, host_config):
        host_config.password_env = "TEST_PASSWORD"
        return host_config
    
    def test_get_watchers_no_password(self, host_config):
        # When no password is provided
        watchers = _get_watchers(host_config)
        
        # Then no watchers are returned
        assert len(watchers) == 0
    
    @patch.dict('os.environ', {"TEST_PASSWORD": "test123"})
    def test_get_watchers_with_password(self, host_with_password):
        # Mock the password property to return a value
        with patch.object(host_with_password, 'password', return_value="test123"):
            # When a password is provided
            watchers = _get_watchers(host_with_password)
            
            # Then watchers are returned
            assert len(watchers) == 2
            # Check patterns
            assert "[sudo] password:" in watchers[0].pattern
            assert f"[sudo] password for {host_with_password.user}:" in watchers[1].pattern
    
    @patch('fujin.connection.Connection')
    def test_host_connection_with_key(self, mock_connection_class, host_with_key):
        # Mock the connection
        mock_connection = MagicMock()
        mock_connection_class.return_value = mock_connection
        
        # When connecting with a key
        with host_connection(host_with_key) as conn:
            # Then the connection is created with the right parameters
            mock_connection_class.assert_called_once_with(
                host_with_key.ip,
                user=host_with_key.user,
                port=host_with_key.ssh_port,
                connect_kwargs={"key_filename": "/path/to/key"}
            )
            assert conn is mock_connection