# Fujin Tests

This directory contains tests for the Fujin project.

## Running Tests

To run the tests, use the following command:

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=fujin

# Run a specific test file
pytest tests/unit/test_connection.py
```

## Test Structure

- `unit/`: Contains unit tests that test individual components in isolation, using mocks for dependencies
- `integration/`: Contains tests that verify components work together, using mock SSH servers

## Mock SSH Architecture

The integration tests use a `MockSSHServer` class to simulate a remote SSH server. This approach allows testing the application's functionality without requiring a real remote host.

Key features:
- Simulates running commands on a remote host
- Tracks commands run and files copied
- Maintains a virtual file system and directory structure
- Can be extended to simulate specific server behaviors

## Writing New Tests

1. For unit tests, use the fixtures in `conftest.py` to get mock objects
2. For integration tests, use the `MockSSHServer` to simulate remote host operations
3. Follow the existing test patterns, using descriptive test names and comments