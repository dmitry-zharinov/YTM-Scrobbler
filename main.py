import logging
from ytmusicapi import YTMusic
import os
import pylast
import datetime
import time
import json
from strsimpy.jaro_winkler import JaroWinkler


def get_ytm_history() -> list:
    """
    Returns the history of the user's YouTube Music account.

    Returns:
        list: A list of dictionaries representing the user YouTube Music history.
    """
    ytmusic = YTMusic('headers_auth.json')
    return ytmusic.get_history()


def get_last_song_from_history(history: list) -> dict:
    """
    Returns a dictionary representing the last song played on YTM by the user.

    Args:
        history (list): A list of dictionaries representing the user's YouTube Music history.

    Returns:
        dict: A dictionary representing the last song played by the user.
    """
    song = {
        'title': history[0]['title'],
        'artist': history[0]['artists'][0]['name'],
        'liked': history[0]['likeStatus'] == 'LIKE'
    }
    try:
        song['album'] = history[0]['album']['name']
    except TypeError:
        logging.error('Album is not set\\n')
    logging.info(f'YTM: Last song was {song["title"]} by {song["artist"]}')
    return song


def get_last_fm_network() -> pylast.LastFMNetwork:
    """
    Returns a LastFMNetwork object representing the user's Last.fm network.

    Returns:
        pylast.LastFMNetwork: A LastFMNetwork object representing the user's Last.fm network.
    """
    with open('logindata.json', 'r') as f:
        lastFmCreds = json.loads(f.read())
        f.close()
    network = pylast.LastFMNetwork(
        api_key=lastFmCreds['apikey'],
        api_secret=lastFmCreds['apisecret'],
        username=lastFmCreds['username'],
        password_hash=pylast.md5(lastFmCreds['password']))
    return network


def get_last_fm_last_scrobble(network: pylast.LastFMNetwork) -> list:
    """
    Returns a list representing the user's last scrobbled song from Last.fm.

    Args:
        network (pylast.LastFMNetwork): A LastFMNetwork object representing the user's Last.fm network.

    Returns:
        list: A list representing the user's last scrobbled song from Last.fm.
    """
    with open('logindata.json', 'r') as f:
        lastFmCreds = json.loads(f.read())
        f.close()
    return network.get_user(lastFmCreds['username']).get_recent_tracks(limit=1)


def get_last_song() -> tuple:
    """
    Returns a tuple representing the last song scrobbled by script.

    Returns:
        tuple: A tuple representing the last song scrobbled by the user.
    """
    with open('last_song.json', 'r') as f:
        last_song = json.loads(f.read())
        f.close()
    logging.info(f'JSON: Last song was {last_song[0]} by {last_song[1]}\\n')
    return last_song


def scrobble_song(song: dict) -> None:
    """
    Scrobbles the given song to the user's Last.fm account.

    Args:
        song (dict): A dictionary representing the song to scrobble.
    """
    jarowinkler = JaroWinkler()

    network = get_last_fm_network()
    last_song = get_last_song()

    title = song['title']
    artist = song['artist']
    album = song['album']

    if last_song[0] != title:  # Check, so that this program doesn't scrobble the song multiple times
        last_scrobble = get_last_fm_last_scrobble(network)

        logging.info(f'LastFM: Last song was {last_scrobble[0][0].title} by {last_scrobble[0][0].artist}')

        if jarowinkler.similarity(str(last_scrobble[0][0].title.lower()),
                                title.lower()) < 0.9:  # check that "nobody else" scrobbled the song
            unix_timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
            if 'album' in locals():
                network.scrobble(artist=artist, title=title,
                                timestamp=unix_timestamp, album=album)
                network.update_now_playing(artist=artist, title=title,
                        album=album)
            else:
                network.scrobble(artist=artist, title=title,
                                timestamp=unix_timestamp)
                network.update_now_playing(artist=artist, title=title)
            logging.warning(f'Scrobbled {title} by {artist}')
            with open('last_song.json', 'w') as f:
                f.write(json.dumps((title, artist)))
                f.close()

        else:
            logging.error("Didn't double-scrobble because of lastFM")
            with open('last_song.json', 'w') as f:
                f.write(json.dumps((title, artist)))
                f.close()
    else:
        logging.error("Didn't double-scrobble because of JSON file")
        with open('last_song.json', 'w') as f:
            f.write(json.dumps((title, artist)))
            f.close()


if __name__ == "__main__":
    if not os.path.isdir('./logs'):
        os.mkdir('./logs')
    logger_filename = f'./logs/log_{datetime.datetime.now().strftime("%F")}.log'
    logging.basicConfig(level=logging.WARNING,
                        filename=logger_filename,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    history = get_ytm_history()
    song = get_last_song_from_history(history)
    scrobble_song(song)
