# from __future__ import unicode_literals
from dotenv import load_dotenv
import logging
import spotipy
# from spotify import connect, fetchPlaylistById, fetchPlaylistUser, extractSongs, query_builder # spotify
from ytmusicapi import YTMusic # Get playlist info from personal account
load_dotenv() # Load .env file
ytmusic = YTMusic('headers_auth.json') # Load authenticated cookie creds for youtube music
import yt_dlp as yt # Download youtube videos
import mutagen # Insert thumbnails into songs
import urllib3.request # Download thumbnails
import time
import os
from pathlib import Path
import re
import json
import requests # Needed for jellyfin api request
from xml.etree import ElementTree as ET # create xml file


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def convertSpotifyPlaylist():
    # Get spotify playlist id from url
    playlistURL = input('Please enter your Spotify Playlist URL: ')
    playlistID  = re.search('.*\/(.*)\?', playlistURL).groups()[0]
    # Connect to spotify
    spotifyAPI = connect(os.environ.get('clientID'), os.environ.get('clientSecret'))
    print('Connected to Spotify')
    # Fetch playlist songs
    playlistUser, playlistName, playlistThumbnail, playlistItems = fetchPlaylistById(spotifyAPI, playlistID)
    queries = query_builder(extractSongs(spotifyAPI, playlistItems))
    # Fetch user URL & follower count
    playlistUserMetaData = fetchPlaylistUser(spotifyAPI, playlistUser)
    # Build description
    ytMusicDescription = (  'Made by: ' + str(playlistUserMetaData['display_name']) +  
                            ' | Followers: ' +  str(playlistUserMetaData['followers']['total']) +  
                            ' | Profile: ' +  'https://open.spotify.com/user/' + str(playlistUserMetaData['id']) +
                            ' | Thumbnail: ' + str(playlistThumbnail))
    print('Fetched Spotify playlist')

    # Loop through spotify songs
    videoIds = []
    for song in queries:
        # Search for matching song title and load top result video id
        match = ytmusic.search(query=song, filter='songs', limit=1)
        print(str(match[0]['title']) + ' | Album: ' + str(match[0]['album']['name']) + ' | Duration: ' + str(match[0]['duration']))
        videoIds.append(match[0]['videoId'])

    # Insert songs into YT playlist
    ytmusic.create_playlist(title=playlistName, description=ytMusicDescription, video_ids=videoIds)
    print("Finished migrating")


def getPlaylistInfo():
    # Construct new playlist infro for youtube download
    newPlaylistInfo = []
    playlists = ytmusic.get_library_playlists()
    for playlist in playlists:
        # Create objects for youtube file download and seperate for jellyfin titles and related urls
        newPlaylist = {}
        cleanedTrackTitle = playlist['title'].replace('<', '').replace('>', '').replace('"', '').replace("'", "").replace('&', 'and').replace('.', '').replace(':', '').replace('/', '').replace('\/', '')
        newPlaylist['title'] = cleanedTrackTitle

        # Liked Music playlist doesn't include count -- get it with get_playlist
        if playlist['title'] == 'Liked Music': 
            yourLikesPlaylist = ytmusic.get_playlist(playlistId=playlist['playlistId'], limit=10000)
            newPlaylist['count'] = yourLikesPlaylist['trackCount']
        # For now don't include the updates episodes for later auto playlist
        elif playlist['title'] == 'Episodes for Later':
            continue
        # Every other playlist should have a count attribute
        else: 
            newPlaylist['count'] = playlist['count']

        # Get list of songs on each playlist
        tempPlaylist = ytmusic.get_playlist(playlistId=playlist['playlistId'], limit=10000)
        tracks = []
        # Add title and url link that will be needed for jellyfin playlist matchup
        for track in tempPlaylist['tracks']:
            cleanedTrackName = track['title'].replace('<', '').replace('>', '').replace('"', '').replace("'", "").replace('&', 'and').replace('.', '').replace(':', '').replace('/', '').replace('\/', '')
            tracks.append({'trackName': cleanedTrackName, 'trackURL': ('https://music.youtube.com/watch?v=' + track['videoId'])})

        # Add objects to json lists
        newPlaylist['tracks'] = tracks
        newPlaylistInfo.append(newPlaylist)

    return newPlaylistInfo


def getPlaylistDiff(existingPlaylists, newPlaylistInfo):
    playlistDiffs = []
    # If there are existing playlist check changes
    if existingPlaylists:
        for existingPlaylist in existingPlaylists:
            for newPlaylist in newPlaylistInfo:
                if newPlaylist['title'] == existingPlaylist['title'] and newPlaylist['count'] != existingPlaylist['count']:
                    playlistDiff = {}
                    playlistDiff['title'] = newPlaylist['title']
                    playlistDiff['delete'] = ''
                    playlistDiff['append'] = ''

                    # Temp list of existing and new track ids
                    existingPlaylistTrackList = []
                    for track in existingPlaylist['tracks']:
                        existingPlaylistTrackList.append(track['trackURL'])
                    newPlaylistTrackList = []
                    for track in newPlaylist['tracks']:
                        newPlaylistTrackList.append(track['trackURL'])

                    # Check to delete
                    deleteList = []
                    for track in existingPlaylist['tracks']:
                        if track['trackURL'] not in newPlaylistTrackList:
                            logging.info(f'New song to be deleted from {newPlaylist["title"]} playlist: {track["trackName"]}')
                            deleteList.append(track)
                    if deleteList:
                        playlistDiff['delete'] = {'tracks': deleteList}

                    # Check to append
                    appendList = []
                    for track in newPlaylist['tracks']:
                        if track['trackURL'] not in existingPlaylistTrackList:
                            logging.info(f'New song to be added to {newPlaylist["title"]} playlist: {track["trackName"]}')
                            appendList.append(track)
                    if appendList:
                        playlistDiff['append'] = {'tracks': appendList}

                    # Only add dict if there are changes
                    if playlistDiff['delete'] or playlistDiff['append']:
                        playlistDiffs.append(playlistDiff)

    # No existing playlist download everything
    else:
        for newPlaylist in newPlaylistInfo:
            playlistDiff = {}
            playlistDiff['title'] = newPlaylist['title']
            playlistDiff['append'] = {'tracks': newPlaylist['tracks']}
            playlistDiffs.append(playlistDiff)

    return playlistDiffs


def downloadPlaylist(playlist):
    # Create playlist folder in local if doesn't exist
    pathAboveMusicFolder = Path(os.getcwd()).parents[1]
    newDir = os.path.join(pathAboveMusicFolder, 'Music', playlist['title'])
    if not os.path.exists(newDir):
        os.makedirs(newDir)
      
    for track in playlist['append']['tracks']:
        # 'ffmpeg_location': str(os.getcwd()),
        ydl_opts = {
            'format': 'bestaudio/best',
            'ignoreerrors':True,
            'extractaudio':True,
            'audioformat':'opus',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'outtmpl': (f'{newDir}/' + f'{track["trackName"]}'), # name the file the title of video
            'writethumbnail': True,
            'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus', 'preferredquality': '128'},
                    {'key': 'FFmpegMetadata', 'add_metadata': 'True'},
                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
            ],
            'ppa': 'ThumbnailsConvertor:-q:v 1'
        }
    
        # Download all songs in playlist
        with yt.YoutubeDL(ydl_opts) as ydl:
            # This is for download
            ydl.download(track['trackURL'])
            # # This is to not hit api rate limits
            # time.sleep(1)


def createJellyfinPlaylist(title):
    # Create new empty playlist
    url = f'http://192.168.68.56:8096/Playlists'
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'x-mediabrowser-token': '6413eee5d68b4e609563334be2d7211f'
    }
    payload = {
        "Name": str(title),
        "UserId": "08ba1929-681e-4b24-929b-9245852f65c0",
        "MediaType": "Music"
    }
    res = requests.request('POST', url=url, params=payload, headers=headers)


def createJellyfinPlaylistXML(playlist, existInJellyfin):
    # Open existing playlist file
    with open(f'/srv/dev-disk-by-uuid-88dba951-7a3c-4e8e-9bf7-8376db5d6c4a/Docker/jellyfin/config/data/data/playlists/{playlist["title"]}/playlist.xml', 'rb') as xml_file:
        tree = ET.parse(xml_file)
    root = tree.getroot()

    # If it is the first time a playlist is added to jellyfin, it is missing the PlaylistItems tag that is needed to insert links
    if not existInJellyfin:
        root.append(ET.Element('PlaylistItems'))

    # Insert list of XML snippets into the PlaylistItems
    elem = root.find('PlaylistItems')
    for track in playlist['append']['tracks']:
        XMLString = fr'''<PlaylistItem><Path>/data/music/{playlist["title"]}/{track["trackName"]}.opus</Path></PlaylistItem>'''
        elem.append(ET.fromstring(XMLString))

    # Write changes to file -- must refresh in jellyfin to see changes
    with open(f'/srv/dev-disk-by-uuid-88dba951-7a3c-4e8e-9bf7-8376db5d6c4a/Docker/jellyfin/config/data/data/playlists/{playlist["title"]}/playlist.xml', 'wb') as f:
        tree.write(f, encoding='utf-8')


def main():
    # Load up existing playlist song counts
    existingPlaylists = []
    if os.path.exists('playlist_info.json'):
        f = open('playlist_info.json')
        data = json.load(f)
        existingPlaylists = data['playlists']
    else:
        logging.info('No existing playlist_info.json found. Attempt to download all playlists')

    # Get current playlist song counts
    newPlaylistInfo = getPlaylistInfo()
    logging.info('Loaded current playlist info')

    # Get diff between new and existing playlist
    playlistDiffs =  getPlaylistDiff(existingPlaylists, newPlaylistInfo)

    # Iterate diff playlist and download songs
    if playlistDiffs:
        for playlist in playlistDiffs:
            if 'append' in playlist:
                if playlist['append'] != '':
                    # Check if it is a new playlist. If so, create in Jellyfin
                    existInJellyfin = False
                    for existingPlaylist in existingPlaylists:
                        if playlist['title'] == existingPlaylist['title']:
                            existInJellyfin = True
                    if not existInJellyfin:
                        createJellyfinPlaylist(playlist['title'])

                    # Download playlist to Music folder
                    downloadPlaylist(playlist)

                    # Modify jellyfin playlist with all the correct songs downloaded to playlist folder
                    createJellyfinPlaylistXML(playlist, existInJellyfin)
                    
                    logging.info('All downloads complete')

            if 'delete' in playlist:
                if playlist['delete'] != '':
                    for track in playlist['delete']['tracks']:
                        os.remove(os.path.join(os.getcwd(), 'Music', playlist['title'], (track['title'] + '.opus')))
                        logging.info(f'Song {track["title"]} was deleted from {playlist["title"]} playlist')
                    logging.info('All deletions complete')

        # Keep a copy of the playlist layout and set as existing
        with open('playlist_info.json', 'w') as fout:
            json.dump({'playlists': newPlaylistInfo}, fout)
        logging.info('Current playlist copied to playlist_info.json')
    else:
        logging.info('No updates to any playlist')


main()



