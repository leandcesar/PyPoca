# -*- coding: utf-8 -*-
import disnake
from disnake.ext import commands

from pypoca.config import COLOR
from pypoca.database import Server
from pypoca.exceptions import NoResults
from pypoca.services import tmdb, trakt
from pypoca.ext import ALL, DEFAULT, DEFAULT_LANGUAGE, DEFAULT_REGION, Choice, Movie, Option


class MovieButtons(disnake.ui.View):
    def __init__(self, inter: disnake.MessageInteraction, *, movie: Movie) -> None:
        self.movie = movie
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        super().__init__(timeout=120)
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_TRAILER"], url=movie.youtube, disabled=(not movie.youtube_id)))
        self.add_item(disnake.ui.Button(label="IMDb", url=movie.imdb, disabled=(not movie.imdb_id)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_CAST"], disabled=(not movie.cast)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_CREW"], disabled=(not movie.crew)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_MOVIE_BUTTON_SIMILAR"], disabled=(not movie.similar)))
        self.children[2].callback = self.cast
        self.children[3].callback = self.crew
        self.children[4].callback = self.similar

    async def cast(self, inter: disnake.MessageInteraction) -> None:
        await inter.bot.get_cog("People")._reply(inter, results=self.movie.cast)

    async def crew(self, inter: disnake.MessageInteraction) -> None:
        await inter.bot.get_cog("People")._reply(inter, results=self.movie.crew)

    async def similar(self, inter: disnake.MessageInteraction) -> None:
        await inter.bot.get_cog("Movies")._reply(inter, results=self.movie.similar)


class MovieEmbed(disnake.Embed):
    def __init__(self, inter: disnake.MessageInteraction, *, movie: Movie) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        locale = ALL[language]
        super().__init__(title=movie.title, description=movie.overview, color=COLOR)
        if movie.homepage:
            self.url = movie.homepage
        if movie.image:
            self.set_image(url=movie.image)
        if movie.directors:
            self.set_author(name=", ".join(movie.directors))
        self.add_field(
            name=locale["COMMAND_MOVIE_FIELD_RATING"], value=movie.rating_and_votes or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_MOVIE_FIELD_RELEASED"], value=movie.release_date.strftime(locale["DATETIME_FORMAT"]) if movie.release_date else "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_MOVIE_FIELD_RUNTIME"], value=movie.duration or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_MOVIE_FIELD_GENRE"], value=", ".join(movie.genres) or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_MOVIE_FIELD_STUDIOS"], value=", ".join(movie.studios) or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_TV_FIELD_WATCH"], value=", ".join(movie.watch_on(region)) or "-", inline=True
        )


class MovieDropdown(disnake.ui.Select):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, *, movies: list[Movie]) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        options = [
            disnake.SelectOption(
                label=movie.title_and_year[:100],
                value=movie.id,
                description=movie.rating_and_votes or "",
            )
            for movie in movies
        ]
        super().__init__(placeholder=locale["PLACEHOLDER"], options=options[:25])

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        movie_id = int(self.values[0])
        result = await tmdb.Movie(id=movie_id, language=language, region=region).details(
            append="credits,external_ids,recommendations,similar,videos,watch/providers"
        )
        try:
            result["external_ids"]["trakt_id"] = await trakt.Movie().trakt_id_by_tmdb_id(movie_id)
        except Exception as e:
            result["external_ids"]["trakt_id"] = None
        movie = Movie(result)
        await inter.response.send_message(
            embed=MovieEmbed(inter, movie=movie), view=MovieButtons(inter, movie=movie)
        )


class MovieSelect(disnake.ui.View):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, *, movies: list[Movie]) -> None:
        super().__init__()
        self.add_item(MovieDropdown(inter, movies=movies))


class Movies(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _reply(self, inter: disnake.ApplicationCommandInteraction, *, results: list[dict]) -> None:
        if len(results) == 0:
            raise NoResults()
        elif len(results) == 1:
            server = Server.get_by_id(inter.guild.id)
            language = server.language if server else DEFAULT_LANGUAGE
            region = server.region if server else DEFAULT_REGION
            movie_id = Movie(results[0]).id
            result = await tmdb.Movie(id=movie_id, language=language, region=region).details(
                append="credits,external_ids,recommendations,similar,videos,watch/providers"
            )
            try:
                result["external_ids"]["trakt_id"] = await trakt.Movie().trakt_id_by_tmdb_id(movie_id)
            except Exception as e:
                result["external_ids"]["trakt_id"] = None
            movie = Movie(result)
            await inter.send(
                embed=MovieEmbed(inter, movie=movie), view=MovieButtons(inter, movie=movie)
            )
        else:
            await inter.send(view=MovieSelect(inter, movies=[Movie(result) for result in results]))

    @commands.group(name="movie", description=DEFAULT["COMMAND_MOVIE_DESC"])
    async def movie(self, ctx: commands.Context) -> None:
        print(ctx)

    @movie.command(name="discover", description=DEFAULT["COMMAND_MOVIE_DISCOVER_DESC"])
    async def discover(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).discover()
        await self._reply(ctx, results=response["results"][:1])

    @movie.command(name="popular", description=DEFAULT["COMMAND_MOVIE_POPULAR_DESC"])
    async def popular(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).popular()
        await self._reply(ctx, results=response["results"][:1])

    @movie.command(name="search", description=DEFAULT["COMMAND_MOVIE_SEARCH_DESC"])
    async def search(self, ctx: commands.Context, query: str = Option.query) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).search(query)
        await self._reply(ctx, results=response["results"][:1])

    @movie.command(name="top", description=DEFAULT["COMMAND_MOVIE_TOP_DESC"])
    async def top(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).top_rated()
        await self._reply(ctx, results=response["results"][:1])

    @movie.command(name="trending", description=DEFAULT["COMMAND_MOVIE_TRENDING_DESC"])
    async def trending(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).trending()
        await self._reply(ctx, results=response["results"][:1])

    @movie.command(name="upcoming", description=DEFAULT["COMMAND_MOVIE_UPCOMING_DESC"])
    async def upcoming(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).upcoming()
        await self._reply(ctx, results=response["results"][:1])

    @commands.slash_command(name="movie", description=DEFAULT["COMMAND_MOVIE_DESC"])
    async def slash_movie(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @slash_movie.sub_command(name="discover", description=DEFAULT["COMMAND_MOVIE_DISCOVER_DESC"])
    async def slash_discover(
        self,
        inter: disnake.ApplicationCommandInteraction,
        sort_by: Choice.movie_sort_by = Option.movie_sort_by,
        service: Choice.movie_service = Option.movie_service,
        genre: Choice.movie_genre = Option.movie_genre,
        nsfw: Choice.boolean = Option.nsfw,
        year: int = Option.year,
        min_year: int = Option.min_year,
        max_year: int = Option.max_year,
        min_votes: int = Option.min_votes,
        max_votes: int = Option.max_votes,
        min_rating: float = Option.min_rating,
        max_rating: float = Option.max_rating,
        min_runtime: int = Option.min_runtime,
        max_runtime: int = Option.max_runtime,
        page: int = Option.page,
    ) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).discover(
            page=page,
            include_adult=nsfw,
            sort_by=sort_by,
            with_watch_providers=service,
            with_genres=genre,
            year=year if year != -1 else None,
            primary_release_date__gte=f"{min_year}-01-01" if min_year != -1 else None,
            primary_release_date__lte=f"{max_year}-12-31" if max_year != -1 else None,
            vote_count__gte=min_votes if min_votes != -1 else None,
            vote_count__lte=max_votes if max_votes != -1 else None,
            vote_average__gte=min_rating if min_rating != -1 else None,
            vote_average__lte=max_rating if max_rating != -1 else None,
            with_runtime__gte=min_runtime if min_runtime != -1 else None,
            with_runtime__lte=max_runtime if max_runtime != -1 else None,
        )
        await self._reply(inter, results=response["results"])

    @slash_movie.sub_command(name="popular", description=DEFAULT["COMMAND_MOVIE_POPULAR_DESC"])
    async def slash_popular(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).popular(page=page)
        await self._reply(inter, results=response["results"])

    @slash_movie.sub_command(name="search", description=DEFAULT["COMMAND_MOVIE_SEARCH_DESC"])
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
        response = await tmdb.Movies(language=language, region=region).search(query, page=page, include_adult=nsfw, year=year)
        await self._reply(inter, results=response["results"])

    @slash_movie.sub_command(name="top", description=DEFAULT["COMMAND_MOVIE_TOP_DESC"])
    async def slash_top(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).top_rated(page=page)
        await self._reply(inter, results=response["results"])

    @slash_movie.sub_command(name="trending", description=DEFAULT["COMMAND_MOVIE_TRENDING_DESC"])
    async def slash_trending(
        self, inter: disnake.ApplicationCommandInteraction, interval: Choice.interval = Option.interval
    ) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).trending(interval=interval)
        await self._reply(inter, results=response["results"])

    @slash_movie.sub_command(name="upcoming", description=DEFAULT["COMMAND_MOVIE_UPCOMING_DESC"])
    async def slash_upcoming(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.Movies(language=language, region=region).upcoming(page=page)
        await self._reply(inter, results=response["results"])


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Movies(bot))
