"""Version and locations, so the About card states facts instead of guesses."""

from pathlib import Path

from fastapi import APIRouter

from appdata.types import AppInfo
from version import VERSION


def about_routes(app_data: Path | None) -> APIRouter:
    router = APIRouter()

    @router.get("/about")
    def about() -> AppInfo:
        return AppInfo(
            version=VERSION,
            app_data=str(app_data) if app_data else "",
            log_directory=str(app_data / "logs") if app_data else "",
        )

    return router
