from scraping.ebert import ebert_lookup
from scraping.rotten_tomatoes import random_tomato
from scraping.gamespot import get_random_post
from discord.ext import commands
from discord import Intents
from make_melonbot_db import make_db
from movienight_bot import movieNightBot
from config import bot_token
from melon_discord import user_to_id, id_to_user

db_filename = 'melonbot.db'
make_db(db_filename)
mnb = movieNightBot(db_filename)


async def chunk(message, max_length=1900):
    chunks = []
    while message:
        chunk = ""
        newline_pos = None
        while (len(chunk) <= max_length) and message:
            character = message[0]
            message = message[1:]
            chunk += character
            
            if character == "\n":
                newline_pos = len(chunk)
        if newline_pos and message:
            extra = chunk[newline_pos:]
            message = extra + message
            chunk = chunk[:newline_pos-1]
            
        chunks.append(chunk)
    return chunks


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sheet(self, ctx):
        """Returns the link for the OG google sheet"""
        url = "https://docs.google.com/spreadsheets/d/1RhQdngV4PshYQAOBYf9lT7MCmPk9ir1yHw9RL7Wn8PM/edit#gid=1230671661"
        await ctx.send(url)
    
    @commands.command()
    async def add(self, ctx, *movie):
        """Suggest a future movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        guild_id = ctx.message.guild.id
        try:
            await mnb.suggest_movie(guild_id=guild_id, movie_title=movie,
                                    user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been suggested")
        
    @commands.command()
    async def remove(self, ctx, *movie):
        """Remove a suggested movie."""
        movie = " ".join(movie)
        guild_id = ctx.message.guild.id
        try:
            await mnb.remove_suggestion(guild_id=guild_id, movie_title=movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed")
            
    @commands.command()
    async def transfer(self, ctx, movie, name_or_mention):
        """Transfer choosership to a new person.
        Requires quotations around movie and nick if they contain spaces.
        """
        discord_id = await user_to_id(ctx, name_or_mention)
        if not discord_id:
            return await ctx.send(f'User {name_or_mention} not found')
        recipient_name = await id_to_user(ctx, discord_id)
        guild_id = ctx.message.guild.id
        try:
            await mnb.transfer_suggestion(guild_id=guild_id, movie_title=movie,
                                          recipient_user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} was transferred to {recipient_name}")
        
    @commands.command()
    async def find(self, ctx, *search_term):
        """Find a user or movie."""
        search_term = " ".join(search_term)
        guild_id = ctx.message.guild.id
        try:
            message = await mnb.find_all(ctx=ctx, guild_id=guild_id,
                                         search_term=search_term)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def endorse(self, ctx, *movie):
        """Endorse a movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        guild_id = ctx.message.guild.id
        try:
            await mnb.endorse_suggestion(guild_id=guild_id, movie_title=movie,
                                         endorser_user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You've endorsed {movie}.")
    
    @commands.command()
    async def unendorse(self, ctx, *movie):
        """Remove endorsement from a movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        guild_id = ctx.message.guild.id
        try:
            await mnb.unendorse_suggestion(guild_id=guild_id, movie_title=movie,
                                           endorser_user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You've unendorsed {movie}.")
        
    @commands.command()
    async def rate(self, ctx, *movie_and_rating):
        """Rate a movie."""
        discord_id = ctx.message.author.id
        guild_id = ctx.message.guild.id
        rating = movie_and_rating[-1]
        cutoff = str(rating).find("/10")
        if cutoff > -1:
            rating = str(rating)[:cutoff]
        movie = " ".join(movie_and_rating[:-1])
        try:
            await mnb.rate_movie(guild_id=guild_id, movie_title=movie,
                                 rater_user_id=discord_id, rating=rating)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You rated {movie} {rating}/10.")

    @commands.command()
    async def unrate(self, ctx, *movie):
        """Rate a movie."""
        discord_id = ctx.message.author.id
        guild_id = ctx.message.guild.id
        movie = " ".join(movie)
        try:
            await mnb.remove_rating(guild_id=guild_id, movie_title=movie,
                                    rater_user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have removed your rating from {movie}.")

    @commands.command()
    async def review(self, ctx, movie, review):
        """Review a movie. Use quotations around movie and review args."""
        discord_id = ctx.message.author.id
        guild_id = ctx.message.guild.id
        try:
            await mnb.review_movie(guild_id=guild_id, movie_title=movie,
                                   reviewer_user_id=discord_id, review_text=review)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have reviewed {movie}.")

    @commands.command()
    async def find_review(self, ctx, movie, *name_or_mention):
        """Finds reviews for a movie from a reviewer."""
        name_or_mention = " ".join(name_or_mention)
        guild_id = ctx.message.guild.id
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            message = await mnb.find_reviews(ctx=ctx, guild_id=guild_id, movie_title=movie,
                                             reviewer_user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def reviews_from(self, ctx, *name_or_mention):
        """Finds reviews from a reviewer."""
        name_or_mention = " ".join(name_or_mention)
        discord_id = await user_to_id(ctx, name_or_mention)
        if not discord_id:
            return await ctx.send(f'User {name_or_mention} not found')
        guild_id = ctx.message.guild.id
        try:
            message = await mnb.find_reviews(ctx=ctx, guild_id=guild_id,
                                             reviewer_user_id=discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def reviews_for(self, ctx, *movie):
        """Finds reviews for a movie."""
        guild_id = ctx.message.guild.id
        movie = " ".join(movie)
        try:
            message = await mnb.find_reviews(ctx=ctx, guild_id=guild_id,
                                             movie_title=movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def tag(self, ctx, movie, tag):
        """Add a tag to a movie. Use quotations around movie and tag args."""
        guild_id = ctx.message.guild.id
        try:
            await mnb.tag_movie(guild_id=guild_id, movie_title=movie, tag_text=tag)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have tagged {movie} as {tag}.")

    @commands.command()
    async def untag(self, ctx, movie, tag):
        """Remove a tag from a movie. Use quotations around movie and tag args."""
        guild_id = ctx.message.guild.id
        try:
            await mnb.untag_movie(guild_id=guild_id, movie_title=movie, tag_text=tag)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have untagged {tag} from {movie}.")

    @commands.command()
    async def tagged(self, ctx, *tags):
        """Find all movies with specified tags. If multiple tags, separate with commas."""
        guild_id = ctx.message.guild.id
        tags = " ".join(tags)
        tags = tags.split(",")
        tags = [tag.strip() for tag in tags]
        try:
            message = await mnb.find_movies_with_tags(guild_id=guild_id, tags=tags)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def tags(self, ctx, *movie):
        """Return tags for a specific movie."""
        guild_id = ctx.message.guild.id
        movie = " ".join(movie)
        try:
            message = await mnb.find_movie_tags(guild_id=guild_id, movie_title=movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")


class IndividualAnalytics(commands.Cog):
    @commands.command()
    async def suggestions(self, ctx, *name_or_mention):
        """Return movies suggested by a chooser."""
        name_or_mention = " ".join(name_or_mention)
        guild_id = ctx.message.guild.id
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            messages = await chunk(await mnb.retrieve_suggestions(ctx=ctx, guild_id=guild_id,
                                                                  chooser_user_id=discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")

    @commands.command()
    async def endorsements(self, ctx, *name_or_mention):
        """Return movies endorsed by a user."""
        name_or_mention = " ".join(name_or_mention)
        guild_id = ctx.message.guild.id
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            messages = await chunk(await mnb.retrieve_endorsements(ctx=ctx, guild_id=guild_id,
                                                                  endorser_user_id=discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
            
    @commands.command()
    async def chooser(self, ctx, *name_or_mention):
        """Return ratings received by a chooser."""
        guild_id = ctx.message.guild.id
        name_or_mention = " ".join(name_or_mention)
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            messages = await chunk(await mnb.ratings_for_choosers_movies(ctx=ctx, guild_id=guild_id,
                                                                         chooser_user_id=discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
        
    @commands.command()
    async def ratings(self, ctx, *name_or_mention):
        """Return ratings from a reviewer."""
        guild_id = ctx.message.guild.id
        name_or_mention = " ".join(name_or_mention)
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            messages = await chunk(await mnb.ratings_from_reviewer(ctx=ctx, guild_id=guild_id,
                                                                   rater_user_id=discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
    
    @commands.command()
    async def unrated(self, ctx, *name_or_mention):
        """Return unrated movies from a reviewer."""
        guild_id = ctx.message.guild.id
        name_or_mention = " ".join(name_or_mention)
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            messages = await chunk(await mnb.missing_ratings_for_reviewer(ctx=ctx, guild_id=guild_id,
                                                                          rater_user_id=discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")


class GroupAnalytics(commands.Cog):
    @commands.command()
    async def top_endorsed(self, ctx, n=5):
        """Return most-endorsed movies."""
        guild_id = ctx.message.guild.id
        try:
            messages = await chunk(await mnb.top_endorsed(ctx=ctx, guild_id=guild_id, n=n))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
    
    @commands.command()
    async def unendorsed(self, ctx, *name_or_mention):
        """Return unendorsed movies."""
        name_or_mention = " ".join(name_or_mention)
        guild_id = ctx.message.guild.id
        if not name_or_mention:
            discord_id = ctx.message.author.id
        else:
            discord_id = await user_to_id(ctx, name_or_mention)
            if not discord_id:
                return await ctx.send(f'User {name_or_mention} not found')
        try:
            messages = await chunk(await mnb.unendorsed(ctx=ctx, guild_id=guild_id,
                                                        chooser_user_id=discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")

    @commands.command()
    async def recent(self, ctx, n=10):
        """Return recently watched movies."""
        guild_id = ctx.message.guild.id
        try:
            messages = await chunk(await mnb.recently_watched_movies(ctx=ctx, guild_id=guild_id, n=n))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```" + message + "```")

    @commands.command()
    async def standings(self, ctx):
        """Return rankings of chooser scores."""
        guild_id = ctx.message.guild.id
        try:
            message = await mnb.standings(ctx=ctx, guild_id=guild_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def top(self, ctx, n=10):
        """Return the top-rated movies."""
        guild_id = ctx.message.guild.id
        try:
            messages = await chunk(await mnb.top_ratings(ctx=ctx, guild_id=guild_id, top=True, n=n))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")

    @commands.command()
    async def bottom(self, ctx, n=10):
        """Return the bottom-rated movies."""
        guild_id = ctx.message.guild.id
        try:
            messages = await chunk(await mnb.top_ratings(ctx=ctx, guild_id=guild_id, top=False, n=n))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```" + message + "```")


class Research(commands.Cog):
    @commands.command()
    async def random(self, ctx):
        """Return a random suggested movie."""
        guild_id = ctx.message.guild.id
        movie = await mnb.pick_random_movie(guild_id=guild_id)
        return await ctx.send("```"+movie+"```")

    @commands.command()
    async def ebert(self, ctx, *movie):
        """Return a Rogert Ebert review for a movie."""
        movie = " ".join(movie)
        messages = await chunk(ebert_lookup(movie))
        for message in messages:
            await ctx.send("```"+message+"```")
 
    @commands.command()
    async def fresh(self, ctx, *movie):
        """Return a random fresh RT review for a movie."""
        movie = " ".join(movie)
        messages = await chunk(random_tomato(movie, fresh=1))
        for message in messages:
            await ctx.send("```"+message+"```")
        
    @commands.command()
    async def rotten(self, ctx, *movie):
        """Return a random rotten RT review for a movie."""
        movie = " ".join(movie)
        messages = await chunk(random_tomato(movie, fresh=0))
        for message in messages:
            return await ctx.send("```"+message+"```")
            
    @commands.command()
    async def gamespot(self, ctx, *directory):
        """Return a random rotten GS post."""
        votes_required_to_self_destruct = 5
        guild_id = ctx.message.guild.id
        self_destructed = await mnb.self_destructed(guild_id, votes_required=votes_required_to_self_destruct)
        if self_destructed:
            return await ctx.send("```This feature is gone forever.```"
                                  )
        directory = " ".join(directory)
        # special self destruct command
        if directory == "self destruct":
            discord_id = ctx.message.author.id
            message = await mnb.vote_gamespot_self_destruct(ctx=ctx, guild_id=guild_id, user_id=discord_id,
                                                            votes_required=votes_required_to_self_destruct)
            await ctx.send("```" + message + "```")
        else:
            try:
                author, time, post_link, post = get_random_post(directory=directory)
            except ValueError as e:
                return await ctx.send(e)
            message = author + " - " + time + "\n" + post + "\n\n" + "read more:\n" + post_link
            messages = await chunk(message)
            for message in messages:
                await ctx.send("```"+message+"```")

    @commands.command()
    async def bullshit(self, ctx):
        if ctx.message.author.id != 117340965760532487:
            return await ctx.send("only jacob can call bullshit")
        else:
            await mnb.bullshit()
            return await ctx.send("congratulations")


intents = Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("?"),
                   case_insensitive=True,
                   intents=intents,
                   description='ur fav movienight companion.\n!register <nick> to get started!!!')


@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(Core(bot))
bot.add_cog(IndividualAnalytics(bot))
bot.add_cog(GroupAnalytics(bot))
bot.add_cog(Research(bot))
bot.run(bot_token)
