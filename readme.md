# movie-sheet bot
This project sets up a discord bot that facilitates keep track of user's movie-night suggestions, and their ratings/reviews for movies that have been watched as a group.

## Setting up a discord bot
1. Create a discord server
2. follow [the official instructions](https://discordpy.readthedocs.io/en/latest/discord.html) to build a bot
···When you are creating the invite link, select the permissions: "send messages" and "read message history"
3. Visit the url you created and select the server you wish to invite the bot to
4. Find your bot token in the Bot tab in the discord developer portal. You'll need this later.
5. Create a file called "config.py" that just contains:
···`bot_token="[your discord bot token]"`
6. Ensure that the config.py file with your bot token is in your .gitignore

## Setting up movie-sheet files
Requires python3.6 or greater due to use of f-strings
1. git clone https://github.com/melonfacedoom/movie-sheet
2. cd movie-sheet
3. python -m venv venv
4-linux. source venv/bin/activate
4-windows. venv\Scripts\activate
5. pip install -r requirements.txt