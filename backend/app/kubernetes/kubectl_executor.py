"""
KubeVora - Kubectl Executor
Safe wrapper around kubectl execution via Python subprocess.
"""
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from loguru import logger
from app.core.config import settings

# RFC 1123 / Kubernetes DNS naming pattern
RESOURCE_NAME_REGEX = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$")
MAX_OUTPUT_BYTES = 512 * 1024  # 512 KB limit to prevent memory bloat


@dataclass
class KubectlResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str
    data: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


class KubectlExecutor:
    def __init__(
        self,
        kubeconfig: Optional[str] = None,
        context: Optional[str] = None,
        default_timeout: int = 15,
    ):
        self.kubeconfig = kubeconfig or settings.KUBECONFIG_PATH
        self.context = context or settings.KUBERNETES_CONTEXT
        self.default_timeout = default_timeout or settings.KUBEVORA_COMMAND_TIMEOUT

    @staticmethod
    def validate_name(name: str, resource_type: str = "resource") -> bool:
        """Validate namespace or resource name against Kubernetes DNS naming rules."""
        if not name or not isinstance(name, str):
            return False
        if len(name) > 253:
            return False
        return bool(RESOURCE_NAME_REGEX.match(name.strip()))

    def execute(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        parse_json: bool = False,
    ) -> KubectlResult:
        """Execute a kubectl command safely using argument lists."""
        cmd_timeout = timeout or self.default_timeout

        # Verify kubectl executable exists
        kubectl_bin = shutil.which("kubectl")
        if not kubectl_bin:
            logger.error("kubectl executable not found in system PATH")
            return KubectlResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="kubectl executable not found in PATH",
                error_message="kubectl is not installed or not in PATH",
            )

        # Build command with optional kubeconfig and context
        command = [kubectl_bin]
        if self.kubeconfig:
            command.extend(["--kubeconfig", self.kubeconfig])
        if self.context:
            command.extend(["--context", self.context])

        command.extend(args)

        # Log command safely without exposing sensitive arguments
        safe_cmd_str = " ".join(command[:6]) + ("..." if len(command) > 6 else "")
        logger.debug(f"Executing: {safe_cmd_str}")

        start_time = time.perf_counter()
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=cmd_timeout,
                shell=False,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            stdout = process.stdout or ""
            stderr = process.stderr or ""

            # Truncate if output exceeds memory limits
            if len(stdout.encode("utf-8")) > MAX_OUTPUT_BYTES:
                stdout = stdout[:MAX_OUTPUT_BYTES] + "\n...[OUTPUT TRUNCATED BY KUBEVORA]..."

            parsed_data = None
            if parse_json and process.returncode == 0 and stdout:
                try:
                    parsed_data = json.loads(stdout)
                except json.JSONDecodeError as jde:
                    logger.warning(f"Failed to parse kubectl JSON output: {jde}")

            success = process.returncode == 0
            err_msg = None if success else stderr.strip() or f"Process exited with code {process.returncode}"

            return KubectlResult(
                success=success,
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr,
                data=parsed_data,
                error_message=err_msg,
                execution_time_ms=elapsed_ms,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"Command timed out after {cmd_timeout}s: {safe_cmd_str}")
            return KubectlResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {cmd_timeout} seconds",
                error_message=f"Timeout expired ({cmd_timeout}s)",
                execution_time_ms=elapsed_ms,
            )
        except Exception as ex:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected error executing kubectl: {ex}")
            return KubectlResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(ex),
                error_message=str(ex),
                execution_time_ms=elapsed_ms,
            )


kubectl_executor = KubectlExecutor()