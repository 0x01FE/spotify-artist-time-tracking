import dataclasses
import typing

@dataclasses.dataclass(kw_only=True)
class ExternalUrls:
    spotify: str

@dataclasses.dataclass(kw_only=True)
class Context:
    type: str
    href: str
    external_urls: ExternalUrls
    uri: str

@dataclasses.dataclass(kw_only=True)
class Followers:
    href: str | None
    total: int

@dataclasses.dataclass(kw_only=True)
class Image:
    url: str
    height: int
    width: int


@dataclasses.dataclass(kw_only=True)
class Artist:
    external_urls: ExternalUrls
    followers: Followers | None = None
    genres: list[str] | None = None
    href: str = ""
    id: str = ""
    images: list[Image] | None = None
    name: str = ""
    popularity: int | None = None
    type: str = ""
    uri: str = ""

    @classmethod
    def from_json(cls, data: dict) -> typing.Self:
        def parse_external_urls(d):
            return ExternalUrls(**d)

        def parse_followers(d):
            if d is None:
                return None
            return Followers(href=d.get("href"), total=d["total"])

        def parse_images(imgs):
            return [Image(**img) for img in imgs] if imgs else []

        return cls(
            external_urls=parse_external_urls(data["external_urls"]),
            followers=parse_followers(data.get("followers")),
            genres=data.get("genres", []),
            href=data.get("href", ""),
            id=data.get("id", ""),
            images=parse_images(data.get("images", [])),
            name=data.get("name", ""),
            popularity=data.get("popularity"),
            type=data.get("type", ""),
            uri=data.get("uri", ""),
        )

@dataclasses.dataclass(kw_only=True)
class Album:
    album_type: str
    total_tracks: int
    available_markets: list[str]
    external_urls: ExternalUrls
    href: str
    id: str
    images: list[Image]
    name: str
    release_date: str
    release_date_precision: str
    type: str
    uri: str
    artists: list[Artist]

@dataclasses.dataclass(kw_only=True)
class ExternalIds:
    isrc: str

@dataclasses.dataclass(kw_only=True)
class Track:
    album: Album
    artists: list[Artist]
    available_markets: list[str]
    disc_number: int
    duration_ms: int
    explicit: bool
    external_ids: ExternalIds
    external_urls: ExternalUrls
    href: str
    id: str
    name: str
    popularity: int
    preview_url: str | None
    track_number: int
    type: str
    uri: str
    is_local: bool

@dataclasses.dataclass(kw_only=True)
class CurrentlyPlayingTrack:
    context: Context
    timestamp: int
    progress_ms: int
    is_playing: bool
    item: Track
    currently_playing_type: str
    actions: dict

    @classmethod
    def from_json(cls, data: dict) -> typing.Self:
        def parse_external_urls(d):
            return ExternalUrls(**d)

        def parse_artist(d):
            return Artist(
                external_urls=parse_external_urls(d["external_urls"]),
                href=d["href"],
                id=d["id"],
                name=d["name"],
                type=d["type"],
                uri=d["uri"],
            )

        def parse_image(d):
            return Image(
                url=d["url"],
                height=d["height"],
                width=d["width"],
            )

        def parse_album(d):
            return Album(
                album_type=d["album_type"],
                total_tracks=d["total_tracks"],
                available_markets=d["available_markets"],
                external_urls=parse_external_urls(d["external_urls"]),
                href=d["href"],
                id=d["id"],
                images=[parse_image(img) for img in d["images"]],
                name=d["name"],
                release_date=d["release_date"],
                release_date_precision=d["release_date_precision"],
                type=d["type"],
                uri=d["uri"],
                artists=[parse_artist(a) for a in d["artists"]],
            )

        def parse_external_ids(d):
            return ExternalIds(isrc=d["isrc"])

        def parse_track(d):
            return Track(
                album=parse_album(d["album"]),
                artists=[parse_artist(a) for a in d["artists"]],
                available_markets=d["available_markets"],
                disc_number=d["disc_number"],
                duration_ms=d["duration_ms"],
                explicit=d["explicit"],
                external_ids=parse_external_ids(d["external_ids"]),
                external_urls=parse_external_urls(d["external_urls"]),
                href=d["href"],
                id=d["id"],
                name=d["name"],
                popularity=d["popularity"],
                preview_url=d.get("preview_url"),
                track_number=d["track_number"],
                type=d["type"],
                uri=d["uri"],
                is_local=d["is_local"],
            )

        def parse_context(d):
            return Context(
                type=d["type"],
                href=d["href"],
                external_urls=parse_external_urls(d["external_urls"]),
                uri=d["uri"],
            )

        return cls(
            context=parse_context(data["context"]),
            timestamp=data["timestamp"],
            progress_ms=data["progress_ms"],
            is_playing=data["is_playing"],
            item=parse_track(data["item"]),
            currently_playing_type=data["currently_playing_type"],
            actions=data["actions"]
        )
