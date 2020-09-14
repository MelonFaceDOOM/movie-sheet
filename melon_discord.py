import re
from matching import find_closest_match


async def get_guild_user_info(ctx):
    members = ctx.message.guild.members
    return [[member.id, member.name] for member in members]


async def id_from_mention(text):
    pattern = "<@!([0-9]+)>"
    mention = re.search(pattern, text)
    if mention:
        return int(mention[1])
    else:
        return None


async def user_to_id(ctx, name_or_mention):
    """finds discord id when @username is provided, or by partial lookup. Returns None if no good match."""
    guild_user_info = await get_guild_user_info(ctx)
    discord_id = await id_from_mention(name_or_mention)
    if discord_id:
        guild_ids = [id_and_name[0] for id_and_name in guild_user_info]
        if discord_id not in guild_ids:
            return None
    else:
        names = [id_and_name[1] for id_and_name in guild_user_info]
        matched_name = find_closest_match(term=name_or_mention, bank=names, threshold=50)
        if matched_name:
            for id_and_name in guild_user_info:
                if id_and_name[1] == matched_name:
                    discord_id = id_and_name[0]
    return discord_id


async def id_to_user(ctx, id):
    """finds a user's username given their discord id"""
    guild_user_info = await get_guild_user_info(ctx)
    for id_and_name in guild_user_info:
        if id_and_name[0] == id:
            return id_and_name[1]
    return None
