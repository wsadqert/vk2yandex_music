from yandex_music import ClientAsync, Track
from vkpymusic import Service
import asyncio
import re
import os
from tqdm import tqdm
from rich.traceback import install

install(width=300, show_locals=True)


def get_tracks_from_vk_playlist(service: Service, playlist_url: str = "https://vk.com/audios518118974?block=my_playlists&section=all&z=audio_playlist348129316_20") -> list[str]:
	def parse_playlist_url(url: str):
		_owner_id = int(re.search(r"(?<=(playlist))\d+", url).group())
		_playlist_id = int(re.search(rf"(?<=(playlist{_owner_id}_))\d+", url).group())

		return _owner_id, _playlist_id

	owner_id, playlist_id = parse_playlist_url(playlist_url)

	for playlist in service.get_playlists_by_userid(owner_id, 200):
		if playlist.playlist_id == playlist_id:
			break
	else:
		raise ValueError("playlist does not exist")

	tracks = [f'{track.artist} - {track.title}' for track in service.get_songs_by_playlist(playlist, count=playlist.count)]

	return tracks


async def search_yandex(client: ClientAsync, query, verbose=True) -> Track | None:
	search_result = await client.search(query)

	best_result_text = ''
	if search_result.best:
		if (type_ := search_result.best.type) != "track":
			print(f"\ncouldn't find track \"{query}\"")
			return None

		result = search_result.best.result

		if type_ in ['track', 'podcast_episode']:
			artists = ''
			if result.artists:
				artists = ', '.join(artist.name for artist in result.artists)
			best_result_text = ' - '.join((artists, result.title))
		elif type_ == 'artist':
			best_result_text = result.name
		elif type_ in ['album', 'podcast']:
			best_result_text = result.title
		elif type_ == 'playlist':
			best_result_text = result.title
		elif type_ == 'video':
			best_result_text = f'{result.title} {result.text}'

		if verbose:
			query_l = query.lower()
			best_result_text_l = best_result_text.lower()

			if (query_l != best_result_text_l) and \
				not (query_l.startswith(best_result_text_l)) and \
				not (best_result_text_l.startswith(query_l)):

				print(f"""requested: "{query}"\nfound:     "{best_result_text}"\n""")

				if input("CONTINUE? [Y/n]: ").lower() == 'n':
					return None

		return result


def parse_m3u8(filename: str = "playlist.m3u"):
	track_flag = "#EXTINF:-1,"
	tracks = []
	with open(filename, encoding="utf-8") as f:
		for line in f.readlines():
			if not line.startswith(track_flag):
				continue
			tracks.append(line[len(track_flag):].strip())

	return tracks


async def main():
	yandex_token = os.environ["YANDEX_TOKEN"]
	yandex_client = await ClientAsync(yandex_token).init()
	vk_client = Service.parse_config()

	yandex_playlist_kind: int = 1012

	vk_tracks = get_tracks_from_vk_playlist(vk_client)

	revision = 1
	for track_name in tqdm(vk_tracks):
		if track := await search_yandex(yandex_client, track_name, verbose=False):
			await yandex_client.usersPlaylistsInsertTrack(yandex_playlist_kind, track.id, track.albums[0].id, revision=revision)
			revision += 1

	print(vk_tracks)

asyncio.run(main())
