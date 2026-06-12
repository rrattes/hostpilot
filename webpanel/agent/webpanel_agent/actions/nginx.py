from dataclasses import dataclass
import os
import posixpath
import re
import subprocess
from typing import Any, Protocol


DEFAULT_ALLOWED_WEBROOT_BASE = "/var/www/hostpilot-sites"
DEFAULT_ALLOWED_NGINX_BASE = "/etc/nginx/sites-available/hostpilot"
DEFAULT_ALLOWED_LOG_BASE = "/var/log/nginx/hostpilot"
MAX_LOG_LINES = 500
MAX_FILE_PAGE_SIZE = 100
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


class Filesystem(Protocol):
    def makedirs(self, path: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def is_dir(self, path: str) -> bool: ...
    def list_dir(self, path: str) -> list["FileEntry"]: ...
    def read_text(self, path: str) -> str: ...
    def write_text(self, path: str, content: str) -> None: ...
    def remove_file(self, path: str) -> None: ...


class CommandRunner(Protocol):
    def run(self, argv: list[str]) -> "CommandResult": ...


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class FileEntry:
    name: str
    is_dir: bool
    size: int
    modified_at: float


class LocalFilesystem:
    def makedirs(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def write_text(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def exists(self, path: str) -> bool:
        return os.path.isfile(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def list_dir(self, path: str) -> list[FileEntry]:
        entries: list[FileEntry] = []
        for entry in os.scandir(path):
            stat = entry.stat(follow_symlinks=False)
            entries.append(
                FileEntry(
                    name=entry.name,
                    is_dir=entry.is_dir(follow_symlinks=False),
                    size=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )
        return entries

    def read_text(self, path: str) -> str:
        with open(path, encoding="utf-8") as handle:
            return handle.read()

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


def disable_site_config(
    payload: dict[str, Any],
    *,
    filesystem: Filesystem | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    fs = filesystem or LocalFilesystem()
    runner = command_runner or LocalCommandRunner()
    request = _validated_disable_request(payload)
    steps: list[str] = []

    if not fs.exists(request["target_config_path"]):
        return {
            "status": "missing_config",
            "disabled": False,
            "rolled_back": False,
            "reloaded": False,
            "steps": [f"missing_config:{request['target_config_path']}"],
            "validation": None,
            "reload": None,
        }

    original_config = fs.read_text(request["target_config_path"])
    fs.remove_file(request["target_config_path"])
    steps.append(f"removed_config:{request['target_config_path']}")

    validation = runner.run(["nginx", "-t"])
    steps.append("ran_validation:nginx -t")
    if validation.returncode != 0:
        fs.write_text(request["target_config_path"], original_config)
        steps.append(f"restored_config:{request['target_config_path']}")
        return {
            "status": "validation_failed",
            "disabled": False,
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
            "disabled": False,
            "rolled_back": False,
            "reloaded": False,
            "steps": steps,
            "validation": _command_result(validation),
            "reload": _command_result(reload_result),
        }

    return {
        "status": "disabled",
        "disabled": True,
        "rolled_back": False,
        "reloaded": True,
        "steps": steps,
        "validation": _command_result(validation),
        "reload": _command_result(reload_result),
    }


def tail_site_logs(
    payload: dict[str, Any],
    *,
    filesystem: Filesystem | None = None,
) -> dict[str, Any]:
    fs = filesystem or LocalFilesystem()
    request = _validated_logs_request(payload)
    access_log = _tail_log_file(fs, request["access_log_path"], request["line_limit"])
    error_log = _tail_log_file(fs, request["error_log_path"], request["line_limit"])
    return {
        "status": "completed",
        "domain": request["domain"],
        "line_limit": request["line_limit"],
        "logs": {
            "access": access_log,
            "error": error_log,
        },
    }


def list_site_files(
    payload: dict[str, Any],
    *,
    filesystem: Filesystem | None = None,
) -> dict[str, Any]:
    fs = filesystem or LocalFilesystem()
    request = _validated_files_request(payload)
    if not fs.is_dir(request["target_path"]):
        return {
            "status": "missing_directory",
            "root_path": request["root_path"],
            "relative_subpath": request["relative_subpath"],
            "target_path": request["target_path"],
            "page": request["page"],
            "page_size": request["page_size"],
            "max_depth": 1,
            "total_entries": 0,
            "has_next": False,
            "entries": [],
        }

    entries = sorted(
        fs.list_dir(request["target_path"]),
        key=lambda entry: (not entry.is_dir, entry.name.lower()),
    )
    total_entries = len(entries)
    start = (request["page"] - 1) * request["page_size"]
    stop = start + request["page_size"]
    return {
        "status": "completed",
        "root_path": request["root_path"],
        "relative_subpath": request["relative_subpath"],
        "target_path": request["target_path"],
        "page": request["page"],
        "page_size": request["page_size"],
        "max_depth": 1,
        "total_entries": total_entries,
        "has_next": stop < total_entries,
        "entries": [
            {
                "name": entry.name,
                "type": "directory" if entry.is_dir else "file",
                "size": entry.size,
                "modified_at": entry.modified_at,
                "relative_path": _join_relative_path(request["relative_subpath"], entry.name),
            }
            for entry in entries[start:stop]
        ],
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


def _validated_logs_request(payload: dict[str, Any]) -> dict[str, Any]:
    domain = _required_string(payload, "domain").lower()
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise ValueError("Invalid domain.")

    allowed_log_base = _safe_base(
        payload.get("allowed_log_base", DEFAULT_ALLOWED_LOG_BASE),
        "allowed log base",
    )
    line_limit = payload.get("line_limit", 100)
    if not isinstance(line_limit, int) or isinstance(line_limit, bool):
        raise ValueError("line_limit must be an integer.")
    if line_limit < 1:
        raise ValueError("line_limit must be at least 1.")
    line_limit = min(line_limit, MAX_LOG_LINES)

    expected_access_log_path = f"{allowed_log_base}/{domain}.access.log"
    expected_error_log_path = f"{allowed_log_base}/{domain}.error.log"
    access_log_path = _safe_child_path(
        str(payload.get("access_log_path", expected_access_log_path)),
        allowed_log_base,
        "access log path",
    )
    error_log_path = _safe_child_path(
        str(payload.get("error_log_path", expected_error_log_path)),
        allowed_log_base,
        "error log path",
    )
    if access_log_path != expected_access_log_path:
        raise ValueError("Access log path must match the site domain under the allowed log path.")
    if error_log_path != expected_error_log_path:
        raise ValueError("Error log path must match the site domain under the allowed log path.")

    return {
        "domain": domain,
        "allowed_log_base": allowed_log_base,
        "line_limit": line_limit,
        "access_log_path": access_log_path,
        "error_log_path": error_log_path,
    }


def _validated_files_request(payload: dict[str, Any]) -> dict[str, Any]:
    allowed_webroot_base = _safe_base(
        payload.get("allowed_webroot_base", DEFAULT_ALLOWED_WEBROOT_BASE),
        "allowed webroot base",
    )
    root_path = _safe_child_path(
        _required_string(payload, "root_path"),
        allowed_webroot_base,
        "site root path",
    )
    relative_subpath = _safe_relative_path(str(payload.get("relative_subpath", "")))
    target_path = root_path if not relative_subpath else f"{root_path}/{relative_subpath}"
    target_path = _safe_child_path(target_path, root_path, "target path")

    page = payload.get("page", 1)
    if not isinstance(page, int) or isinstance(page, bool):
        raise ValueError("page must be an integer.")
    if page < 1:
        raise ValueError("page must be at least 1.")

    page_size = payload.get("page_size", 50)
    if not isinstance(page_size, int) or isinstance(page_size, bool):
        raise ValueError("page_size must be an integer.")
    if page_size < 1:
        raise ValueError("page_size must be at least 1.")
    page_size = min(page_size, MAX_FILE_PAGE_SIZE)

    return {
        "allowed_webroot_base": allowed_webroot_base,
        "root_path": root_path,
        "relative_subpath": relative_subpath,
        "target_path": target_path,
        "page": page,
        "page_size": page_size,
    }


def _validated_disable_request(payload: dict[str, Any]) -> dict[str, str]:
    domain = _required_string(payload, "domain").lower()
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise ValueError("Invalid domain.")

    allowed_nginx_base = _safe_base(
        payload.get("allowed_nginx_base", DEFAULT_ALLOWED_NGINX_BASE),
        "allowed nginx base",
    )
    target_config_path = _safe_child_path(
        _required_string(payload, "target_config_path"),
        allowed_nginx_base,
        "target config path",
    )
    expected_config_path = f"{allowed_nginx_base}/{domain}.conf"
    if target_config_path != expected_config_path:
        raise ValueError("Target config path must match the site domain under the allowed Nginx path.")

    return {
        "domain": domain,
        "allowed_nginx_base": allowed_nginx_base,
        "target_config_path": target_config_path,
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


def _safe_relative_path(path: str) -> str:
    raw_value = path.strip()
    if not raw_value:
        return ""
    if "\\" in raw_value or "\x00" in raw_value or raw_value.startswith("/"):
        raise ValueError("relative_subpath must be a safe relative path.")
    value = raw_value.strip("/")
    normalized = posixpath.normpath(value)
    if normalized in {"", "."}:
        return ""
    if normalized != value or ".." in normalized.split("/"):
        raise ValueError("relative_subpath must not contain traversal or redundant segments.")
    return normalized


def _join_relative_path(base: str, name: str) -> str:
    return name if not base else f"{base}/{name}"


def _tail_log_file(fs: Filesystem, path: str, line_limit: int) -> dict[str, Any]:
    if not fs.exists(path):
        return {
            "path": path,
            "missing": True,
            "lines": [],
        }
    content = fs.read_text(path)
    return {
        "path": path,
        "missing": False,
        "lines": content.splitlines()[-line_limit:],
    }


def _command_result(result: CommandResult) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
