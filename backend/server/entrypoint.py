"""PyInstaller entry point uses the same server as `python -m server`."""

from server.main import main

if __name__ == "__main__":
    main()
