import pytest

from webpanel_agent.actions.nginx import CommandResult, apply_site_config
from webpanel_agent.contracts import AgentActionRequest
from webpanel_agent.actions.mock import run_mock_action
from webpanel_agent.policies.allowlist import allowed_actions


class FakeFilesystem:
    def __init__(self) -> None:
        self.directories: list[str] = []
        self.files: dict[str, str] = {}
        self.removed: list[str] = []

    def makedirs(self, path: str) -> None:
        self.directories.append(path)

    def write_text(self, path: str, content: str) -> None:
        self.files[path] = content

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
