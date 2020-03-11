# movie-sheet bot
This project sets up a discord bot that uses a set of google sheet functions to perform very specific tasks within a specific google sheet.

## Setting up googlsheet api 
1. Visit [google's api and services page](console.developers.google.com)
2. Create a new project
3. Navigate to that project's page
4. Click "enable apis and services"
5. Find and add the google drive api
···You should be redirected to a google drive api page for your project
6. On the left navigation pane, select "Credientials"
7. Click "Create Credentials" and then "Help me choose". 
8. Find the text "If you want you can skip this step and create an API key, client ID or service account." and click on **service account**
9. Click "Create Service Account"
10. Follow the steps to make the account, and give it the editor project role
11. Create a JSON key for the new service account and save it.
12. Open the JSON and find the **client_email** value. Copy it
13. Create a copy of [the movienight sheet](https://docs.google.com/spreadsheets/d/1RhQdngV4PshYQAOBYf9lT7MCmPk9ir1yHw9RL7Wn8PM/edit?usp=sharing) in your own google drive
14. Click "Share"
15. Paste the client_email value into the People input 

## Setting up a discord bot
1. Create a discord server
2. follow [the official instructions](https://discordpy.readthedocs.io/en/latest/discord.html) to build a bot
···When you are creating the invite link, select the permissions: "send messages" and "read message history"
3. Visit the url you created and select the server you wish to invite the bot to
4. Find your bot token in the Bot tab in the discord developer portal. You'll need this later.

## Setting up movie-sheet files
Requires python3.6 or greater due to use of f-strings
1. git clone https://github.com/melonfacedoom/movie-sheet
2. cd movie-sheet
3. python -m venv venv
4-linux. source venv/bin/activate
4-windows. venv\Scripts\activate
5. pip install -r requirements.txt

## Tying in APIs
1. In movie_sheet.py, edit the credentials variable to point to your json file from step 11 in **setting up googlsheet api**
2. Add the json credentials file to your .gitignore
3. Get the bot token from step 4 in **Setting up a discord bot**
4. Create a file called "config.py" that just contains:
···`bot_token="[your discord bot token]"`
5. Ensure that the config.py file with your bot token is in your .gitignore