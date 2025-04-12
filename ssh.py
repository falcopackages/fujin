# from __future__ import annotations
#
# import subprocess
# from contextlib import contextmanager
# from dataclasses import dataclass, field
# from typing import Generator
#
#
# @dataclass
# class SSHClient:
#     host: str
#     user: str
#     port: int = 22
#     password: str | None = None
#     prefix: str | None = None
#     ssh_process: subprocess.Popen | None = field(init=False)
#     stdin_file: int | None = field(init=False)
#
#     def __enter__(self) -> SSHClient:
#         self.connect()
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb) -> None:
#         if not self.ssh_process:
#             return
#         self.ssh_process.stdin.write("exit\n")
#         self.ssh_process.stdin.flush()
#         self.ssh_process.communicate(timeout=5)
#         # print("trying to stop the process")
#         # # self.ssh_process.stdin.close()
#         # # self.ssh_process.stdout.close()
#         # # self.ssh_process.stderr.close()
#         # print("trying to stop the process 2")
#         # self.ssh_process.terminate()
#         # try:
#         #     self.ssh_process.wait(timeout=1)
#         # except subprocess.TimeoutExpired:
#         #     self.ssh_process.kill()
#
#
#     def connect(self) -> None:
#         self.ssh_process = subprocess.Popen(
#             ["ssh", f"{self.user}@{self.host}"],
#             stdin=subprocess.PIPE,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             encoding="utf-8",
#         )
#
#     def run(
#             self, cmd: str, warn=False, hide=False
#     ):
#         if not self.ssh_process:
#             return
#         self.ssh_process.stdin.write(cmd + "\n")
#         self.ssh_process.stdin.flush()
#         for line in self.ssh_process.stdout:
#             if line:
#                 print(line.strip())
#             else:
#                 break
#             # print(line, end="", flush=True)
#
#     @contextmanager
#     def prefix(self, prefix: str) -> Generator[SSHClient, None, None]:
#         try:
#             self.prefix = prefix
#             yield self
#         finally:
#             self.prefix = None
#
#     def put(self, source: str, destination: str) -> None:
#         ...
#
#     def get(self, source: str, destination: str) -> None:
#         ...
#
#
# with SSHClient("backend.dubai36.online", "fujin") as ssh:
#     ssh.run("ls -la")
#     ssh.run("echo 'Hello, World!'")
#     ssh.run("cat /etc/hosts")

#
# from __future__ import annotations
#
# import subprocess
# import time
# import uuid
# from contextlib import contextmanager
# from dataclasses import dataclass, field
# from typing import Generator
#
#
# @dataclass
# class SSHClient:
#     host: str
#     user: str
#     port: int = 22
#     password: str | None = None
#     prefix: str | None = None
#     ssh_process: subprocess.Popen | None = field(default=None, init=False)
#
#     def __enter__(self) -> SSHClient:
#         self.connect()
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb) -> None:
#         if not self.ssh_process:
#             return
#
#         try:
#             # Send exit command
#             self.ssh_process.stdin.write("exit\n")
#             self.ssh_process.stdin.flush()
#
#             # Wait briefly for graceful exit
#             self.ssh_process.wait(timeout=1)
#         except:
#             pass
#         finally:
#             # Force terminate if still running
#             if self.ssh_process.poll() is None:
#                 try:
#                     self.ssh_process.terminate()
#                     self.ssh_process.wait(timeout=1)
#                 except:
#                     self.ssh_process.kill()
#
#             # Close all file descriptors
#             for pipe in (
#                 self.ssh_process.stdin,
#                 self.ssh_process.stdout,
#                 self.ssh_process.stderr,
#             ):
#                 try:
#                     pipe.close()
#                 except:
#                     pass
#
#     def connect(self) -> None:
#         self.ssh_process = subprocess.Popen(
#             ["ssh", f"{self.user}@{self.host}"],
#             stdin=subprocess.PIPE,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             encoding="utf-8",
#         )
#         # Wait for connection to establish
#         time.sleep(0.5)
#
#     def run(self, cmd: str, warn=False, hide=False) -> str:
#         if not self.ssh_process:
#             return ""
#
#         # Generate a unique marker to detect end of output
#         marker = str(uuid.uuid4())
#
#         # Send the command followed by an echo command with the marker
#         self.ssh_process.stdin.write(f"{cmd}\n")
#         self.ssh_process.stdin.write(f"echo 'END_MARKER_{marker}'\n")
#         self.ssh_process.stdin.flush()
#
#         # Read until we see our marker or timeout
#         output = []
#         start_time = time.time()
#         while time.time() - start_time < 5:  # 5 second timeout
#             line = self.ssh_process.stdout.readline()
#             if not line:
#                 time.sleep(0.1)
#                 continue
#
#             if f"END_MARKER_{marker}" in line:
#                 break
#
#             if not hide and cmd not in line:  # Don't echo the command
#                 print(line.strip())
#             output.append(line)
#
#         return "".join(output)
#
#     @contextmanager
#     def prefix(self, prefix: str) -> Generator[SSHClient, None, None]:
#         try:
#             old_prefix = self.prefix
#             self.prefix = prefix
#             yield self
#         finally:
#             self.prefix = old_prefix
#
#     def put(self, source: str, destination: str) -> None: ...
#
#     def get(self, source: str, destination: str) -> None: ...
#
#
# with SSHClient("net.oluwatobi.dev", "tobi") as ssh:
#     ssh.run("ls -la")
#     ssh.run("echo 'Hello, World!'")
#     ssh.run("cat /etc/hosts")

from pssh.clients import SSHClient

client = SSHClient(host="dotnet", user="tobi")
output = client.run_command("export PATH='/home/tobi/.local/bin:$PATH'; fastfetch")
print("\n".join(output.stdout))
try:
    for line in client.run_command("sudo journalctl -u bookstore -f", use_pty=True).stdout:
        print(line)
except KeyboardInterrupt:
    pass
