import re
from sys import exit
def main():
  with open('dump.sql', 'r', encoding='utf-8') as file:
    # read a list of lines into data
    original_data = file.readlines()
  new_data=[]
  for line in original_data:
    process = False
    for nope in ('BEGIN TRANSACTION','COMMIT',
                 'sqlite_sequence','CREATE UNIQUE INDEX'):
      if nope in line: break
    else:
      process = True
    if not process: continue
    m = re.search('CREATE TABLE ([a-z_]*)(.*)', line)
    if m:
      name, sub = m.groups()
      line = '''DROP TABLE IF EXISTS %(name)s;
CREATE TABLE IF NOT EXISTS %(name)s%(sub)s
'''
      line = line % dict(name=name, sub=sub)
    else:
      m = re.search('INSERT INTO "([a-z_]*)"(.*)', line)
      if m:
        line = 'INSERT INTO %s%s\n' % m.groups()
        line = line.replace('"', r'\"')
        line = line.replace('"', "'")
    line = re.sub(r"([^'])'t'(.)", r"\1THIS_IS_TRUE\2", line)
    line = line.replace('THIS_IS_TRUE', '1')
    line = re.sub(r"([^'])'f'(.)", r"\1THIS_IS_FALSE\2", line)
    line = line.replace('THIS_IS_FALSE', '0')
    line = line.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
    new_data.append(line)
  with open('dump.sql', 'w', encoding='utf-8') as file:
    file.writelines(new_data)

main()