import asyncio
import discord
import yt_dlp
from utils.logger import get_logger

music_logger = get_logger("music")

YTDL_OPTIONS = {
    "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

YTDL_FLAT_OPTIONS = {
    **YTDL_OPTIONS,
    "extract_flat": "in_playlist",
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-bufsize 64k "
        "-probesize 200k "
        "-analyzeduration 0"
    ),
    "options": "-vn -b:a 128k",
}

# Stored on ready so the after() callback has a reliable event loop
_bot_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    global _bot_loop
    _bot_loop = loop


class Track:
    def __init__(self, webpage_url: str, title: str, duration: int, thumbnail: str, requester: discord.Member):
        self.webpage_url = webpage_url  # permanent YouTube URL
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester
        self._stream_url: str | None = None  # resolved lazily just before playback

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return "Unknown"
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    async def resolve(self) -> str:
        """Fetch a fresh stream URL right before playback."""
        loop = asyncio.get_event_loop()

        def _extract():
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = ydl.extract_info(self.webpage_url, download=False)
                return info["url"]

        self._stream_url = await loop.run_in_executor(None, _extract)
        return self._stream_url

    def __str__(self):
        return f"[{self.title}]({self.webpage_url}) `{self.duration_str}`"


async def search(query: str, requester: discord.Member) -> list[Track]:
    """Search YouTube and return Track objects with webpage_url only — no stream URLs yet."""
    loop = asyncio.get_event_loop()

    def _extract():
        with yt_dlp.YoutubeDL(YTDL_FLAT_OPTIONS) as ydl:
            if not query.startswith("http"):
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get("entries", [])
            else:
                info = ydl.extract_info(query, download=False)
                entries = info.get("entries", [info])
        return entries

    try:
        entries = await loop.run_in_executor(None, _extract)
    except Exception as e:
        music_logger.error(f"yt-dlp search error: {e}")
        return []

    tracks = []
    for entry in entries:
        if not entry:
            continue
        try:
            webpage_url = entry.get("webpage_url") or entry.get("url", "")
            if not webpage_url:
                continue

            track = Track(
                webpage_url=webpage_url,
                title=entry.get("title", "Unknown"),
                duration=entry.get("duration", 0),
                thumbnail=entry.get("thumbnail", ""),
                requester=requester
            )
            tracks.append(track)
        except Exception as e:
            music_logger.warning(f"Failed to process entry: {e}")
            continue

    return tracks


class MusicQueue:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue: list[Track] = []
        self.current: Track | None = None
        self.loop: bool = False
        self.volume: float = 0.5

    def add(self, track: Track):
        self.queue.append(track)

    def add_many(self, tracks: list[Track]):
        self.queue.extend(tracks)

    def clear(self):
        self.queue.clear()
        self.current = None

    def shuffle(self):
        import random
        random.shuffle(self.queue)

    def next(self) -> Track | None:
        if self.loop and self.current:
            return self.current
        if self.queue:
            return self.queue.pop(0)
        return None


_queues: dict[int, MusicQueue] = {}


def get_queue(guild_id: int) -> MusicQueue:
    if guild_id not in _queues:
        _queues[guild_id] = MusicQueue(guild_id)
    return _queues[guild_id]


async def play_next(guild: discord.Guild):
    mq = get_queue(guild.id)
    vc = guild.voice_client

    if vc is None or not vc.is_connected():
        music_logger.info(f"Voice client gone for guild {guild.id} — stopping")
        mq.clear()
        return

    track = mq.next()

    if track is None:
        mq.current = None
        music_logger.info(f"Queue empty for guild {guild.id}")
        return

    mq.current = track

    try:
        # Resolve fresh stream URL right before playback
        music_logger.info(f"Resolving stream URL for: {track.title}")
        stream_url = await track.resolve()

        source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=mq.volume)

        def after(error):
            if error:
                music_logger.error(f"Playback error in guild {guild.id}: {error}")
            if _bot_loop:
                asyncio.run_coroutine_threadsafe(play_next(guild), _bot_loop)
            else:
                music_logger.error("No event loop stored — cannot schedule next track")

        vc.play(source, after=after)
        music_logger.info(f"Now playing in guild {guild.id}: {track.title}")

    except Exception as e:
        music_logger.error(f"Failed to play '{track.title}' in guild {guild.id}: {e}")
        # Skip to next track on failure
        await play_next(guild)