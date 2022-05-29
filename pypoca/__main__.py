# -*- coding: utf-8 -*-
import os

import disnake
from disnake.ext import commands

from pypoca.config import DB_CREDENTIALS, DEBUG, GUILDS_ID, TOKEN
from pypoca.database import Server, db
from pypoca.exceptions import NoResults
from pypoca.ext import ALL, DEFAULT_LANGUAGE
from pypoca.log import log


class PypocaBot(commands.Bot):
    def load_extensions(self, folder: str) -> None:
        for filename in os.listdir(folder):
            if filename.endswith(".py") and not filename.startswith("_"):
                self.load_extension(f"{folder}/{filename[:-3]}".replace("/", "."))

    async def on_ready(self) -> None:
        activity = disnake.Activity(type=disnake.ActivityType.watching, name="/help")
        await self.change_presence(activity=activity)

    async def on_slash_command_error(self, inter: disnake.AppCmdInter, error: commands.CommandError) -> None:
        server = Server.get_by_id(inter.guild.id)
        language = server.language if server else DEFAULT_LANGUAGE
        locale = ALL[language]
        if isinstance(error, commands.MissingPermissions):
            description = locale["ERROR_NO_PERMISSION_REPLY"]
        elif isinstance(error, NoResults):
            description = locale["ERROR_NO_RESULTS"]
        else:
            log.error(
                f"{inter}. {error}",
                extra={"locals": locals(), "ctx": vars(inter)},
                exc_info=error,
            )
            return None
        await inter.send(embed=disnake.Embed(title=title, description=description, color=Color.error), ephemeral=True)


def main() -> None:
    db_credentials = {k: v for k, v in DB_CREDENTIALS.items() if v is not None}
    test_guilds = [int(guild_id) for guild_id in GUILDS_ID.split(",")]

    db.bind(**db_credentials)
    db.generate_mapping(create_tables=True)

    # intents = disnake.Intents.default()
    # intents.message_content = True

    bot = PypocaBot(
        # command_prefix=commands.when_mentioned_or("/"),
        # intents=intents,
        reload=DEBUG,
        help_command=None,
        sync_commands_debug=DEBUG,
        test_guilds=test_guilds,
    )
    # bot.i18n.load("pypoca/locale")
    bot.load_extensions("pypoca/cogs")
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
