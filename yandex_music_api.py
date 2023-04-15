from yandex_music import Client
from settings import yandex_api_settings

client = Client(yandex_api_settings['token']).init()


def get_tracks_info(name: str, count: int = 10):
    tracks = client.search(text=name, type_='track', nocorrect=False)['tracks']
    if tracks:
        tracks = tracks['results'][:count]

        return [
            {
                'title': track['title'],
                'artists': [artist['name'] for artist in track['artists']],
                'duration': (lambda x: f'{x// 60 // 1000}:{str(x // 1000 - x // 60 // 1000 * 60).rjust(2, "0")}')(track["duration_ms"]),
                'id': track['id']
            } for track in tracks
        ]
    return None


def download_track(id: int, path: str = ''):
    client.tracks(id)[0].download(path + f'{id}.mp3')
