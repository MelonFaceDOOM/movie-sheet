from config import bot_token
import discord
from discord.ext import commands
import os
import movie_sheet

def chunk(message, max_length=1900)
    chunks = []
    while message:
        chunks.append(message[:max_length])
        message = message[max_length:]
    return chunks
    
    
class MovieSheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def register(self, ctx, nick):
        """Register your discord id with a nickname in the googlesheet."""
        id = str(ctx.message.author.id)
        try:
            movie_sheet.register(id, nick)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"you have registered as {nick}")
    
    @commands.command()
    async def add(self, ctx, movie, chooser=None):
        """Suggest a future movie."""
        if chooser is None:
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
    async def remove(self, ctx, movie):
        """Remove a suggested movie."""
        try:
            movie_sheet.remove_future_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed")
    
    @commands.command()
    async def watch(self, ctx, movie):
        """Move a movie from the suggestions sheet to the ratings sheet."""
        try:
            movie_sheet.watch_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been moved to the ratings sheet")
        
    @commands.command()
    async def unwatch(self, ctx, movie):
        """Remove a movie from the ratings sheet"""
        try:
            movie_sheet.unwatch_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed from ratings sheet")
        
    @commands.command()
    async def rate(self, ctx, movie, rating):
        """Rate a movie."""
        id = str(ctx.message.author.id)
        try:
            nick = movie_sheet.get_nick(id)
        except ValueError as e:
            return await ctx.send(e)
        rating = float(rating)
        try:
            movie_sheet.rate_movie(movie, nick, rating)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You rated {movie} {rating}/10")
        
    @commands.command()
    async def find(self, ctx, movie):
        """Find movie and return either endorsers or ratings."""
        try:
            message = movie_sheet.find_future_movie(movie)
        except ValueError:
            try:
                message = movie_sheet.average_movie_rating(movie)
            except ValueError:
                return await ctx.send(f"{movie} was not found")
        return await ctx.send("```"+message+"```")

    @commands.command()
    async def rr(self, ctx, reviewer=None):
        """Return ratings given by a reviewer."""
        if reviewer is None:
            id = str(ctx.message.author.id)
            try:
                reviewer = movie_sheet.get_nick(id)
            except ValueError as e:
                return await ctx.send(e)
        try:
            message = movie_sheet.average_reviewer_rating(reviewer)
        except ValueError as e:
            return await ctx.send(e)
        
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def cr(self, ctx, chooser=None):
        """Return ratings received by a chooser"""
        if chooser is None:
            id = str(ctx.message.author.id)
            try:
                chooser = movie_sheet.get_nick(id)
            except ValueError as e:
                return await ctx.send(e)
        try:
            rating_summary = movie_sheet.average_chooser_rating(chooser)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+rating_summary+"```")

    @commands.command()
    async def endorse(self, ctx, movie):
        """Endorse a movie."""
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
    async def unendorse(self, ctx, movie):
        """Remove endorsement from a movie."""
        id = str(ctx.message.author.id)
        try:
            nick = movie_sheet.get_nick(id)
        except ValueError as e:
            return await ctx.send(e)
        message = movie_sheet.unendorse_movie(movie, nick)
        return await ctx.send(message)
        
    @commands.command()
    async def transfer(self, ctx, movie, new_chooser):
        """Transfer choosership to a new person."""
        try:
            movie_sheet.transfer_movie(movie, new_chooser)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} was transferred to {new_chooser}")
        
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
    async def recent(self, ctx, n=10):
        """Return most recently-suggested future movies."""
        message = movie_sheet.recent_suggestions(n)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def standings(self, ctx):
        """Return rankings of chooser average scores."""
        message = movie_sheet.standings()
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def top_ratings(self, ctx, n=10):
        """Return the top-rated movies."""
        message = movie_sheet.top_ratings(n)
        return await ctx.send("```"+message+"```")
        
    @commands.command()
    async def suggestions(self, ctx, chooser):
        """Return all movies suggested by a chooser."""
        message = movie_sheet.chooser_suggestions(chooser)
        return await ctx.send("```"+message+"```")
        
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description='ur fav movienight companion')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(MovieSheet(bot))
bot.run(bot_token)