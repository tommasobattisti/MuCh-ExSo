class Song:
    def __init__(self, spotify_id):
        spotify_id = self.spotify_id

    def __str__(self):
        return f"Song: {self.spotify_id}"

    def get_spotify_data(self, spotify_id):
        # Get song data from Spotify API
        pass

    def get_genius_data(self, spotify_id):
        # Get song data from Genius API
        pass

    def get_musicbrainz_data(self, spotify_id):
        # Get song data from MusicBrainz API
        pass