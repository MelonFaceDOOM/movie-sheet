from scraping.ebert import ebert_lookup
from scraping.rotten_tomatoes import random_tomato
import discord
from discord.ext import commands
import os
import random
import string
import datetime
from melon_scheduling import parse_time_range
from movienight_bot import movieNightBot
from scheduling_bot import schedulingBot
from config import bot_token

db_file = 'melonbot.db'
mnb = movieNightBot(db_file)
sb = schedulingBot(db_file)


def chunk(message, max_length=1900):
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
    async def register(self, ctx, *nick):
        """Register with a nickname."""
        nick = " ".join(nick)
        discord_id = ctx.message.author.id
        try:
            mnb.register(discord_id, nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"you have registered as {nick}")
    
    @commands.command()
    async def add(self, ctx, *movie):
        """Suggest a future movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        try:
            mnb.suggest_movie(movie, discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been suggested")
        
    @commands.command()
    async def remove(self, ctx, *movie):
        """Remove a suggested movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        try:
            mnb.remove_suggestion(movie, discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed")
            
    @commands.command()
    async def transfer(self, ctx, movie, nick):
        """Transfer choosership to a new person.
        Requires quotations around movie and nick if they contain spaces.
        """
        discord_id = ctx.message.author.id
        try:
            mnb.transfer_suggestion(movie, discord_id, nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} was transferred to {nick}")
        
    @commands.command()
    async def find(self, ctx, *search_string):
        """Find a user or movie."""
        search_string = " ".join(search_string)
        try:
            message = mnb.find_all(search_string)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def endorse(self, ctx, *movie):
        """Endorse a movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        try:
            mnb.endorse_suggestion(movie, discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You've endorsed {movie}.")
    
    @commands.command()
    async def unendorse(self, ctx, *movie):
        """Remove endorsement from a movie."""
        movie = " ".join(movie)
        discord_id = ctx.message.author.id
        try:
            mnb.unendorse_suggestion(movie, discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You've unendorsed {movie}.")
        
    @commands.command()
    async def rate(self, ctx, *movie_and_rating):
        """Rate a movie."""
        discord_id = ctx.message.author.id
        rating = movie_and_rating[-1]
        cutoff = str(rating).find("/10")
        if cutoff > -1:
            rating = str(rating)[:cutoff]
        movie = " ".join(movie_and_rating[:-1])
        try:
            mnb.rate_movie(movie, discord_id, rating)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You rated {movie} {rating}/10.")

    @commands.command()
    async def unrate(self, ctx, *movie):
        """Rate a movie."""
        discord_id = ctx.message.author.id
        movie = " ".join(movie)
        try:
            mnb.remove_rating(movie, discord_id)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have removed your rating from {movie}.")

    @commands.command()
    async def review(self, ctx, movie, review):
        """Review a movie. Use quotations around movie and review args."""
        discord_id = ctx.message.author.id
        try:
            mnb.review_movie(movie_title=movie, reviewer_discord_id=discord_id, review_text=review)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have reviewed {movie}.")

    @commands.command()
    async def find_review(self, ctx, movie, reviewer):
        """Finds reviews for a movie from a reviewer."""
        try:
            message = mnb.find_reviews(movie_title=movie, reviewer_name=reviewer)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def reviews_from(self, ctx, *reviewer):
        """Finds reviews for a movie. Returns one specific review if reviwer is supplied as well."""
        reviewer = " ".join(reviewer)
        try:
            message = mnb.find_reviews(reviewer_name=reviewer)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def reviews_for(self, ctx, *movie):
        """Finds reviews for a movie."""
        movie = " ".join(movie)
        try:
            message = mnb.find_reviews(movie_title=movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def tag(self, ctx, movie, tag):
        """Add a tag to a movie. Use quotations around movie and tag args."""
        try:
            mnb.tag_movie(movie_title=movie, tag_text=tag)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have tagged {movie} as {tag}.")

    @commands.command()
    async def untag(self, ctx, movie, tag):
        """Remove a tag from a movie. Use quotations around movie and tag args."""
        try:
            mnb.untag_movie(movie_title=movie, tag_text=tag)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You have untagged {tag} from {movie}.")

    @commands.command()
    async def tagged(self, ctx, *tags):
        """Find all movies with specified tags. If multiple tags, separate with commas."""
        tags = " ".join(tags)
        tags = tags.split(",")
        tags = [tag.strip() for tag in tags]
        try:
            message = mnb.find_movies_with_tags(tags)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def tags(self, ctx, *movie):
        """Return tags for a specific movie."""
        movie = " ".join(movie)
        try:
            message = mnb.find_movie_tags(movie_title=movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")


class IndividualAnalytics(commands.Cog):
    @commands.command()
    async def suggestions(self, ctx, *nick):
        """Return movies suggested by a chooser."""
        nick = " ".join(nick)
        if not nick:
            discord_id = ctx.message.author.id
        else:
            discord_id = mnb.name_to_discord_id(nick)
        try:
            messages = chunk(mnb.retrieve_suggestions(discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
            
    @commands.command()
    async def chooser(self, ctx, *nick):
        """Return ratings received by a chooser."""
        nick = " ".join(nick)
        if not nick:
            discord_id = ctx.message.author.id
        else:
            discord_id = mnb.name_to_discord_id(nick)
        try:
            messages = chunk(mnb.ratings_for_choosers_movies(discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
        
    @commands.command()
    async def ratings(self, ctx, *nick):
        """Return ratings from a reviewer."""
        nick = " ".join(nick)
        if not nick:
            discord_id = ctx.message.author.id
        else:
            discord_id = mnb.name_to_discord_id(nick)
        try:
            messages = chunk(mnb.ratings_from_reviewer(discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
    
    @commands.command()
    async def unrated(self, ctx, *nick):
        """Return unrated movies from a reviewer."""
        nick = " ".join(nick)
        if not nick:
            discord_id = ctx.message.author.id
        else:
            discord_id = mnb.name_to_discord_id(nick)
        try:
            messages = chunk(mnb.missing_ratings_for_reviewer(discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")


class GroupAnalytics(commands.Cog):
    @commands.command()
    async def top_endorsed(self, ctx, n=5):
        """Return most-endorsed movies."""
        try:
            messages = chunk(mnb.top_endorsed(n))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
    
    @commands.command()
    async def unendorsed(self, ctx, *nick):
        """Return unendorsed movies."""
        nick = " ".join(nick)
        discord_id = mnb.name_to_discord_id(nick)
        try:
            messages = chunk(mnb.unendorsed(discord_id))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")

    @commands.command()
    async def standings(self, ctx):
        """Return rankings of chooser scores."""
        message = mnb.standings()
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def top_rated(self, ctx, n=10):
        """Return the top-rated movies."""
        try:
            messages = chunk(mnb.top_ratings(n))
        except ValueError as e:
            return await ctx.send(e)
        for message in messages:
            await ctx.send("```"+message+"```")
        
        
class Research(commands.Cog):
    @commands.command()
    async def random(self, ctx):
        """Return a random suggested movie."""
        movie = mnb.pick_random_movie()
        return await ctx.send("```"+movie+"```")

    @commands.command()
    async def ebert(self, ctx, *movie):
        """Return a Rogert Ebert review for a movie."""
        movie = " ".join(movie)
        messages = chunk(ebert_lookup(movie))
        for message in messages:
            await ctx.send("```"+message+"```")
 
    @commands.command()
    async def fresh(self, ctx, *movie):
        """Return a random fresh RT review for a movie."""
        movie = " ".join(movie)
        messages = chunk(random_tomato(movie, fresh=1))
        for message in messages:
            await ctx.send("```"+message+"```")
        
    @commands.command()
    async def rotten(self, ctx, *movie):
        """Return a random rotten RT review for a movie."""
        movie = " ".join(movie)
        messages = chunk(random_tomato(movie, fresh=0))
        for message in messages:
            await ctx.send("```"+message+"```")


#TODO: find event
#TODO: remove all events
class Scheduling(commands.Cog):
    @commands.command()
    async def event(self, ctx, command, *args):
        """?event create/delete event_name
           ?event ready/unready/vote/unvote [event_name:] start_time [- end_time]"""

        # 0) check command and exit early if create/delete,
        #    as no parsing is necessary for those commands
        if command == "create":
            await self.create_event(ctx, args)
            return None
        elif command == "delete":
            await self.delete_event(ctx, args)
            return None
        elif command == "summary":
            await self.event_summary(ctx, args)
            return None
        elif command == "help":
            await self.event_help(ctx)
            return None
        elif command not in ['ready', 'unready', 'vote', 'unvote']:
            raise ValueError(f'Command {command} not recognized.')

        # 1) find title
        if args[0][-1] == ":":
            title = args[0][:-1]
            args = args[1:]
        else:
            title = sb.most_recent_event_title()
            if not title:
                raise ValueError("There are currently no events registered")
        
        # 2) find start/end times
        try:
            time_div = args.index("-")
        except ValueError:
            time_div = None
        if time_div:
            start_raw = " ".join(args[:time_div])
            end_raw = " ".join(args[time_div+1:])
            start, end = parse_time_range(start_raw, end_raw)
        else:
            # there is only 1 arg given for the time range.
            # it is either a vote_id associated with an existing time_range
            # OR, it is either something like "today", "saturday", "2020-09-09",
            # in which case the full day should be taken as the range,
            start_raw = " ".join(args)
            if start_raw.strip().isdigit():
                start, end = sb.find_time_range_by_vote_id(
                    event_title=title, vote_id=start_raw.strip())
            else:
                start, end = parse_time_range(start_raw)

        # 3) call command with parsed args
        if command == "ready":
            await self.event_ready(ctx, title, start, end)
        elif command == "unready":
            await self.event_unready(ctx, title, start, end)
        elif command == "vote":
            await self.event_vote(ctx, title, start, end)
        elif command == "unvote":
            await self.event_unvote(ctx, title, start, end)

    async def create_event(self, ctx, title):
        title = " ".join(title)
        if ":" in title:
            raise ValueError('title cannot contain ":"')
        try:
            sb.create_event(title)
            await ctx.send(f'The event "{title}" has been created.')
        except ValueError as e:
            await ctx.send(e)

    async def delete_event(self, ctx, title):
        title = " ".join(title)
        try:
            sb.remove_event(title)
            return await ctx.send(f'The event "{title}" has been deleted.')
        except ValueError as e:
            return await ctx.send(e)
    
    async def event_ready(self, ctx, event_title, start, end):
        try:
            ev = sb.build_event(event_title)
        except ValueError as e:
            return await ctx.send(e)        
        
        discord_id = ctx.message.author.id
        try:
            nick = sb.discord_id_to_name(discord_id)
        except ValueError as e:
            return await ctx.send(e) 
        participant = ev.add_participant(nick)
        participant.add_availability(start, end)
        sb.update_event(ev)
        start_str = datetime.datetime.strftime(start, "%Y-%m-%d %H:%M")
        end_str = datetime.datetime.strftime(end, "%Y-%m-%d %H:%M")
        return await ctx.send(f'added availability to {ev.name} from {start_str} to {end_str}')

    async def event_unready(self, ctx, event_title, start, end):
        try:
            ev = sb.build_event(event_title)
        except ValueError as e:
            return await ctx.send(e)

        discord_id = ctx.message.author.id
        try:
            nick = sb.discord_id_to_name(discord_id)
        except ValueError as e:
            return await ctx.send(e)
        participant = ev.find_participant(nick)
        if not participant:
            return await ctx.send('participant not found')
        participant.remove_availability(start, end)
        sb.update_event(ev)
        start_str = datetime.datetime.strftime(start, "%Y-%m-%d %H:%M")
        end_str = datetime.datetime.strftime(end, "%Y-%m-%d %H:%M")
        return await ctx.send(f'removed availability from {start_str} to {end_str}') 

    async def event_vote(self, ctx, event_title, start, end):
        try:
            ev = sb.build_event(event_title)
        except ValueError as e:
            return await ctx.send(e)

        discord_id = ctx.message.author.id
        try:
            nick = sb.discord_id_to_name(discord_id)
        except ValueError as e:
            return await ctx.send(e)
        participant = ev.add_participant(nick)
        participant.suggest_time(start, end)
        sb.update_event(ev)
        start_str = datetime.datetime.strftime(start, "%Y-%m-%d %H:%M")
        end_str = datetime.datetime.strftime(end, "%Y-%m-%d %H:%M")
        return await ctx.send(f'voted for {event_title} to occur between {start_str} and {end_str}') 

    async def event_unvote(self, ctx, event_title, start, end):
        try:
            ev = sb.build_event(event_title)
        except ValueError as e:
            return await ctx.send(e)

        discord_id = ctx.message.author.id
        try:
            nick = sb.discord_id_to_name(discord_id)
        except ValueError as e:
            return await ctx.send(e)
        participant = ev.find_participant(nick)
        if not participant:
            return await ctx.send('participant not found')    
        participant.unsuggest_time(start, end)
        sb.update_event(ev)
        start_str = datetime.datetime.strftime(start, "%Y-%m-%d %H:%M")
        end_str = datetime.datetime.strftime(end, "%Y-%m-%d %H:%M")
        return await ctx.send(f'you have removed your vote for {event_title} to occur between {start_str} and {end_str}')

    async def event_summary(self, ctx, title):
        title = " ".join(title)
        if not title:
            title = sb.most_recent_event_title()
            if not title:
                raise ValueError("There are currently no events registered")
        try:
            ev = sb.build_event(title)
        except ValueError as e:
            return await ctx.send(e)
        day_summaries = ev.summary()
        for day_summary in day_summaries:
            await ctx.send(f'```{day_summary}```')

    async def event_help(self, ctx):
        message = "```[] denotes optional\n" \
                  "?event create event_name\n" \
                  "?event delete event_name\n" \
                  "?event ready [event_name: ]start_time[ - end_time]\n" \
                  "?event unready [event_name: ]start_time[ - end_time]\n" \
                  "?event vote [event_name: ]start_time[ - end_time]\n" \
                  "?event unvote [event_name: ]start_time[ - end_time]```"
        await ctx.send(message)

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description='ur fav movienight companion.\n!register <nick> to get started!!!')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(Core(bot))
bot.add_cog(IndividualAnalytics(bot))
bot.add_cog(GroupAnalytics(bot))
bot.add_cog(Research(bot))
bot.add_cog(Scheduling(bot))
bot.run(bot_token)
