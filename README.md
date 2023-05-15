# Youtube Music Playlist Local Downloader

## Description

This script will look at the current state of your Youtube Music playlists and download/update/delete songs from all playlist that have been downloaded to a local 'Music' folder. 

## Requirements

### FFmpeg Binary

[FFmpeg](https://ffmpeg.org/) is a leading multimedia framework, able to decode, encode, transcode, mux, demux, stream, and filter various audio and video formats. The binary needs to be downloaded specific for your operating system, and added to this root directory.

### Current Youtube Music Session Cookie

A `headers_auth.json` file containes the session data and cookie that the ytmusicapi python library uses to access personal Youtube Music data. A similar `headers_auth.json` file needs to be added to this root directory:

```
{
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Content-Type": "application/json",
    "X-Goog-AuthUser": "0",
    "x-origin": "https://music.youtube.com",
    "Cookie" : "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
```
You can read more information on how to extract the cookie from a browser session [here](https://ytmusicapi.readthedocs.io/en/stable/usage.html#authenticated). This script uses the manual json file load.

### Jellyfin Server Specific Features

This script will create mirrored Jellyfin playlists and add the local downloaded songs to these playlist. You will need to change the following variables to get this to work within the `createJellyfinPlaylist` function:

```
def createJellyfinPlaylist(title):
    # Create new empty playlist
    url = f'http://192.168.68.56:8096/Playlists'
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'x-mediabrowser-token': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    }                            
    payload = {
        "Name": str(title),
        "UserId": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",    
        "MediaType": "Music"
    }
    res = requests.request('POST', url=url, params=payload, headers=headers)
```

- The `url` needs to be changed to the local address of your Jellyfin server.
- The `x-mediabrowser-token` needs an updated API key. You can create a new API key from within the `Dashboard` view, under `API Keys`. (Example -> 192.168.1.1:8096/web/index.html#!/apikeys.html)
- The `UserId` needs to be changed. This can be found within the `Dashboard` view, under `Users`. If you click into a user profile, the userId is in the URL. (Example -> 192.168.1.1:8096/web/index.html#!/useredit.html?userId=hkjhkj4493b9e3242234iuyiscde3aa)

The `createJellyfinPlaylistXML` function will also need to reference the XML file that is created for each playlist. Asjust the path accordingly to your instance of Docker/Jellyfin.

## How it works

A `playlist_info` json object is created that will catalog all the songs and URLs that are in your youtube music playlists. Every time the script runs this json object will be checked against the actual state of your youtube playlist, and note the updates and deletions that need to happen. Songs will be deleted and downloaded accordingly, and new songs will be added to the Jellyfin instance playlist if applicable.

The `createJellyfinPlaylist` function uses the Jellyfin API to create a new playlist in Jellyfin. Make sure to add the correct IP adress for this to work. There is also a bug currently that will not allow you to create a new playlist if there doesn't already exists a playlist. To in the UI I have created a dummy 'default' playlist. 

The `createJellyfinPlaylistXML` function adds the song paths to the XML file that Jellyfin uses to add songs to playlist. Currently Jellyfin music playlist data is held in an external XML file. This function edits the existing file and insert the paths. To avoid XML malformity issues, the titles of songs downloaded from Youtube have modified names to remove illegal characters such as `&` and `.`