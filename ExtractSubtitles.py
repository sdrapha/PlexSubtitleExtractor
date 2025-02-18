import gzip
import os
import platform
import sqlite3

class SubtitleBlob:
    """
    Contains the details of a subtitle file stored in the Plex database
    """

    def __init__(self, stream_id, blob):
        self.stream_id = stream_id
        self.data = gzip.decompress(blob)

    def set_info(self, file, codec, language, forced):
        self.file = file
        self.codec = codec
        self.language = language
        self.forced = forced
    
    def get_name(self):
        filename = os.path.splitext(os.path.basename(self.file))[0]
        filename += f'.{self.language}'
        if self.forced == 1:
            filename += '.forced'
        return filename + f'.{self.codec}'

def process():
    blob_db, plex_db = find_database()
    save_dir = get_save_dir()

    blobs = get_subtitle_blobs(blob_db)
    get_subtitle_details(blobs, plex_db)

    write_subtitles(blobs, save_dir)
    print('Done!')


def get_subtitle_blobs(database):
    """
    Return the gzip'd subtitle blobs stored in the Plex blob database
    """

    blobs = {}
    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT linked_id, blob FROM blobs WHERE blob_type=3")
        for row in cur.fetchall():
            blobs[row[0]] = SubtitleBlob(row[0], row[1])
        cur.close()
    return blobs


def get_subtitle_details(blobs, database):
    """
    Take the given blobs and find the file they're associated with, updating the given blobs with that infomation.
    """

    with sqlite3.connect(database) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        for stream_id in blobs.keys():
            cur.execute(f"SELECT parts.file, stream.codec, stream.language, stream.forced FROM media_streams AS stream INNER JOIN media_parts AS parts ON parts.id=stream.media_part_id WHERE stream.id={stream_id}")
            row = cur.fetchall()
            if not row:
                print(f'Error grabbing associated file with stream id {stream_id}')
                continue
            row = row[0]
            blobs[stream_id].set_info(row[0], row[1], row[2], row[3])
        cur.close()


def write_subtitles(blobs, save_dir):
    """
    Write the given subtitles to the given save directory
    """

    for subtitle in blobs.values():
        filename = subtitle.get_name()
        print(f'Writing {filename}')
        with open(os.path.join(save_dir, filename), 'wb') as sub_file:
            try:
                sub_file.write(subtitle.data)
            except:
                print('ERROR: Could not write data. Data snippet:')
                print(subtitle.data[:100])


def find_database():
    """
    Attempt to automatically find the required Plex databases. If not found, ask the user to provide the full path to the 'Databases' folder
    """

    blob_db = 'com.plexapp.plugins.library.blobs.db'
    plex_db = 'com.plexapp.plugins.library.db'
    system = platform.system().lower()
    db_base = ''
    if system == 'windows' and 'LOCALAPPDATA' in os.environ:
        db_base = os.path.join(os.environ['LOCALAPPDATA'], 'Plex Media Server', 'Plug-in Support', 'Databases')
    elif system == 'darwin':
        db_base = os.path.join('~', 'Library', 'Application Support', 'Plex Media Server', 'Plug-in Support', 'Databases')
    elif system == 'linux' and 'PLEX_HOME' in os.environ:
        db_base = os.path.join(os.environ['PLEX_HOME'], 'Plex Media Server', 'Plug-in Support', 'Databases')

    # Surrounding quotes aren't necessary
    if len(db_base) > 0 and db_base[0] in ['"', "'"] and db_base[len(db_base) - 1] in ['"', "'"]:
        db_base = db_base[1:len(db_base) - 1]

    if len(db_base) > 0 and os.path.exists(db_base) and os.path.exists(os.path.join(db_base, blob_db)) and os.path.exists(os.path.join(db_base, plex_db)):
        blob_db = os.path.join(db_base, blob_db)
        plex_db = os.path.join(db_base, plex_db)
        return blob_db, plex_db

    db_base = input('Could not find database directory. Please enter the full path to the "Databases" folder: ')
    while not os.path.exists(db_base) or not os.path.isfile(os.path.join(db_base, blob_db)) or not os.path.isfile(os.path.join(db_base, plex_db)):
        db_base = input('That directory does not exist (or does not contain the Plex databases). Please enter the full path: ')
    
    return os.path.join(db_base, blob_db), os.path.join(db_base, plex_db)


def get_save_dir():
    """
    Ask the user where they want to save the subtitles
    """

    save_dir = input('Where do you want to save your extracted subtitles (full path)? ')
    while not os.path.isdir(save_dir):
        if get_yes_no('That path does not exist. Would you like to create it'):
            try:
                os.makedirs(save_dir)
                return save_dir
            except OSError:
                print('Sorry, something went wrong attempting to create the save directory.')
        save_dir = input('Where do you want to save your extracted subtitles (full path)? ')
    
    return save_dir


def get_yes_no(prompt):
    """
    Return True or False depending on whether the user enters 'Y' or 'N'
    """
    while True:
        response = input(f'{prompt} (y/n)? ')
        ch = response.lower()[0] if len(response) > 0 else 'x'
        if ch in ['y', 'n']:
            return ch == 'y'


process()