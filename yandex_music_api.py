import json
import os

import requests
import yandex_music.track.track
from yandex_music import Client

from settings import yandex_api_settings

client: Client = Client(yandex_api_settings['token']).init()


def get_tracks_info(name: str, count: int = 10):
    tracks = client.search(text=name, type_='track', nocorrect=False)['tracks']
    if tracks:
        tracks = tracks['results'][:count]

        return [get_track_info(track) for track in tracks]


def get_chart_tracks_info():
    tracks = [i['track'] for i in
              json.loads(requests.get('https://api.music.yandex.net/landing3/chart/russia').content)['result']['chart'][
                  'tracks']]

    if tracks:
        return [
            {
                'title': track['title'],
                'artists': ', '.join([artist['name'] for artist in track['artists']]),
                'duration': track['durationMs'],
                'id': track['id'],
                'image_url': f'https://{track["coverUri"].replace("%%", "400x400")}'
            } for track in tracks
        ]


def get_track_info(track):
    return {
        'title': track['title'],
        'artists': ', '.join([artist['name'] for artist in track['artists']]),
        'duration': track['duration_ms'],
        'id': track['id'],
        'image_url': f'https://{track.cover_uri.replace("%%", "400x400")}'
    }


def download_track(id: int, path: str = ''):
    if not os.path.exists(path):
        os.mkdir(path)

    client.tracks(id)[0].download(path + f'{id}.mp3')


def get_albums_info(name: str):
    albums: yandex_music.album.album.Album = client.search(text=name, type_='album', nocorrect=False)['albums']
    if not albums:
        return
    albums = albums['results']
    if albums:
        return [
            {
                'title': album['title'],
                'artists': ', '.join([artist['name'] for artist in album['artists']]),
                'id': album['id'],
                'track_count': album['track_count'],
                'image_url': f'https://{album.cover_uri.replace("%%", "400x400")}'
            } for album in albums
        ]
