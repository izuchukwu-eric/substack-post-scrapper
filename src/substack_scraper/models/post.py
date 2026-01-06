"""Substack post model matching the required JSON structure."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .author import PublishedByline


class PostTag(BaseModel):
    """Post tag/category."""

    model_config = ConfigDict(extra="allow")

    id: str
    publication_id: int
    name: str
    slug: str
    hidden: bool = False


class PodcastFields(BaseModel):
    """Podcast-specific metadata."""

    model_config = ConfigDict(extra="allow")

    post_id: int
    podcast_episode_number: int | None = None
    podcast_season_number: int | None = None
    podcast_episode_type: str | None = None
    should_syndicate_to_other_feed: bool | None = None
    syndicate_to_section_id: int | None = None
    hide_from_feed: bool = False
    free_podcast_url: str | None = None
    free_podcast_duration: float | None = None


class AudioItem(BaseModel):
    """Audio item for text-to-speech or voiceover."""

    model_config = ConfigDict(extra="allow")

    post_id: int
    voice_id: str | None = None
    audio_url: str | None = None
    type: str | None = None
    status: str | None = None
    duration: float | None = None


class VoiceoverUpload(BaseModel):
    """Voiceover upload details."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str | None = None
    created_at: datetime | str | None = None
    uploaded_at: datetime | str | None = None
    publication_id: int | None = None
    state: str | None = None
    post_id: int | None = None
    user_id: int | None = None
    duration: float | None = None
    height: int | None = None
    width: int | None = None
    thumbnail_id: int | None = None
    preview_start: float | None = None
    preview_duration: float | None = None
    media_type: str | None = None
    primary_file_size: int | None = None
    is_mux: bool = False
    mux_asset_id: str | None = None
    mux_playback_id: str | None = None
    mux_preview_asset_id: str | None = None
    mux_preview_playback_id: str | None = None
    mux_rendition_quality: str | None = None
    mux_preview_rendition_quality: str | None = None
    explicit: bool = False
    copyright_infringement: str | None = None
    src_media_upload_id: str | None = None
    live_stream_id: str | None = None


class ColorPalette(BaseModel):
    """Color palette entry."""

    model_config = ConfigDict(extra="allow")

    rgb: list[float]
    population: int


class CoverImagePalette(BaseModel):
    """Cover image color palette."""

    model_config = ConfigDict(extra="allow")

    Vibrant: ColorPalette | None = None
    DarkVibrant: ColorPalette | None = None
    LightVibrant: ColorPalette | None = None
    Muted: ColorPalette | None = None
    DarkMuted: ColorPalette | None = None
    LightMuted: ColorPalette | None = None


class SubstackPost(BaseModel):
    """Main Substack post model matching the required JSON output structure."""

    model_config = ConfigDict(extra="allow")

    # Search context
    keyword: str = Field(..., description="The search keyword used to find this post")

    # Post identifiers
    id: int
    publication_id: int
    type: str = "newsletter"
    slug: str

    # Content fields
    title: str
    social_title: str | None = None
    search_engine_title: str | None = None
    search_engine_description: str | None = None
    subtitle: str | None = None
    description: str | None = None
    truncated_body_text: str | None = None
    body_json: Any | None = None
    body_html: str | None = None
    wordcount: int | None = None

    # Editor
    editor_v2: bool = False

    # Media
    cover_image: str | None = None
    cover_image_is_square: bool = False
    cover_image_is_explicit: bool = False
    coverImagePalette: CoverImagePalette | None = None

    # URLs
    canonical_url: str

    # Dates
    post_date: datetime | str

    # Audience and permissions
    audience: str = "everyone"
    write_comment_permissions: str = "everyone"
    should_send_free_preview: bool = False
    free_unlock_required: bool = False
    default_comment_sort: str | None = None
    teaser_post_eligible: bool = True

    # Section info
    section_id: int | None = None
    section_slug: str | None = None
    section_name: str | None = None
    is_section_pinned: bool = False

    # Positioning
    position: int | None = None
    top_exclusions: list[Any] = []
    pins: list[int] = []

    # Engagement metrics
    reactions: dict[str, int] | None = None
    restacks: int = 0
    reaction: Any | None = None
    reaction_count: int = 0
    comment_count: int = 0
    child_comment_count: int = 0

    # Restack info
    restacked_post_id: int | None = None
    restacked_post_slug: str | None = None
    restacked_pub_name: str | None = None
    restacked_pub_logo_url: str | None = None

    # Podcast/Video fields
    podcast_duration: float | None = None
    video_upload_id: str | None = None
    podcast_upload_id: str | None = None
    podcast_url: str | None = None
    videoUpload: Any | None = None
    podcastFields: PodcastFields | None = None
    podcast_preview_upload_id: str | None = None
    podcastUpload: Any | None = None
    podcastPreviewUpload: Any | None = None

    # Voiceover
    voiceover_upload_id: str | None = None
    voiceoverUpload: VoiceoverUpload | None = None
    has_voiceover: bool = False

    # Related data
    postTags: list[PostTag] = []
    publishedBylines: list[PublishedByline] = []
    audio_items: list[AudioItem] = []
    postCountryBlocks: list[Any] = []
    headlineTest: Any | None = None

    # Status flags
    is_geoblocked: bool = False
    hasCashtag: bool = False

    # Metadata
    scrapedAt: datetime = Field(default_factory=datetime.utcnow)
