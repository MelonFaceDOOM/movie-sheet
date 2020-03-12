from config import bot_token
import discord
from discord.ext import commands
import os
import movie_sheet

def chunk(message, max_length=1900):
    chunks = []
    while message:
        chunks.append(message[:max_length])
        message = message[max_length:]
    return chunks
    
    
class MovieSheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def register(self, ctx, *nick):
        """Register your discord id with a nickname in the googlesheet."""
        nick = " ".join(nick)
        id = str(ctx.message.author.id)
        try:
            movie_sheet.register(id, nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"you have registered as {nick}")
    
    @commands.command()
    async def add(self, ctx, *movie):
        """Suggest a future movie."""
        movie = " ".join(movie)
        id = str(ctx.message.author.id)
        try:
            chooser = movie_sheet.get_nick(id)
        except ValueError as e:
            return await ctx.send(e)
        try:
            movie_sheet.add_future_movie(movie, chooser)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been suggested by {chooser}")
        
    @commands.command()
    async def remove(self, ctx, *movie):
        """Remove a suggested movie."""
        movie = " ".join(movie)
        try:
            movie_sheet.remove_future_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed")
            
    @commands.command()
    async def transfer(self, ctx, movie, nick):
        """Transfer choosership to a new person."""
        try:
            movie_sheet.transfer_movie(movie, nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} was transferred to {nick}")
        
    @commands.command()
    async def find(self, ctx, *movie):
        """Find movie that has been suggested or watched."""
        movie = " ".join(movie)
        try:
            message = movie_sheet.find_all_movies(movie)
        except ValueError:
            return await ctx.send(f'Could not find "{movie}".')
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def endorse(self, ctx, *movie):
        """Endorse a movie."""
        movie = " ".join(movie)
        id = str(ctx.message.author.id)
        try:
            nick = movie_sheet.get_nick(id)
        except ValueError as e:
            return await ctx.send(e)
        try:
            movie_sheet.endorse_movie(movie, nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You've endorsed {movie}.")
    
    @commands.command()
    async def unendorse(self, ctx, *movie):
        """Remove endorsement from a movie."""
        movie = " ".join(movie)
        id = str(ctx.message.author.id)
        try:
            nick = movie_sheet.get_nick(id)
        except ValueError as e:
            return await ctx.send(e)
        message = movie_sheet.unendorse_movie(movie, nick)
        return await ctx.send(message)
        
    @commands.command()
    async def rate(self, ctx, rating, *movie):
        """Rate a movie."""
        movie = " ".join(movie)
        id = str(ctx.message.author.id)
        try:
            nick = movie_sheet.get_nick(id)
        except ValueError as e:
            return await ctx.send(e)
        cutoff = str(rating).find("/10")
        if cutoff > -1:
            rating = str(rating)[:cutoff]
        rating = float(rating)
        try:
            movie_sheet.rate_movie(movie, nick, rating)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You rated {movie} {rating}/10")
        
    @commands.command()
    async def watch(self, ctx, *movie):
        """Move a movie from the suggestions sheet to the ratings sheet."""
        movie = " ".join(movie)
        try:
            movie_sheet.watch_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been moved to the ratings sheet")
        
    @commands.command()
    async def unwatch(self, ctx, *movie):
        """Remove a movie from the ratings sheet"""
        movie = " ".join(movie)
        try:
            movie_sheet.unwatch_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed from ratings sheet")
        
    @commands.command()
    async def suggestions(self, ctx, *nick):
        """Return all movies suggested by a chooser."""
        nick = " ".join(nick)
        try:
            message = movie_sheet.chooser_suggestions(nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def recent(self, ctx, n=10):
        """Return most recently-suggested future movies."""
        message = movie_sheet.recent_suggestions(n)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def top_endorsed(self, ctx, n=5):
        """Return most-endorsed movies."""
        message = movie_sheet.top_endorsed(n)
        return await ctx.send("```"+message+"```")
    
    @commands.command()
    async def unendorsed(self, ctx):
        """Return unendorsed movies."""
        message = movie_sheet.unendorsed()
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def reviewer(self, ctx, *nick):
        """Return ratings given by a reviewer."""
        nick = " ".join(nick)
        if not nick:
            id = str(ctx.message.author.id)
            try:
                nick = movie_sheet.get_nick(id)
            except ValueError as e:
                return await ctx.send(e)
        try:
            message = movie_sheet.average_reviewer_rating(nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def chooser(self, ctx, *nick):
        """Return ratings received by a chooser."""
        nick = " ".join(nick)
        if not nick:
            id = str(ctx.message.author.id)
            try:
                nick = movie_sheet.get_nick(id)
            except ValueError as e:
                return await ctx.send(e)
        try:
            rating_summary = movie_sheet.average_chooser_rating(nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+rating_summary+"```")
        
    @commands.command()
    async def ratings(self, ctx, *nick):
        """Return ratings from a reviewer."""
        nick = " ".join(nick)
        try:
            message = movie_sheet.ratings_from_reviewer(nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")
    
    @commands.command()
    async def unrated(self, ctx, *nick):
        nick = " ".join(nick)
        """Return unrated movies from a reviewer."""
        try:
            message = movie_sheet.missing_ratings_for_reviewer(nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def standings(self, ctx):
        """Return rankings of chooser average scores."""
        message = movie_sheet.standings()
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def top_rated(self, ctx, n=10):
        """Return the top-rated movies."""
        message = movie_sheet.top_ratings(n)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def random(self, ctx):
        """Return a random suggested movie."""
        movie = movie_sheet.pick_random_movie()
        return await ctx.send("```"+movie+"```")
        
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description='ur fav movienight companion')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(MovieSheet(bot))
bot.run(bot_token)