import requests, re, os
from lyricsgenius import Genius
import musicbrainzngs as mbz
from dotenv import load_dotenv

load_dotenv()


class SongDataCollector(object):

    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')
    MUSICBRAINZ_USER = os.getenv('MUSICBRAINZ_USER')
    MUSICBRAINZ_TOKEN = os.getenv('MUSICBRAINZ_TOKEN')


    def __init__(self, spotify_id):
        self.spotify_id = spotify_id

    def __str__(self):
        return f"Song: {self.spotify_id}"


    def get_spotify_headers(self):
        # Get headers for Spotify API
        data = {
                'grant_type': 'client_credentials',
                'client_id': self.SPOTIFY_CLIENT_ID,
                'client_secret': self.SPOTIFY_CLIENT_SECRET,
                }

        response = requests.post('https://accounts.spotify.com/api/token', data=data).json()
        token_type = response['token_type']
        access_token = response['access_token']
        return { 'Authorization': str(token_type) + ' ' + str(access_token), }



    def get_spotify_song(self, headers=None):
        # Get song data from Spotify API
        if headers == None:
            headers = self.get_spotify_headers()
        return requests.get(f'https://api.spotify.com/v1/tracks/{self.spotify_id}', headers=headers).json()


    def get_spotify_artist(self, artist_id, headers=None):
        # Get song data from Spotify API
        if headers == None:
            headers = self.get_spotify_headers()
        return requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers).json()



    def save_spotify_data(self):
        # Save song data from Spotify API
        song = {}
        headers = self.get_spotify_headers()
        song_data = self.get_spotify_song(headers)
        song['spotify_id'] = song_data['id']
        song['spotify_href'] = song_data['href']
        song['name'] = song_data['name']
        song['artists'] = []
        for artist in song_data['artists']:
            artist_dict = {}
            artist_dict['spotify_id'] = artist['id']
            artist_dict['spotify_href'] = artist['href']
            artist_dict['name'] = artist['name']
            get_art =  self.get_spotify_artist(artist['id'], headers)
            artist_dict['genres'] = get_art['genres']
            song['artists'].append(artist_dict)
        song['isrc'] = song_data['external_ids']['isrc']

        return song




    def get_genius_data(self, song_name, artist_name):
        # Get song data from Genius API
        genius = Genius(self.GENIUS_ACCESS_TOKEN)
        return genius.search_song(song_name, artist_name)



    def save_genius_data(self, song_name, artist_name, store=dict()):
        genius = Genius(self.GENIUS_ACCESS_TOKEN)
        genius_song = self.get_genius_data(song_name, artist_name)
        genius_id = genius_song.id

        store['genius_id'] = genius_id
        store['genius_url'] = genius_song.url
        store['lyrics'] = re.sub(r'[0-9]+\sContributors.+\sLyrics\n', '', genius.lyrics(genius_id, remove_section_headers=True))
        
        annotations_list = []
        annotations = genius.song_annotations(genius_id)
        for tup in annotations:
            new_tup = (tup[0], tup[1][0][0])
            annotations_list.append(new_tup)
        store['annotations'] = annotations_list

        return store


        


    def get_musicbrainz_song(self, user_agent, version, isrc, auth=False):
        # Get song data from MusicBrainz API
        if auth:
            mbz.set_useragent(user_agent, version)
            mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)
        mbz_song = mbz.get_recordings_by_isrc(isrc)
        return mbz.get_recording_by_id(mbz_song['isrc']['recording-list'][0]['id'], includes=['artists'])
    

    def get_musicbrainz_artist(self, user_agent, version, art_id, auth=False):
        # Get artist data from MusicBrainz API
        if auth:
            mbz.set_useragent(user_agent, version)
            mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)
        return mbz.get_artist_by_id(art_id, includes=["url-rels", "tags"])

    
    def save_musicbrainz_data(self, user_agent, version, isrc, store=dict()):
        # Save song data from MusicBrainz API
        mbz.set_useragent(user_agent, version)
        mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)

        mbz_song = self.get_musicbrainz_song(user_agent, version, isrc)
        if 'artists' not in store:
            art_dict = {}
            for artist in mbz_song['artist-credit']:
                art_dict['name'] = artist['artist']['name']
                art_dict['mbz_id'] = artist['artist']['id']
                art_dict['disambiguation'] = artist['artist']['disambiguation']
                #art_dict['tags'] = artist['artist']['tags']
            store['artists'] = art_dict
        else:
            for art in store['artists']: #for every artist in the song_ditionary
                for mbz_art in mbz_song['recording']['artist-credit']:   #for every artist in the mbz dictionary
                    if art['name'] == mbz_art['artist']['name']:   #if the name of the artist in the song dictionary is the same as the name of the artist in the mbz dictionary
                        art['disambiguation'] = mbz_art['artist']['disambiguation'] #add the disambiguation to the song dictionary
                        art['mbz_id'] = mbz_art['artist']['id'] #add the mbz id to the song dictionary
                        #art['mbz_tags'] = {}
                        #for tag in mbz_art['artist']['tag-list']: #for every tag in the mbz dictionary
                        #    art['mbz_tags'][tag['name']] = tag['count'] #add the tag name and the tag count to the song dictionary
                wts = self.get_musicbrainz_artist(user_agent, version, art['mbz_id'])
                art['type'] = wts['artist']['type']
                for url in wts['artist']['url-relation-list']:
                    if url['type'] == 'wikidata':
                        art['wikidata_url'] = url['target']
        return store


    def get_song_data(self, mbz_user_agent, mbz_app_version):
        # Get song data from all APIs
        song_data = self.save_spotify_data()
        song_data = self.save_genius_data(song_data['name'], song_data['artists'][0]['name'], song_data)
        song_data = self.save_musicbrainz_data(mbz_user_agent, mbz_app_version, song_data['isrc'], song_data)
        return song_data