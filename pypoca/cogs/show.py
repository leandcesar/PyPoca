# -*- coding: utf-8 -*-
import disnake
from disnake.ext import commands

from pypoca.config import COLOR
from pypoca.database import Server
from pypoca.exceptions import NoResults
from pypoca.services import tmdb, trakt
from pypoca.ext import ALL, DEFAULT, DEFAULT_LANGUAGE, DEFAULT_REGION, Choice, Option, Show


class ShowButtons(disnake.ui.View):
    def __init__(self, inter: disnake.MessageInteraction, *, show: Show) -> None:
        self.show = show
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        super().__init__(timeout=120)
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_TRAILER"], url=show.youtube, disabled=(not show.youtube_id)))
        self.add_item(disnake.ui.Button(label="IMDb", url=show.imdb, disabled=(not show.imdb_id)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_CAST"], disabled=(not show.cast)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_CREW"], disabled=(not show.crew)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_SIMILAR"], disabled=(not show.similar)))
        self.children[2].callback = self.cast
        self.children[3].callback = self.crew
        self.children[4].callback = self.similar

    async def cast(self, inter: disnake.MessageInteraction) -> None:
        await inter.bot.get_cog("People")._reply(inter, results=self.show.cast)

    async def crew(self, inter: disnake.MessageInteraction) -> None:
        await inter.bot.get_cog("People")._reply(inter, results=self.show.crew)

    async def similar(self, inter: disnake.MessageInteraction) -> None:
        await inter.bot.get_cog("Shows")._reply(inter, results=self.show.similar)


class ShowEmbed(disnake.Embed):
    def __init__(self, inter: disnake.MessageInteraction, *, show: Show) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        locale = ALL[language]
        super().__init__(title=show.title, description=show.overview, color=COLOR)
        if show.homepage:
            self.url = show.homepage
        if show.image:
            self.set_image(url=show.image)
        if show.directors:
            self.set_author(name=", ".join(show.directors))
        self.add_field(
            name=locale["COMMAND_TV_FIELD_RATING"], value=show.rating_and_votes or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_PREMIERED"], value=show.first_date.strftime(locale["DATETIME_FORMAT"]) if show.first_date else "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_STATUS"],
            value=f"{show.status} ({show.last_date.year})" if show.status == "Ended" else show.status if show.status else "-",
            inline=True,
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_EPISODES"], value=str(show.number_of_episodes) or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_SEASONS"], value=str(show.number_of_seasons) or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_RUNTIME"], value=show.duration or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_GENRE"], value=", ".join(show.genres) or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_NETWORK"], value=", ".join(show.studios) or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_WATCH"], value=", ".join(show.watch_on(region)) or "-", inline=True
        )


class ShowDropdown(disnake.ui.Select):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, *, shows: list[Show]) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        options = [
            disnake.SelectOption(
                label=show.title_and_year[:100],
                value=show.id,
                description=show.rating_and_votes or "",
            )
            for show in shows
        ]
        super().__init__(placeholder=locale["PLACEHOLDER"], options=options[:25])

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        show_id = int(self.values[0])
        result = await tmdb.Show(id=show_id, language=language, region=region).details(
            append="credits,external_ids,recommendations,similar,videos,watch/providers"
        )
        try:
            result["external_ids"]["trakt_id"] = await trakt.Show().trakt_id_by_tmdb_id(show_id)
        except Exception as e:
            result["external_ids"]["trakt_id"] = None
        show = Show(result)
        await inter.response.send_message(
            embed=ShowEmbed(inter, show=show), view=ShowButtons(inter, show=show)
        )


class ShowSelect(disnake.ui.View):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, *, shows: list[Show]) -> None:
        super().__init__()
        self.add_item(ShowDropdown(inter, shows=shows))


class Shows(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _reply(self, inter: disnake.ApplicationCommandInteraction, *, results: list[dict]) -> None:
        if len(results) == 0:
            raise NoResults()
        elif len(results) == 1:
            server = Server.get_by_id(inter.guild.id)
            language = server.language if server else DEFAULT_LANGUAGE
            region = server.region if server else DEFAULT_REGION
            show_id = Show(results[0]).id
            result = await tmdb.Show(id=show_id, language=language, region=region).details(
                append="credits,external_ids,recommendations,similar,videos,watch/providers"
            )
            try:
                result["external_ids"]["trakt_id"] = await trakt.Show().trakt_id_by_tmdb_id(show_id)
            except Exception as e:
                result["external_ids"]["trakt_id"] = None
            show = Show(result)
            await inter.send(
                embed=ShowEmbed(inter, show=show), view=ShowButtons(inter, show=show)
            )
        else:
            await inter.send(view=ShowSelect(inter, shows=[Show(result) for result in results]))

    @commands.group(name="tv", description=DEFAULT["COMMAND_TV_DESC"])
    async def tv(self, ctx: commands.Context) -> None:
        pass

    @tv.command(name="discover", description=DEFAULT["COMMAND_TV_DISCOVER_DESC"])
    async def discover(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).discover()
        await self._reply(ctx, results=response["results"][:1])

    @tv.command(name="popular", description=DEFAULT["COMMAND_TV_POPULAR_DESC"])
    async def popular(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).popular()
        await self._reply(ctx, results=response["results"][:1])

    @tv.command(name="search", description=DEFAULT["COMMAND_TV_SEARCH_DESC"])
    async def search(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).search(query)
        await self._reply(ctx, results=response["results"][:1])

    @tv.command(name="top", description=DEFAULT["COMMAND_TV_TOP_DESC"])
    async def top(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).top_rated()
        await self._reply(ctx, results=response["results"][:1])

    @tv.command(name="trending", description=DEFAULT["COMMAND_TV_TRENDING_DESC"])
    async def trending(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).trending()
        await self._reply(ctx, results=response["results"][:1])

    @tv.command(name="upcoming", description=DEFAULT["COMMAND_TV_UPCOMING_DESC"])
    async def upcoming(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).on_the_air()
        await self._reply(ctx, results=response["results"][:1])

    @commands.slash_command(name="tv", description=DEFAULT["COMMAND_TV_DESC"])
    async def slash_tv(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @slash_tv.sub_command(name="discover", description=DEFAULT["COMMAND_TV_DISCOVER_DESC"])
    async def slash_discover(
        self,
        inter: disnake.ApplicationCommandInteraction,
        sort_by: Choice.tv_sort_by = Option.tv_sort_by,
        service: Choice.tv_service = Option.tv_service,
        genre: Choice.tv_genre = Option.tv_genre,
        year: int = Option.year,
        min_year: int = Option.min_year,
        max_year: int = Option.max_year,
        min_votes: int = Option.min_votes,
        min_rating: float = Option.min_rating,
        min_runtime: int = Option.min_runtime,
        max_runtime: int = Option.max_runtime,
        page: int = Option.page,
    ) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).discover(
            page=page,
            sort_by=sort_by,
            with_watch_providers=service,
            with_genres=genre,
            first_air_date_year=year if year != -1 else None,
            first_air_date__gte=f"{min_year}-01-01" if min_year != -1 else None,
            first_air_date__lte=f"{max_year}-12-31" if max_year != -1 else None,
            vote_count__gte=min_votes if min_votes != -1 else None,
            vote_average__gte=min_rating if min_rating != -1 else None,
            with_runtime__gte=min_runtime if min_runtime != -1 else None,
            with_runtime__lte=max_runtime if max_runtime != -1 else None,
        )
        await self._reply(inter, results=response["results"])

    @slash_tv.sub_command(name="popular", description=DEFAULT["COMMAND_TV_POPULAR_DESC"])
    async def slash_popular(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).popular(page=page)
        await self._reply(inter, results=response["results"])

    @slash_tv.sub_command(name="search", description=DEFAULT["COMMAND_TV_SEARCH_DESC"])
    async def slash_search(
        self,
        inter: disnake.ApplicationCommandInteraction,
        query: str = Option.query,
        year: int = Option.year,
        nsfw: Choice.boolean = Option.nsfw,
        page: int = Option.page,
    ) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).search(query, page=page, include_adult=nsfw, first_air_date_year=year)
        await self._reply(inter, results=response["results"])

    @slash_tv.sub_command(name="top", description=DEFAULT["COMMAND_TV_TOP_DESC"])
    async def slash_top(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).top_rated(page=page)
        await self._reply(inter, results=response["results"])

    @slash_tv.sub_command(name="trending", description=DEFAULT["COMMAND_TV_TRENDING_DESC"])
    async def slash_trending(
        self, inter: disnake.ApplicationCommandInteraction, interval: Choice.interval = Option.interval
    ) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).trending(interval=interval)
        await self._reply(inter, results=response["results"])

    @slash_tv.sub_command(name="upcoming", description=DEFAULT["COMMAND_TV_UPCOMING_DESC"])
    async def slash_upcoming(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Shows(language=language, region=region).on_the_air(page=page)
        await self._reply(inter, results=response["results"])


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Shows(bot))
