"""Local entry point for the synthetic analyst interface."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "creditpilot.interface.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
