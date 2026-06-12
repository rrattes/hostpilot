import pytest

from webpanel_agent.actions.nginx import (
    CommandResult,
    FileEntry,
    apply_site_config,
    disable_site_config,
    list_site_files,
    tail_site_logs,
)
from webpanel_agent.contracts import AgentActionRequest
from webpanel_agent.actions.mock import run_mock_action
from webpanel_agent.policies.allowlist import allowed_actions


class FakeFilesystem:
    def __init__(self) -> None:
        self.directories: list[str] = []
        self.files: dict[str, str] = {}
        self.directory_entries: dict[str, list[FileEntry]] = {}
        self.removed: list[str] = []

    def makedirs(self, path: str) -> None:
        self.directories.append(path)

    def write_text(self, path: str, content: str) -> None:
        self.files[path] = content

    def exists(self, path: str) -> bool:
        return path in self.files

    def is_dir(self, path: str) -> bool:
        return path in self.directory_entries

    def list_dir(self, path: str) -> list[FileEntry]:
        return self.directory_entries[path]

    def read_text(self, path: str) -> str:
        return self.files[path]

    def remove_file(self, path: str) -> None:
        self.removed.append(path)
        self.files.pop(path, None)


class FakeRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = results
        self.commands: list[list[str]] = []

    def run(self, argv: list[str]) -> CommandResult:
        self.commands.append(argv)
        return self.results.pop(0)


def test_nginx_apply_action_is_allowlisted() -> None:
    assert "web.nginx.apply_site_config" in allowed_actions()
    assert "web.nginx.disable_site_config" in allowed_actions()
    assert "web.files.list_site_files" in allowed_actions()
    assert "web.logs.tail_site_logs" in allowed_actions()


def test_apply_site_config_success_uses_fixed_commands_and_paths() -> None:
    fs = FakeFilesystem()
    runner = FakeRunner([CommandResult(0), CommandResult(0)])

    result = apply_site_config(_payload(), filesystem=fs, command_runner=runner)

    assert result["applied"] is True
    assert result["reloaded"] is True
    assert fs.directories == [
        "/var/www/hostpilot-sites/example.com",
        "/etc/nginx/sites-available/hostpilot",
    ]
    assert "/etc/nginx/sites-available/hostpilot/example.com.conf" in fs.files
    assert runner.commands == [["nginx", "-t"], ["systemctl", "reload", "nginx"]]


def test_apply_site_config_rolls_back_when_validation_fails() -> None:
    fs = FakeFilesystem()
    runner = FakeRunner([CommandResult(1, stderr="bad config")])

    result = apply_site_config(_payload(), filesystem=fs, command_runner=runner)

    assert result["applied"] is False
    assert result["rolled_back"] is True
    assert result["reloaded"] is False
    assert fs.removed == ["/etc/nginx/sites-available/hostpilot/example.com.conf"]
    assert runner.commands == [["nginx", "-t"]]


def test_apply_site_config_rejects_unsafe_paths() -> None:
    payload = _payload()
    payload["target_config_path"] = "/etc/nginx/sites-available/default"

    with pytest.raises(ValueError):
        apply_site_config(payload, filesystem=FakeFilesystem(), command_runner=FakeRunner([]))


def test_run_mock_action_dispatches_controlled_nginx_apply() -> None:
    response = run_mock_action(
        AgentActionRequest(
            action="web.nginx.apply_site_config",
            payload={
                **_payload(),
                "target_config_path": "/etc/nginx/sites-available/default",
            },
            requested_by="test",
            request_id="req-1",
        )
    )

    assert response.success is False
    assert response.status == "rejected"


def test_disable_site_config_success_removes_only_hostpilot_config() -> None:
    fs = FakeFilesystem()
    fs.files["/etc/nginx/sites-available/hostpilot/example.com.conf"] = "server_name example.com;"
    fs.files["/etc/nginx/sites-available/default"] = "unrelated"
    runner = FakeRunner([CommandResult(0), CommandResult(0)])

    result = disable_site_config(_disable_payload(), filesystem=fs, command_runner=runner)

    assert result["disabled"] is True
    assert result["reloaded"] is True
    assert fs.removed == ["/etc/nginx/sites-available/hostpilot/example.com.conf"]
    assert "/etc/nginx/sites-available/hostpilot/example.com.conf" not in fs.files
    assert fs.files["/etc/nginx/sites-available/default"] == "unrelated"
    assert runner.commands == [["nginx", "-t"], ["systemctl", "reload", "nginx"]]


def test_disable_site_config_rolls_back_when_validation_fails() -> None:
    fs = FakeFilesystem()
    fs.files["/etc/nginx/sites-available/hostpilot/example.com.conf"] = "original config"
    runner = FakeRunner([CommandResult(1, stderr="bad config")])

    result = disable_site_config(_disable_payload(), filesystem=fs, command_runner=runner)

    assert result["disabled"] is False
    assert result["rolled_back"] is True
    assert result["reloaded"] is False
    assert fs.files["/etc/nginx/sites-available/hostpilot/example.com.conf"] == "original config"
    assert runner.commands == [["nginx", "-t"]]


def test_disable_site_config_rejects_unsafe_paths() -> None:
    payload = _disable_payload()
    payload["target_config_path"] = "/etc/nginx/sites-available/hostpilot/../default"

    with pytest.raises(ValueError):
        disable_site_config(payload, filesystem=FakeFilesystem(), command_runner=FakeRunner([]))


def test_disable_site_config_protects_unrelated_configs() -> None:
    fs = FakeFilesystem()
    fs.files["/etc/nginx/sites-available/hostpilot/other.com.conf"] = "unrelated"
    payload = _disable_payload()
    payload["target_config_path"] = "/etc/nginx/sites-available/hostpilot/other.com.conf"

    with pytest.raises(ValueError):
        disable_site_config(payload, filesystem=fs, command_runner=FakeRunner([]))

    assert fs.files["/etc/nginx/sites-available/hostpilot/other.com.conf"] == "unrelated"
    assert fs.removed == []


def test_run_mock_action_dispatches_controlled_nginx_disable() -> None:
    response = run_mock_action(
        AgentActionRequest(
            action="web.nginx.disable_site_config",
            payload={
                **_disable_payload(),
                "target_config_path": "/etc/nginx/sites-available/default",
            },
            requested_by="test",
            request_id="req-2",
        )
    )

    assert response.success is False
    assert response.status == "rejected"


def test_tail_site_logs_reads_allowed_site_logs() -> None:
    fs = FakeFilesystem()
    fs.files["/var/log/nginx/hostpilot/example.com.access.log"] = "a1\na2\na3\n"
    fs.files["/var/log/nginx/hostpilot/example.com.error.log"] = "e1\ne2\n"

    result = tail_site_logs(_logs_payload(2), filesystem=fs)

    assert result["status"] == "completed"
    assert result["line_limit"] == 2
    assert result["logs"]["access"]["lines"] == ["a2", "a3"]
    assert result["logs"]["error"]["lines"] == ["e1", "e2"]
    assert result["logs"]["access"]["missing"] is False


def test_tail_site_logs_rejects_unsafe_path() -> None:
    payload = _logs_payload(20)
    payload["access_log_path"] = "/var/log/nginx/default/access.log"

    with pytest.raises(ValueError):
        tail_site_logs(payload, filesystem=FakeFilesystem())


def test_tail_site_logs_clamps_max_lines() -> None:
    fs = FakeFilesystem()
    fs.files["/var/log/nginx/hostpilot/example.com.access.log"] = "\n".join(
        f"line-{index}" for index in range(700)
    )
    fs.files["/var/log/nginx/hostpilot/example.com.error.log"] = ""

    result = tail_site_logs(_logs_payload(900), filesystem=fs)

    assert result["line_limit"] == 500
    assert len(result["logs"]["access"]["lines"]) == 500
    assert result["logs"]["access"]["lines"][0] == "line-200"


def test_tail_site_logs_returns_missing_log_file_state() -> None:
    result = tail_site_logs(_logs_payload(50), filesystem=FakeFilesystem())

    assert result["logs"]["access"]["missing"] is True
    assert result["logs"]["access"]["lines"] == []
    assert result["logs"]["error"]["missing"] is True


def test_run_mock_action_dispatches_web_log_tail() -> None:
    response = run_mock_action(
        AgentActionRequest(
            action="web.logs.tail_site_logs",
            payload={
                **_logs_payload(20),
                "access_log_path": "/var/log/nginx/default/access.log",
            },
            requested_by="test",
            request_id="req-3",
        )
    )

    assert response.success is False
    assert response.status == "rejected"


def test_list_site_files_lists_allowed_site_root() -> None:
    fs = FakeFilesystem()
    fs.directory_entries["/var/www/hostpilot-sites/example.com"] = [
        FileEntry(name="index.html", is_dir=False, size=120, modified_at=10),
        FileEntry(name="public", is_dir=True, size=4096, modified_at=20),
    ]

    result = list_site_files(_files_payload(), filesystem=fs)

    assert result["status"] == "completed"
    assert result["target_path"] == "/var/www/hostpilot-sites/example.com"
    assert [entry["name"] for entry in result["entries"]] == ["public", "index.html"]
    assert result["entries"][0]["type"] == "directory"
    assert result["entries"][0]["relative_path"] == "public"


def test_list_site_files_rejects_traversal() -> None:
    payload = _files_payload()
    payload["relative_subpath"] = "../other-site"

    with pytest.raises(ValueError):
        list_site_files(payload, filesystem=FakeFilesystem())


def test_list_site_files_enforces_root_boundary() -> None:
    payload = _files_payload()
    payload["root_path"] = "/home/example.com"

    with pytest.raises(ValueError):
        list_site_files(payload, filesystem=FakeFilesystem())


def test_list_site_files_returns_missing_directory_state() -> None:
    result = list_site_files(_files_payload(), filesystem=FakeFilesystem())

    assert result["status"] == "missing_directory"
    assert result["entries"] == []
    assert result["total_entries"] == 0


def test_list_site_files_paginates_and_clamps_limit() -> None:
    fs = FakeFilesystem()
    fs.directory_entries["/var/www/hostpilot-sites/example.com"] = [
        FileEntry(name=f"file-{index}.txt", is_dir=False, size=index, modified_at=float(index))
        for index in range(130)
    ]
    payload = _files_payload()
    payload["page_size"] = 500
    payload["page"] = 2

    result = list_site_files(payload, filesystem=fs)

    assert result["page_size"] == 100
    assert result["page"] == 2
    assert result["total_entries"] == 130
    assert result["has_next"] is False
    assert len(result["entries"]) == 30


def test_run_mock_action_dispatches_web_file_listing() -> None:
    response = run_mock_action(
        AgentActionRequest(
            action="web.files.list_site_files",
            payload={**_files_payload(), "relative_subpath": "../escape"},
            requested_by="test",
            request_id="req-4",
        )
    )

    assert response.success is False
    assert response.status == "rejected"


def _payload() -> dict[str, str]:
    config = """server {
    listen 80;
    server_name example.com;
    root /var/www/hostpilot-sites/example.com;
    index index.php index.html;
}
"""
    return {
        "domain": "example.com",
        "webroot_path": "/var/www/hostpilot-sites/example.com",
        "target_config_path": "/etc/nginx/sites-available/hostpilot/example.com.conf",
        "config_content": config,
        "allowed_webroot_base": "/var/www/hostpilot-sites",
        "allowed_nginx_base": "/etc/nginx/sites-available/hostpilot",
    }


def _disable_payload() -> dict[str, str]:
    return {
        "domain": "example.com",
        "target_config_path": "/etc/nginx/sites-available/hostpilot/example.com.conf",
        "allowed_nginx_base": "/etc/nginx/sites-available/hostpilot",
    }


def _logs_payload(line_limit: int) -> dict[str, object]:
    return {
        "domain": "example.com",
        "line_limit": line_limit,
        "allowed_log_base": "/var/log/nginx/hostpilot",
    }


def _files_payload() -> dict[str, object]:
    return {
        "root_path": "/var/www/hostpilot-sites/example.com",
        "relative_subpath": "",
        "page": 1,
        "page_size": 50,
        "allowed_webroot_base": "/var/www/hostpilot-sites",
    }
