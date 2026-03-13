import os
import subprocess
from abc import ABC

from application.ports.os import OS, CommandOutput


class OSImpl(OS, ABC):
    def run(self, args: list[str], timeout: int = 10) -> CommandOutput:
        try:
            result = subprocess.run(args=args, capture_output=True, text=True, timeout=timeout)
            return CommandOutput(code=result.returncode, error=str(result.stderr), output=str(result.stdout))
        except subprocess.TimeoutExpired as e:
            return CommandOutput(code=124, error=str(e), output="")


class LinuxOSImpl(OSImpl):
    def iface_exists(self, iface: str) -> bool:
        # Check sysfs presence to avoid racing netifd
        path = f"/sys/class/net/{iface}"
        return os.path.exists(path)
