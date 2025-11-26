import json
from pathlib import Path
from unittest.mock import call


class MockRecorder:
    def __init__(self, path: Path):
        self.path = path
        self.mode = "verify" if path.exists() else "record"

    def process_calls(self, mock_calls):
        commands = []
        for c in mock_calls:
            name = c[0]
            if name == "run":
                if c.args:
                    commands.append(str(c.args[0]))
                elif "command" in c.kwargs:
                    commands.append(str(c.kwargs["command"]))

        if self.mode == "record":
            self._save(commands)
        else:
            self._verify(commands)

    def _save(self, calls):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(calls, f, indent=2)

    def _verify(self, actual_calls):
        with open(self.path) as f:
            expected_calls = json.load(f)

        # Simple comparison for now
        # We can improve this to show diffs
        if len(actual_calls) != len(expected_calls):
            self._raise_mismatch(expected_calls, actual_calls, "Length mismatch")

        for i, (expected, actual) in enumerate(zip(expected_calls, actual_calls)):
            if expected != actual:
                self._raise_mismatch(
                    expected_calls, actual_calls, f"Mismatch at index {i}"
                )

    def _raise_mismatch(self, expected, actual, message):
        import difflib

        expected_str = json.dumps(expected, indent=2)
        actual_str = json.dumps(actual, indent=2)

        diff = difflib.unified_diff(
            expected_str.splitlines(),
            actual_str.splitlines(),
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )

        diff_text = "\n".join(diff)
        raise AssertionError(f"{message}\n{diff_text}")
