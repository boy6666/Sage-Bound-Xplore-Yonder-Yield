from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    from .main import create_app

    host = os.environ.get("STUDENT_WORKBENCH_HOST", "127.0.0.1")
    port = int(os.environ.get("STUDENT_WORKBENCH_PORT", "8765"))
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    main()
