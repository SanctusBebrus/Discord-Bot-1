import yandex_music.track.track
from yandex_music import Client
from settings import yandex_api_settings

client = Client(yandex_api_settings['token']).init()


def get_tracks_info(name: str, count: int = 10):
    tracks = client.search(text=name, type_='track', nocorrect=False)['tracks']
    if tracks:
        tracks = tracks['results'][:count]
        track: yandex_music.track.track.Track = tracks[0]

        return [
            {
                'title': track['title'],
                'artists': ', '.join([artist['name'] for artist in track['artists']]),
                'duration': (lambda x: f'{x // 60 // 1000}:{str(x // 1000 - x // 60 // 1000 * 60).rjust(2, "0")}')(
                    track["duration_ms"]),
                'id': track['id'],
                'image_url': f'https://{track.cover_uri.replace("%%", "400x400")}'
            } for track in tracks
        ]
    return None


def download_track(id: int, path: str = ''):
    client.tracks(id)[0].download(path + f'{id}.mp3')
