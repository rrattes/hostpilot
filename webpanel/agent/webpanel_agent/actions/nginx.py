from dataclasses import dataclass
import os
import posixpath
import re
import subprocess
from typing import Any, Protocol


DEFAULT_ALLOWED_WEBROOT_BASE = "/var/www/hostpilot-sites"
DEFAULT_ALLOWED_NGINX_BASE = "/etc/nginx/sites-available/hostpilot"
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


class Filesystem(Protocol):
    def makedirs(self, path: str) -> None: ...
    def write_text(self, path: str, content: str) -> None: ...
    def remove_file(self, path: str) -> None: ...


class CommandRunner(Protocol):
    def run(self, argv: list[str]) -> "CommandResult": ...


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class LocalFilesystem:
    def makedirs(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def write_text(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def remove_file(self, path: str) -> None:
        try:
            os.remove(path)
        except FileNotFoundError:
            return


class LocalCommandRunner:
    def run(self, argv: list[str]) -> CommandResult:
        completed = subprocess.run(
            argv,
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def apply_site_config(
    payload: dict[str, Any],
    *,
    filesystem: Filesystem | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    fs = filesystem or LocalFilesystem()
    runner = command_runner or LocalCommandRunner()
    request = _validated_request(payload)
    steps: list[str] = []
    config_written = False

    fs.makedirs(request["webroot_path"])
    steps.append(f"created_or_verified_webroot:{request['webroot_path']}")

    fs.makedirs(posixpath.dirname(request["target_config_path"]))
    steps.append(f"created_or_verified_nginx_dir:{posixpath.dirname(request['target_config_path'])}")

    fs.write_text(request["target_config_path"], request["config_content"])
    config_written = True
    steps.append(f"wrote_config:{request['target_config_path']}")

    validation = runner.run(["nginx", "-t"])
    steps.append("ran_validation:nginx -t")
    if validation.returncode != 0:
        if config_written:
            fs.remove_file(request["target_config_path"])
            steps.append(f"rolled_back_config:{request['target_config_path']}")
        return {
            "status": "validation_failed",
            "applied": False,
            "rolled_back": True,
            "reloaded": False,
            "steps": steps,
            "validation": _command_result(validation),
            "reload": None,
        }

    reload_result = runner.run(["systemctl", "reload", "nginx"])
    steps.append("ran_reload:systemctl reload nginx")
    if reload_result.returncode != 0:
        return {
            "status": "reload_failed",
            "applied": False,
            "rolled_back": False,
            "reloaded": False,
            "steps": steps,
            "validation": _command_result(validation),
            "reload": _command_result(reload_result),
        }

    return {
        "status": "applied",
        "applied": True,
        "rolled_back": False,
        "reloaded": True,
        "steps": steps,
        "validation": _command_result(validation),
        "reload": _command_result(reload_result),
    }


def _validated_request(payload: dict[str, Any]) -> dict[str, str]:
    domain = _required_string(payload, "domain").lower()
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise ValueError("Invalid domain.")

    allowed_webroot_base = _safe_base(
        payload.get("allowed_webroot_base", DEFAULT_ALLOWED_WEBROOT_BASE),
        "allowed webroot base",
    )
    allowed_nginx_base = _safe_base(
        payload.get("allowed_nginx_base", DEFAULT_ALLOWED_NGINX_BASE),
        "allowed nginx base",
    )
    webroot_path = _safe_child_path(
        _required_string(payload, "webroot_path"),
        allowed_webroot_base,
        "webroot path",
    )
    target_config_path = _safe_child_path(
        _required_string(payload, "target_config_path"),
        allowed_nginx_base,
        "target config path",
    )
    expected_config_path = f"{allowed_nginx_base}/{domain}.conf"
    if target_config_path != expected_config_path:
        raise ValueError("Target config path must match the site domain under the allowed Nginx path.")

    config_content = _required_string(payload, "config_content")
    if f"server_name {domain};" not in config_content:
        raise ValueError("Config content must include the site server_name.")
    if f"root {webroot_path};" not in config_content:
        raise ValueError("Config content must include the approved webroot path.")

    return {
        "domain": domain,
        "allowed_webroot_base": allowed_webroot_base,
        "allowed_nginx_base": allowed_nginx_base,
        "webroot_path": webroot_path,
        "target_config_path": target_config_path,
        "config_content": config_content,
    }


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _safe_base(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("/"):
        raise ValueError(f"{label} must be an absolute path.")
    normalized = posixpath.normpath(value)
    if normalized != value.rstrip("/") or ".." in value.split("/"):
        raise ValueError(f"{label} is unsafe.")
    return normalized


def _safe_child_path(path: str, base: str, label: str) -> str:
    if "\\" in path or "\x00" in path or not path.startswith("/"):
        raise ValueError(f"{label} must be a safe absolute path.")
    normalized = posixpath.normpath(path)
    if normalized != path or ".." in path.split("/"):
        raise ValueError(f"{label} must not contain traversal or redundant segments.")
    if normalized != base and not normalized.startswith(f"{base}/"):
        raise ValueError(f"{label} must stay under {base}.")
    return normalized


def _command_result(result: CommandResult) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
