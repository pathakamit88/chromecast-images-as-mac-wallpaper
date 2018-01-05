"""
Script to update mac wallpaper automatically by fetching chromecast wallpapers.
"""
import json
import os
import urllib2
import sqlite3
import sys
import commands
from bs4 import BeautifulSoup

__author__ = 'amit'

CHROMECAST_WEB_URL = 'https://clients3.google.com/cast/chromecast/home'

conn = sqlite3.connect('ccast.sqlite3')


def parse_webpage():
  webpage_content = urllib2.urlopen(CHROMECAST_WEB_URL).read()
  parsed_data = BeautifulSoup(webpage_content)
  script_ele = parsed_data.findAll('script')[-1]
  text = script_ele.text
  start_index = text.find("JSON.parse") + len("JSON.parse('")
  end_index = text.find("')). constant('isTextPromoEnabled', true)")
  data = text[start_index: end_index]
  try:
    json_data = json.loads(data.encode('utf-8').decode('string_escape'))
  except UnicodeEncodeError:
    sys.exit(0)

  urls_list = [x[0] for x in json_data[0]]
  return urls_list


def dump_urls_to_db():
  conn.execute("DELETE FROM master")
  conn.commit()
  conn.execute("VACUUM")
  conn.commit()

  urls_list = parse_webpage()
  for url in urls_list:
    conn.execute("INSERT INTO master (image_url, selected) VALUES (?, ?)", (url, 0))
  conn.commit()

  cursor = conn.execute("select id from master order by id asc limit 1")
  result = cursor.fetchone()
  return result[0]


def write_image_to_disk(db_id, image_url):
  image_url = image_url.replace('w1280', 'w1920').replace('h720', 'h1200')

  path = os.path.realpath(os.path.dirname(__file__))
  req = urllib2.Request(image_url)
  response = urllib2.urlopen(req)
  file_buffer = response.read()
  filepath = os.path.join(path, 'wallpaper_%s.jpg' % db_id)
  with open(filepath, 'wb') as temp_file:
    temp_file.write(file_buffer)

  return filepath


def set_mac_wallpaper(filepath):
  script = """osascript -e 'set desktopImage to POSIX file "%s"
                  tell application "Finder"
                  set desktop picture to desktopImage
              end tell'"""
  script = script % filepath
  commands.getoutput(script)


def delete_old_wallpaper(db_id):
  path = os.path.realpath(os.path.dirname(__file__))
  filepath = os.path.join(path, 'wallpaper_%s.jpg' % db_id)
  try:
    os.remove(filepath)
  except OSError:
    pass


def main():
  cursor = conn.execute("SELECT id FROM master WHERE selected=?", (1,))
  result = cursor.fetchone()
  if not result:
    result = (0,)

  previous_id = result[0]

  # Check if next record exists
  next_id = result[0] + 1
  cursor = conn.execute("SELECT * FROM master WHERE id=?", (next_id,))
  result = cursor.fetchone()
  if not result:
    next_id = dump_urls_to_db()
    cursor = conn.execute("SELECT * FROM master WHERE id=?", (next_id,))
    result = cursor.fetchone()

  image_path = write_image_to_disk(result[0], result[1])
  set_mac_wallpaper(image_path)

  conn.execute("update master set selected=0")
  conn.commit()
  conn.execute("update master set selected=1 where id=?", (next_id,))
  conn.commit()

  delete_old_wallpaper(previous_id)

if __name__ == '__main__':
  main()
