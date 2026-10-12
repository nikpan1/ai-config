import json
import os
import signal
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import uuid4

from docgen_graph.storage import ArtifactStore

PINNED_CODEX_VERSION = "0.162.1"
DISABLED_FEATURES = (
    "shell_tool",
    "unified_exec",
    "apps",
    "plugins",
    "remote_plugin",
    "multi_agent",
    "hooks",
    "memories",
    "skill_search",
    "skill_mcp_dependency_install",
    "view_image",
    "tool_suggest",
    "auth_elicitation",
    "in_app_browser",
    "workspace_dependencies",
)


def restricted_config(workspace, runtime_home):
    from openai_codex import CodexConfig

    overrides = (
        'default_permissions="docgen-analysis"',
        'permissions.docgen-analysis.filesystem={":root"="deny",":minimal"="read",'
        '":workspace_roots"="read"}',
        "permissions.docgen-analysis.network.enabled=false",
        "features.skip_host_skill_discovery=true",
        'web_search="disabled"',
        'cli_auth_credentials_store="ephemeral"',
        "project_doc_max_bytes=0",
        "check_for_update_on_startup=false",
        "mcp_servers={}",
        "agents.enabled=false",
        *(f"features.{name}=false" for name in DISABLED_FEATURES),
    )
    return CodexConfig(
        cwd=str(workspace), env={"CODEX_HOME": str(runtime_home)}, config_overrides=overrides
    )


def validate_effective_config(value, runtime_version):
    if runtime_version != PINNED_CODEX_VERSION:
        raise ValueError("Codex runtime differs from the pinned SDK runtime")
    if value.get("sandbox_mode") or value.get("default_permissions") != "docgen-analysis":
        raise ValueError("The effective sandbox does not use the restricted profile")
    profile = value.get("permissions", {}).get("docgen-analysis", {})
    filesystem = {k: v for k, v in profile.get("filesystem", {}).items() if v is not None}
    if filesystem != {":root": "deny", ":minimal": "read", ":workspace_roots": "read"}:
        raise ValueError("Codex filesystem restrictions were changed")
    if profile.get("extends") or profile.get("workspace_roots"):
        raise ValueError("Codex profile grants additional roots")
    if profile.get("network", {}).get("enabled") is not False:
        raise ValueError("Codex command network access is not disabled")
    if any(value.get("features", {}).get(name) is not False for name in DISABLED_FEATURES):
        raise ValueError("Codex execution or discovery tools are not disabled")
    if value.get("web_search") != "disabled" or value.get("mcp_servers"):
        raise ValueError("Codex external tools are not disabled")


def stop_process_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


class NativeCodexTransport:
    def __init__(self, settings, frozen_root):
        self.settings = settings
        self.root = Path(frozen_root).resolve().parent / "sdk-sessions" / uuid4().hex
        self.process = None

    def capabilities(self):
        try:
            versions = [version(name) for name in ("openai-codex", "openai-codex-cli-bin")]
        except PackageNotFoundError:
            return {"status": "unavailable", "reason": "Install the code-analysis extra"}
        if any(item != PINNED_CODEX_VERSION for item in versions):
            return {"status": "unsupported", "reason": "Codex SDK and runtime pins must match"}
        if not self.settings.code_analysis_api_key:
            return {
                "status": "unavailable",
                "reason": "OPENAI_API_KEY is required for isolated Codex",
            }
        return {
            "status": "ok",
            "provider": "codex_sdk",
            "read_only": True,
            "filesystem_tools": False,
            "method": "frozen_context",
            "sdk_version": PINNED_CODEX_VERSION,
        }

    def run(self, payload):
        capability = self.capabilities()
        if capability["status"] != "ok":
            raise ValueError(capability["reason"])
        store = ArtifactStore(self.root)
        store.write("workspace/.snapshot", "Frozen source context is supplied in the request.")
        store.write("home/.isolated", "Isolated SDK runtime settings.")
        workspace, runtime_home = self.root / "workspace", self.root / "home"
        request = {
            "workspace": str(workspace),
            "runtime_home": str(runtime_home),
            "api_key": self.settings.code_analysis_api_key,
            "model": self.settings.code_analysis_model,
            "payload": payload,
            "result_limit": self.settings.code_analysis_result_limit,
        }
        env = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC"}
        }
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        env["PYTHONIOENCODING"] = "utf-8"
        self.process = subprocess.Popen(
            [sys.executable, "-m", "docgen_graph.code_analysis.sdk_worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=workspace,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        try:
            output, _ = self.process.communicate(
                json.dumps(request), timeout=self.settings.code_analysis_timeout
            )
        except subprocess.TimeoutExpired as error:
            stop_process_tree(self.process)
            raise TimeoutError("Codex analysis exceeded its deadline") from error
        if (
            self.process.returncode
            or len(output.encode()) > self.settings.code_analysis_result_limit
        ):
            raise ValueError("Codex returned an invalid or oversized result")
        response = json.loads(output)
        if response.get("status") != "ok":
            raise ValueError(
                "Codex configuration or analysis failed: "
                + response.get("error_type", "unknown")
                + ": "
                + response.get("error_message", "No diagnostic supplied")
            )
        return response

    def close(self):
        if self.process is not None:
            stop_process_tree(self.process)
