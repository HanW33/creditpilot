"""Local entry point for the synthetic analyst interface."""

import uvicorn

from creditpilot.interface.operations import RuntimeConfig


def main() -> None:
    config = RuntimeConfig.from_environment()
    uvicorn.run(
        "creditpilot.interface.app:app",
        host=config.host,
        port=config.port,
        reload=False,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
