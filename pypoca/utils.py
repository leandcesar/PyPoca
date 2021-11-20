# -*- coding: utf-8 -*-
from aiohttp import ClientSession
from datetime import datetime

from pypoca.languages import DATETIME_STR
from pypoca.config import TraktTVConfig

__all__ = (
    "format_datetime",
    "format_duration",
    "get_trakt_id",
    "watch_provider_url",
    "slash_data_option_to_str",
)


def format_datetime(value: str, from_format: str = "%Y-%m-%d", to_format: str = DATETIME_STR) -> str:
    """Convert a datetime string to different string format."""
    if not value:
        return None
    return datetime.strptime(value, from_format).strftime(to_format)


def format_duration(value: str) -> str:
    """Convert a duration in minutes to a duration in hours and minutes."""
    if not value:
        return None
    hours, minutes = divmod(int(value), 60)
    if hours == 0:
        return f"{minutes}min"
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}min"


async def get_trakt_id(tmdb_id: str, type: str) -> str:
    """Get the Trakt.tv ID from the TMDb ID."""
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": TraktTVConfig.client_id,
    }
    async with ClientSession() as session:
        async with session.get(f"https://api.trakt.tv/search/tmdb/{tmdb_id}", headers=headers) as response:
            data = await response.json()
    trakt_id = data[0][type]["ids"]["trakt"]
    return trakt_id


def watch_provider_url(watch_provider: str, type: str, trakt_id: str, region: str) -> str:
    """Get the watch provider Trakt.tv URL from the watch provider name."""
    raw_url = f"https://trakt.tv/watchnow/{type}/{trakt_id}/1/{region}/{watch_provider}"
    url = raw_url.replace(" ", "_").lower()
    return url


def slash_data_option_to_str(data_options: dict) -> str:
    """Convert a Slash Interaction data option to string."""
    options = []
    for option in data_options.values():
        if option.name and option.value:
            options.append(f"{option.name}={option.value}")
        elif option.name:
            options.append(option.name)
        if option.options:
            for opt in option.options.values():
                options.append(f"{opt.name}={opt.value}")
    return " ".join(options)
