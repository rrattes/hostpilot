from typing import TypedDict


class MockSystemInfo(TypedDict):
    hostname: str
    os: str
    cpu_load_percent: int
    memory_used_percent: int
    disk_used_percent: int


def get_mock_system_info() -> MockSystemInfo:
    return {
        "hostname": "hostpilot-local-dev",
        "os": "Ubuntu Server 26.04 LTS",
        "cpu_load_percent": 18,
        "memory_used_percent": 42,
        "disk_used_percent": 37,
    }
