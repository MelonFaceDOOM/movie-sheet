from config import bot_token
import discord
from discord.ext import commands
import os
import movie_sheet


class MovieSheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        movie_sheet.authorize()
    
    def get_nick(self)
        user_id = ctx.message.author.id
        try:
            nick = movie_sheet.get_nick(user_id)
        except ValueError as e:
            return await ctx.send(e)
        return nick
    
    @commands.command()
    def add(self, ctx, movie, chooser=None):    
        if chooser is None:
            chooser = self.get_nick()
        try:
            movie_sheet.add_future_movie(movie, chooser):
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been suggested by {chooser}")
        
    @commands.command()
    def remove(self, ctx, movie):
        try:
            movie_sheet.remove_future_movie(movie):
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed")
    
    @commands.command()
    def watch(self, ctx, movie):
        movie_sheet.watch_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been moved to the ratings sheet")
        
    @commands.command()
    def unwatch(self, ctx, movie):
        movie_sheet.unwatch_movie(movie)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"{movie} has been removed from ratings sheet")
        
    @commands.command()
    def rate(self, ctx, movie, rating):
        nick = self.get_nick()
        try:
            movie_sheet.rate_movie(movie, reviewer, rating)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send(f"You rated {movie} {rating}/10")
        
    @commands.command()
    def find(self, ctx, movie):
        try:
            message = movie_sheet.find_future_movie(movie):
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+message+"```")
    
    @commands.command()
    def mr(self, ctx, movie):
        try:
            rating_summary = movie_sheetaverage_movie_rating(movie)
        except ValueError as e:
            return await ctx.send(e)
        
        return await ctx.send("```"+rating_summary+"```")

    @commands.command()
    def rr(self, ctx, reviewer):
        try:
            rating_summary = movie_sheetaverage_reviewer_rating(reviewer)
        except ValueError as e:
            return await ctx.send(e)
        
        return await ctx.send("```"+rating_summary+"```")
        
    @commands.command()
    def cr(self, ctx, chooser):
        try:
            rating_summary = movie_sheetaverage_chooser_rating(chooser)
        except ValueError as e:
            return await ctx.send(e)
        return await ctx.send("```"+rating_summary+"```")

    @commands.command()
    def endorse(self, ctx, movie):
        nick = self.get_nick()
        movie_sheet.endorse_movie(movie, nick)
        return await ctx.send(f"You've endorsed {movie}.")
    
    @commands.command()
    def unendorse(self, ctx, movie):
        nick = self.get_nick()
        message = movie_sheet.unendorse_movie(movie, nick)
        return await ctx.send(message)
        
    @commands.command()
    def top_endorsed(self, ctx, n=5):
        message = movie_sheet.top_endorsed(n)
        return await ctx.send(message)
    
    @commands.command()
    def unendorsed(self, ctx):
        message = movie_sheet.unendorsed()
        return await ctx.send(message)
        
    @commands.command()
    def recent(self, ctx, n=10):
        message = movie_sheet.recent_suggestions(n)
        return await ctx.send("```"+message+"```")
        
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), description='ur fav movienight companion')

@bot.event
async def on_ready():
    print('Logged in as {0} ({0.id})'.format(bot.user))
    print('------')

bot.add_cog(MovieSheet(bot))
bot.run(bot_token)