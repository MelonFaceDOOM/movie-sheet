import random
import sqlite3
import datetime
from melon_scheduling import Event, Participant, SuggestedTime


class schedulingBot:
    """Takes care of sql transactions involved in saving/updating Events from melon_scheduling in a database."""
    def __init__(self, db_filename=None):
        if not db_filename:
            db_filename = 'scheduling_bot.db'
        self.conn = sqlite3.connect(db_filename)
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                         (discord_id INTEGER PRIMARY KEY NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                          date DATETIME DEFAULT current_timestamp)''')
        c.execute('''CREATE TABLE IF NOT EXISTS events
                          (id INTEGER PRIMARY KEY NOT NULL UNIQUE, title TEXT NOT NULL UNIQUE COLLATE NOCASE,
                           date DATETIME DEFAULT current_timestamp)''')
        c.execute('''CREATE TABLE IF NOT EXISTS participant_availability
                          (id INTEGER PRIMARY KEY NOT NULL UNIQUE, event_id INTEGER NOT NULL,
                           participant_discord_id INTEGER NOT NULL, date DATETIME DEFAULT current_timestamp,
                           availability_type TEXT NOT NULL, start DATETIME NOT NULL, end DATETIME NOT NULL)''')
        self.conn.commit()
        
    def build_event(self, event_title):
        c = self.conn.cursor()
        c.execute('''SELECT id FROM events WHERE title = ?''', (event_title,))
        event_id = c.fetchone()
        if not event_id:
            raise ValueError(f'an event with title "{event_title}" was not found')            
        event_id = event_id[0]
        c.execute('''SELECT id, participant_discord_id, availability_type, start, end FROM
                     participant_availability WHERE event_id = ?''', (event_id,))
        participant_availability = c.fetchall()
        
        ev = Event(event_title)
        for availability_id, participant_discord_id, availability_type, start, end in participant_availability:
            c.execute('''SELECT name FROM users WHERE discord_id = ?''', (participant_discord_id,))
            participant_name = c.fetchone()[0]
            participant = ev.add_participant(participant_name)
            start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M")
            end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M")
            if availability_type == "ready":
                participant.add_availability(start, end)
            elif availability_type == "vote":
                participant.suggest_time(start, end)
        return ev
        
    def save_event(self, event):
        c = self.conn.cursor()
        c.execute('''SELECT id FROM events where title = ?''', (event.name,))
        event_id = c.fetchone()
        if event_id:
            event_id = event_id[0]
        else:
            c.execute('''INSERT INTO events (title) values (?)''', (event.name,))
            c.execute('''SELECT id FROM events where title = ?''', (event.name,))
            event_id = c.fetchone()[0]
        self.conn.commit()
        
        for participant in event.participants:
            c.execute('''SELECT discord_id FROM users WHERE name = ?''', (participant.name,))
            participant_discord_id = c.fetchone()
            if not participant_discord_id:
                raise ValueError(f'was not able to find registered user with name {participant.name}')
            participant_discord_id = participant_discord_id[0]
            
            for time_pair in participant.times_available:
                start = datetime.datetime.strftime(time_pair[0], "%Y-%m-%d %H:%M")
                end = datetime.datetime.strftime(time_pair[1], "%Y-%m-%d %H:%M")
                c.execute('''INSERT INTO participant_availability (event_id, participant_discord_id, availability_type, start, end) values (?,?,?,?,?)''', (event_id, participant_discord_id, 'ready',
                start, end))

        for suggested_time in event.suggested_times:
            start = datetime.datetime.strftime(suggested_time.start_time, "%Y-%m-%d %H:%M")
            end = datetime.datetime.strftime(suggested_time.end_time, "%Y-%m-%d %H:%M")
            for voter in suggested_time.voters:
                c.execute('''INSERT INTO participant_availability (event_id, participant_discord_id, availability_type, start, end) values (?,?,?,?,?)''', (event_id, participant_discord_id, 'vote',
                start, end))

    def create_event(self, event_title):
        c = self.conn.cursor()
        c.execute('''SELECT id FROM events WHERE title = ?''', (event_title,))
        event_id = c.fetchone()
        if event_id:
            raise ValueError(f'An event called {event_title} already exists.')
        event = Event(name=event_title)
        self.save_event(event)
        return None
    
    def remove_event(self, event_title):
        c = self.conn.cursor()
        c.execute('''SELECT id FROM events WHERE title = ?''', (event_title, ))
        event_id = c.fetchone()
        if not event_id:
            raise ValueError('cannot remove event because this event could not be found.')
        event_id = event_id[0]
        c.execute('''DELETE FROM events WHERE id = ?''', (event_id,))
        c.execute('''DELETE FROM participant_availability WHERE event_id = ?''',(event_id,))
        self.conn.commit()
        return None
        
    def update_event(self, event):
        c = self.conn.cursor()
        if type(event) != Event:
            raise ValueError(f'ev must be an Event object')
        c.execute('''SELECT * FROM events WHERE title = ?''', (event.name,))
        event_title = c.fetchone()
        if not event_title:
            raise ValueError('cannot update event because this event could not be found')
        backup = self.build_event(event.name)
        self.remove_event(event.name)
        try:
            self.save_event(event)
        except:
            self.save_event(backup)

    def find_time_range_by_vote_id(self, event_title, vote_id):
        c = self.conn.cursor()
        c.execute('''SELECT id FROM events WHERE title = ?''', (event_title,))
        event_id = c.fetchone()
        if not event_id:
            raise ValueError(f'cannot find event with title {event_title}.')
        c.execute('''SELECT start, end FROM participant_availability
                     event_id = ? AND WHERE id = ?''', (vote_id, event_id))
        row = c.fetchone()
        if row:
            start, end = row[0]
        else:
            raise ValueError(f'cannot find vote_id {vote_id} in event {event_title}')

        return start, end

    def most_recent_event_title(self):
        c = self.conn.cursor()
        c.execute('''SELECT title FROM events WHERE date =(
                     SELECT MAX(date) FROM events)''')
        title = c.fetchone()
        if not title:
            return None
        return title[0]

    def name_to_discord_id(self, nick):
        c = self.conn.cursor()
        c.execute('''SELECT discord_id FROM users WHERE name = ?''', (nick,))
        discord_id = c.fetchone()
        if discord_id:
            return discord_id[0]
        else:
            return None

    def discord_id_to_name(self, discord_id):
        c = self.conn.cursor()
        c.execute('''SELECT name FROM users WHERE discord_id = ?''', (discord_id,))
        discord_id = c.fetchone()
        if discord_id:
            return discord_id[0]
        else:
            return None

    def register(self, discord_id, nick):
        c = self.conn.cursor()
        # TODO: What if someone wants to change their name?
        if len(nick) < 2:
            raise ValueError('nick must be at least 2 character')

        try:
            c.execute('''INSERT INTO users (discord_id, name) values (?,?)''', (discord_id, nick))
        except sqlite3.IntegrityError:
            raise ValueError('discord id and user name must be unique')
        self.conn.commit()