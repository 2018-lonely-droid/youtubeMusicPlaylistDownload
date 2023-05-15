# Youtube Music Playlist Local Downloader

## Description

This script will look at the current state of your Youtube Music playlists and download/update/delete songs from all playlist that have been downloaded to a local 'Music' folder. 

## How it works

A `playlist_info` json object is created that will catalog all the songs and URLs that are in your youtube music playlists. Every time the script runs this json object will be checked against the actual state of your youtube playlist, and note the updates and deletions that need to happen. Songs will be deleted and downloaded accordingly, and new songs will be added to the Jellyfin instance playlist if applicable.

The `createJellyfinPlaylist` function uses the Jellyfin API to create a new playlist in Jellyfin. Make sure to add the correct IP adress for this to work. There is also a bug currently that will not allow you to create a new playlist if there doesn't already exists a playlist. To in the UI I have created a dummy 'default' playlist. 

The `createJellyfinPlaylistXML` function adds the song paths to the XML file that Jellyfin uses to add songs to playlist. Currently Jellyfin music playlist data is held in an external XML file. This function edits the existing file and insert the paths. To avoid XML malformity issues, the titles of songs downloaded from Youtube have modified names to remove illegal characters such as `&` and `.`

## Getting started

The following will need to be modified to get up and running:

- The script requires a *headers_auth.json* file in the root directory. More info on this can be found [here](https://ytmusicapi.readthedocs.io/en/stable/usage.html#authenticated). This script uses the manual json file load.

- The IP address in `createJellyfinPlaylist` needs to be modified to reflect the server where Jellyfin is hosted. If you are not using a Jellyfin server on your local, this can be commented out. 

- The `downloadPlaylist` function contains the path where the Music folder is created, and where the music will be downloaded. I have modified this to work well on my server, but of course you can change the Music folder download path to your needs.