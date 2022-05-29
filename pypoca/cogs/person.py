# -*- coding: utf-8 -*-
import disnake
from disnake.ext import commands

from pypoca.config import COLOR
from pypoca.database import Server
from pypoca.exceptions import NoResults
from pypoca.services import tmdb, trakt
from pypoca.ext import ALL, DEFAULT, DEFAULT_LANGUAGE, DEFAULT_REGION, Choice, Option, Person


class PersonButtons(disnake.ui.View):
    def __init__(self, inter: disnake.MessageInteraction, *, person: Person) -> None:
        self.person = person
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        super().__init__(timeout=120)
        self.add_item(disnake.ui.Button(label="IMDb", url=person.imdb, disabled=(not person.imdb_id)))
        self.add_item(disnake.ui.Button(label="Instagram", url=person.instagram, disabled=(not person.instagram_id)))
        self.add_item(disnake.ui.Button(label="Twitter", url=person.twitter, disabled=(not person.twitter_id)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_PERSON_BUTTON_ACTING"], disabled=(not person.cast)))
        self.add_item(disnake.ui.Button(label=locale["COMMAND_PERSON_BUTTON_JOBS"], disabled=(not person.crew)))
        self.children[3].callback = self.cast
        self.children[4].callback = self.crew

    async def cast(self, inter: disnake.MessageInteraction) -> None:
        if len(self.person.cast_movies) >= len(self.person.cast_shows):
            await inter.bot.get_cog("Movies")._reply(inter, results=self.person.cast_movies)
        else:
            await inter.bot.get_cog("Shows")._reply(inter, results=self.person.cast_shows)

    async def crew(self, inter: disnake.MessageInteraction) -> None:
        if len(self.person.crew_movies) >= len(self.person.crew_shows):
            await inter.bot.get_cog("Movies")._reply(inter, results=self.person.crew_movies)
        else:
            await inter.bot.get_cog("Shows")._reply(inter, results=self.person.cast_shows)


class PersonEmbed(disnake.Embed):
    def __init__(self, inter: disnake.MessageInteraction, *, person: Person) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        super().__init__(title=person.name, description=person.biography, color=COLOR)
        if person.homepage:
            self.url = person.homepage
        if person.image:
            self.set_thumbnail(url=person.image)
        self.add_field(
            name=locale["COMMAND_PERSON_FIELD_BIRTHDAY"], value=person.birthday.strftime(locale["DATETIME_FORMAT"]) if person.birthday else "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_PERSON_FIELD_DEATHDAY"], value=person.deathday.strftime(locale["DATETIME_FORMAT"]) if person.deathday else "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_PERSON_FIELD_BORN"], value=person.place_of_birth or "-", inline=True
        )
        self.add_field(
            name=locale["COMMAND_PERSON_FIELD_KNOW_FOR"], value=", ".join(person.jobs[:6]) or "-", inline=False
        )


class PersonDropdown(disnake.ui.Select):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, *, people: list[Person]) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        options = [
            disnake.SelectOption(
                label=person.name[:100],
                value=person.id,
                description=", ".join(person.jobs[:5])[:100],
            )
            for person in people
        ]
        super().__init__(placeholder=locale["PLACEHOLDER"], options=options[:25])

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        person_id = int(self.values[0])
        result = await tmdb.Person(id=person_id, language=language, region=region).details(
            append="combined_credits,external_ids"
        )
        person = Person(result)
        await inter.response.send_message(
            embed=PersonEmbed(inter, person=person), view=PersonButtons(inter, person=person)
        )


class PersonSelect(disnake.ui.View):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, *, people: list[Person]) -> None:
        super().__init__()
        self.add_item(PersonDropdown(inter, people=people))


class People(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _reply(self, inter: disnake.ApplicationCommandInteraction, *, results: list[dict]) -> None:
        if len(results) == 0:
            raise NoResults()
        elif len(results) == 1:
            server = Server.get_by_id(inter.guild.id)
            language = server.language if server else DEFAULT_LANGUAGE
            region = server.region if server else DEFAULT_REGION
            person_id = Person(results[0]).id
            result = await tmdb.Person(id=person_id, language=language, region=region).details(
                append="combined_credits,external_ids"
            )
            person = Person(result)
            await inter.send(
                embed=PersonEmbed(inter, person=person), view=PersonButtons(inter, person=person)
            )
        else:
            await inter.send(view=PersonSelect(inter, people=[Person(result) for result in results]))

    @commands.group(name="people", description=DEFAULT["COMMAND_PERSON_DESC"])
    async def person(self, ctx: commands.Context) -> None:
        pass

    @person.command(name="popular", description=DEFAULT["COMMAND_PERSON_POPULAR_DESC"])
    async def popular(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.People(language=language, region=region).popular()
        await self._reply(ctx, results=response["results"][:1])

    @person.command(name="search", description=DEFAULT["COMMAND_PERSON_SEARCH_DESC"])
    async def search(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.People(language=language, region=region).search(query)
        await self._reply(ctx, results=response["results"][:1])

    @person.command(name="trending", description=DEFAULT["COMMAND_PERSON_TRENDING_DESC"])
    async def trending(self, ctx: commands.Context) -> None:
        server = Server.get_by_id(ctx.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.People(language=language, region=region).trending()
        await self._reply(ctx, results=response["results"][:1])

    @commands.slash_command(name="people", description=DEFAULT["COMMAND_PERSON_DESC"])
    async def slash_person(self, inter: disnake.ApplicationCommandInteraction) -> None:
        pass

    @slash_person.sub_command(name="popular", description=DEFAULT["COMMAND_PERSON_POPULAR_DESC"])
    async def slash_popular(self, inter: disnake.ApplicationCommandInteraction, page: int = Option.page) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.People(language=language, region=region).popular(page=page)
        await self._reply(inter, results=response["results"])

    @slash_person.sub_command(name="search", description=DEFAULT["COMMAND_PERSON_SEARCH_DESC"])
    async def slash_search(
        self,
        inter: disnake.ApplicationCommandInteraction,
        query: str = Option.query,
        nsfw: Choice.boolean = Option.nsfw,
        page: int = Option.page,
    ) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.People(language=language, region=region).search(query, page=page, include_adult=nsfw)
        await self._reply(inter, results=response["results"])

    @slash_person.sub_command(name="trending", description=DEFAULT["COMMAND_PERSON_TRENDING_DESC"])
    async def slash_trending(self, inter: disnake.ApplicationCommandInteraction, interval: Choice.interval = Option.interval) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        region = server.region if server else DEFAULT_REGION
        response = await tmdb.People(language=language, region=region).trending(interval=interval)
        await self._reply(inter, results=response["results"])


def setup(bot: commands.Bot) -> None:
    bot.add_cog(People(bot))
