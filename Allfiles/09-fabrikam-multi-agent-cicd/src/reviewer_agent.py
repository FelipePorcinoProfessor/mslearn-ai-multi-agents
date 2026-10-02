from agent_framework_foundry_hosting import ResponsesHostServer

from src.hosted_common import create_agent


def main() -> None:
    ResponsesHostServer(create_agent("reviewer")).run()


if __name__ == "__main__":
    main()
