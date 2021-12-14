# -*- coding: utf-8 -*-
from aiotmdb import AsObj

from pypoca import utils
from pypoca.embeds import Color
from pypoca.languages import Language

__all__ = ("embed", "option", "buttons")


def embed(result: AsObj, language: str, region: str) -> dict:
    """Convert a `AsObj` movie result to a `dict` with Discord embed items."""
    vote_average = result.get("vote_average")
    vote_count = result.get("vote_count")
    genres = [genre["name"] for genre in result.get("genres", [])]
    production_companies = [company["name"] for company in result.get("production_companies", [])]
    rating = f"{vote_average} ({vote_count} votes)" if vote_average else None
    release_date = utils.format_datetime(
        result.release_date, to_format=Language(language).datetime_format
    ) or result.get("status")
    duration = utils.format_duration(result.get("runtime"))
    try:
        watch_providers = [
            watch_provider["provider_name"]
            for watch_provider in result["watch/providers"]["results"][region]["flatrate"]
        ]
    except Exception:
        watch_providers = []
    try:
        trakt_id = result["external_ids"]["trakt"]
        watch_providers = [
            f"[{watch_provider}]({utils.watch_provider_url(watch_provider, 'movie', trakt_id, region)})"
            for watch_provider in watch_providers
        ]
    except Exception:
        pass

    embed = {
        "title": result.get("title") or result.original_title,
        "description": result.get("overview"),
        "color": Color.bot,
        "fields": [
            {
                "name": Language(language).commands["movie"]["reply"]["fields"]["rating"],
                "value": rating or "-",
                "inline": True,
            },
            {
                "name": Language(language).commands["movie"]["reply"]["fields"]["released"],
                "value": release_date or "-",
                "inline": True,
            },
            {
                "name": Language(language).commands["movie"]["reply"]["fields"]["watch"],
                "value": ", ".join(watch_providers) if watch_providers else "-",
                "inline": True,
            },
            {
                "name": Language(language).commands["movie"]["reply"]["fields"]["runtime"],
                "value": duration or "-",
                "inline": True,
            },
            {
                "name": Language(language).commands["movie"]["reply"]["fields"]["genre"],
                "value": ", ".join(genres) if genres else "-",
                "inline": True,
            },
            {
                "name": Language(language).commands["movie"]["reply"]["fields"]["studios"],
                "value": ", ".join(production_companies) if production_companies else "-",
                "inline": True,
            },
        ],
    }
    if result.get("homepage"):
        embed["url"] = result.homepage
    if result.get("backdrop_path"):
        embed["image"] = {"url": f"https://image.tmdb.org/t/p/w1280/{result.backdrop_path}"}
    for person in result.credits.get("crew", []):
        if person["job"] == "Director":
            embed["author"] = {"name": person.name}
            if person.get("profile_path"):
                embed["author"]["icon_url"] = f"https://image.tmdb.org/t/p/w185/{person.profile_path}"
            break
    return embed


def option(result: AsObj, language: str) -> dict:
    """Convert a `AsObj` movie result to a `dict` with Discord option items."""
    title = result.get("title") or result.original_title
    release_date = utils.format_datetime(result.get("release_date"), to_format=Language(language).datetime_format)
    vote_average = result.get("vote_average")
    vote_count = result.get("vote_count")
    label = f"{title} ({release_date})" if release_date else title
    description = f"{vote_average} ({vote_count} votes)" if vote_average else ""
    option = {"label": label[:100], "description": description[:100]}
    return option


def buttons(result: AsObj, language: str) -> list:
    """Convert a `AsObj` movie result to a `dict` with Discord buttons items."""
    imdb_id = result.external_ids.get("imdb_id")
    try:
        video_key = result.videos["results"][0]["key"]
    except Exception:
        video_key = None
    buttons = [
        {
            "label": Language(language).commands["movie"]["reply"]["buttons"]["trailer"],
            "url": f"https://www.youtube.com/watch?v={video_key}",
            "disabled": not video_key,
            "style": 5,
        },
        {
            "label": "IMDb",
            "url": f"https://www.imdb.com/title/{imdb_id}",
            "disabled": not imdb_id,
            "style": 5,
        },
        {
            "label": Language(language).commands["movie"]["reply"]["buttons"]["cast"],
            "custom_id": "cast",
            "disabled": not result.credits.cast,
            "style": 2,
        },
        {
            "label": Language(language).commands["movie"]["reply"]["buttons"]["crew"],
            "custom_id": "crew",
            "disabled": not result.credits.crew,
            "style": 2,
        },
        {
            "label": Language(language).commands["movie"]["reply"]["buttons"]["similar"],
            "custom_id": "similar",
            "disabled": not result.recommendations.results,
            "style": 2,
        },
    ]
    return buttons
