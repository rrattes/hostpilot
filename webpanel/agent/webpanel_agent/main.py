from webpanel_agent.server import agent_health, run_server


def health_check() -> dict[str, object]:
    return agent_health()


def main() -> None:
    run_server()


if __name__ == "__main__":
    main()
