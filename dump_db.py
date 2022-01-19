import sqlite3 

con = sqlite3.connect('melonbot.db')
with open('dump.sql', 'w', encoding='utf-8') as f:
    for line in con.iterdump():
        f.write('%s\n' % line)