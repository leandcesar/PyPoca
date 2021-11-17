# -*- coding: utf-8 -*-
from aiotmdb import TMDB
from discord.ext.commands import Bot, Cog
from dislash import ResponseType, SlashInteraction, slash_command

from pypoca.adapters import Adapter
from pypoca.config import TMDBConfig
from pypoca.embeds import Option, Buttons, Poster, Menu
from pypoca.exceptions import NotFound
from pypoca.languages import CommandDescription


class TV(Cog):
    """`TV` cog has all TV show related commands."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @staticmethod
    async def _reply(
        inter: SlashInteraction,
        *,
        results: list,
        page: int,
        total_pages: int,
        language: str,
        region: str,
    ) -> None:
        adapter = Adapter("tv")
        if len(results) > 1:
            embed = Poster(title="TV show results")
            select_menu = Menu(options=[adapter.option(result) for result in results])
            msg = await inter.reply(
                embed=embed,
                components=[select_menu],
                type=ResponseType.ChannelMessageWithSource,
            )

            def check(ctx: SlashInteraction):
                return ctx.author == inter.author

            ctx = await msg.wait_for_dropdown(check)
            index = int(ctx.select_menu.selected_options[0].value)
        elif len(results) == 1:
            index = 0
        else:
            raise NotFound()
        tv_id = results[index].id
        result = await TMDB.tv(language=language, region=region).details(
            tv_id,
            append_to_response="credits,external_ids,recommendations,videos,watch/providers",
        )
        embed = Poster(**adapter.embed(result, region=region))
        buttons = Buttons(buttons=adapter.buttons(result))
        if len(results) > 1:
            await ctx.reply(embed=embed, components=[buttons], type=ResponseType.UpdateMessage)
        else:
            await inter.reply(embed=embed, components=[buttons])

    @slash_command(name="tv", description=CommandDescription.tv)
    async def tv(self, inter: SlashInteraction):
        """Command that groups tv-related subcommands."""

    @tv.sub_command(
        name="discover",
        description=CommandDescription.discover_tv,
        options=[
            Option.tv_sort_by,
            Option.tv_service,
            Option.tv_genre,
            Option.year,
            Option.min_year,
            Option.max_year,
            Option.min_votes,
            Option.min_rating,
            Option.min_runtime,
            Option.max_runtime,
            Option.page,
            Option.language,
            Option.region,
        ],
        connectors={
            Option.tv_sort_by.name: "sort_by",
            Option.tv_service.name: "service",
            Option.tv_genre.name: "genre",
            Option.year.name: "year",
            Option.min_year.name: "min_year",
            Option.max_year.name: "max_year",
            Option.min_votes.name: "min_votes",
            Option.min_rating.name: "min_rating",
            Option.min_runtime.name: "min_runtime",
            Option.max_runtime.name: "max_runtime",
            Option.page.name: "page",
            Option.language.name: "language",
            Option.region.name: "region",
        },
    )
    async def discover_tv(
        self,
        inter: SlashInteraction,
        sort_by: str = "popularity.desc",
        service: str = None,
        genre: str = None,
        year: int = None,
        min_year: int = None,
        max_year: int = None,
        min_votes: int = None,
        min_rating: float = None,
        min_runtime: int = None,
        max_runtime: int = None,
        page: int = 1,
        language: str = TMDBConfig.language,
        region: str = TMDBConfig.region,
    ) -> None:
        """Subcommand to discover TV shows by different types of data."""
        discover = TMDB.discover(language=language, region=region)
        results = await discover.tv_shows(
            page=page,
            sort_by=sort_by,
            with_watch_providers=service,
            with_genres=genre,
            first_air_date_year=year,
            first_air_date__gte=f"{min_year}-01-01" if min_year else None,
            first_air_date__lte=f"{max_year}-12-31" if max_year else None,
            vote_count__gte=min_votes,
            vote_average__gte=min_rating,
            with_runtime__gte=min_runtime,
            with_runtime__lte=max_runtime,
        )
        await self._reply(
            inter,
            results=results,
            page=discover.page,
            total_pages=discover.total_pages,
            language=language,
            region=region,
        )

    @tv.sub_command(
        name="popular",
        description=CommandDescription.popular_tv,
        options=[Option.page, Option.language, Option.region],
        connectors={Option.page.name: "page", Option.language.name: "language", Option.region.name: "region"},
    )
    async def popular_tv(
        self,
        inter: SlashInteraction,
        page: int = 1,
        language: str = TMDBConfig.language,
        region: str = TMDBConfig.region,
    ) -> None:
        """Subcommand to get the current popular TV shows."""
        tv = TMDB.tv(language=language, region=region)
        results = await tv.popular(page=page)
        await self._reply(
            inter,
            results=results,
            page=tv.page,
            total_pages=tv.total_pages,
            language=language,
            region=region,
        )

    @tv.sub_command(
        name="search",
        description=CommandDescription.search_tv,
        options=[
            Option.query,
            Option.year,
            Option.nsfw,
            Option.page,
            Option.language,
            Option.region,
        ],
        connectors={
            Option.query.name: "query",
            Option.year.name: "year",
            Option.nsfw.name: "nsfw",
            Option.page.name: "page",
            Option.language.name: "language",
            Option.region.name: "region",
        },
    )
    async def search_tv(
        self,
        inter: SlashInteraction,
        query: str,
        year: int = None,
        nsfw: bool = False,
        page: int = 1,
        language: str = TMDBConfig.language,
        region: str = TMDBConfig.region,
    ) -> None:
        """Subcommand to search for a TV show."""
        search = TMDB.search(language=language, region=region)
        results = await search.tv_shows(query, page=page, include_adult=nsfw, first_air_date_year=year)
        await self._reply(
            inter,
            results=results,
            page=search.page,
            total_pages=search.total_pages,
            language=language,
            region=region,
        )

    @tv.sub_command(
        name="top",
        description=CommandDescription.top_tv,
        options=[Option.page, Option.language, Option.region],
        connectors={Option.page.name: "page", Option.language.name: "language", Option.region.name: "region"},
    )
    async def top_tv(
        self,
        inter: SlashInteraction,
        page: int = 1,
        language: str = TMDBConfig.language,
        region: str = TMDBConfig.region,
    ) -> None:
        """Subcommand get the top rated TV shows."""
        tv = TMDB.tv(language=language, region=region)
        results = await tv.top_rated(page=page)
        await self._reply(
            inter,
            results=results,
            page=tv.page,
            total_pages=tv.total_pages,
            language=language,
            region=region,
        )

    @tv.sub_command(
        name="trending",
        description=CommandDescription.trending_tv,
        options=[Option.interval, Option.language, Option.region],
        connectors={Option.interval.name: "interval", Option.language.name: "language", Option.region.name: "region"},
    )
    async def trending_tv(
        self,
        inter: SlashInteraction,
        interval: str = "day",
        language: str = TMDBConfig.language,
        region: str = TMDBConfig.region,
    ) -> None:
        """Subcommand get the trending TV shows."""
        trending = TMDB.trending(language=language, region=region)
        if interval == "day":
            results = await trending.tv_shows_day()
        else:
            results = await trending.tv_shows_week()
        await self._reply(
            inter,
            results=results,
            page=trending.page,
            total_pages=trending.total_pages,
            language=language,
            region=region,
        )

    @tv.sub_command(
        name="upcoming",
        description=CommandDescription.upcoming_tv,
        options=[Option.page, Option.language, Option.region],
        connectors={Option.page.name: "page", Option.language.name: "language", Option.region.name: "region"},
    )
    async def upcoming_tv(
        self,
        inter: SlashInteraction,
        page: int = 1,
        language: str = TMDBConfig.language,
        region: str = TMDBConfig.region,
    ) -> None:
        """Subcommand get the upcoming TV shows in theatres."""
        tv = TMDB.tv(language=language, region=region)
        results = await tv.on_the_air(page=page)
        await self._reply(
            inter,
            results=results,
            page=tv.page,
            total_pages=tv.total_pages,
            language=language,
            region=region,
        )


def setup(bot: Bot) -> None:
    """Setup `TV` cog."""
    bot.add_cog(TV(bot))