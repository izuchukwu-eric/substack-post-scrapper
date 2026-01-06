"""Author and publication models for Substack posts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Publication(BaseModel):
    """Substack publication details."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    subdomain: str
    custom_domain: str | None = None
    custom_domain_optional: bool = False
    hero_text: str | None = None
    logo_url: str | None = None
    author_id: int | None = None
    primary_user_id: int | None = None
    theme_var_background_pop: str | None = None
    created_at: datetime | str | None = None
    email_from_name: str | None = None
    copyright: str | None = None
    founding_plan_name: str | None = None
    community_enabled: bool = False
    invite_only: bool = False
    payments_state: str | None = None
    language: str | None = None
    explicit: bool = False
    homepage_type: str | None = None
    is_personal_mode: bool = False


class PublicationUser(BaseModel):
    """User's role in a publication."""

    model_config = ConfigDict(extra="allow")

    id: int
    user_id: int
    publication_id: int
    role: str
    public: bool = True
    is_primary: bool = False
    publication: Publication | None = None


class UserStatus(BaseModel):
    """User status and badges."""

    model_config = ConfigDict(extra="allow")

    bestsellerTier: int | None = None
    subscriberTier: int | None = None
    leaderboard: Any | None = None
    vip: bool = False
    badge: dict[str, Any] | None = None
    paidPublicationIds: list[int] = []
    subscriber: Any | None = None


class PublishedByline(BaseModel):
    """Author/byline information for a post."""

    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    handle: str | None = None
    previous_name: str | None = None
    photo_url: str | None = None
    bio: str | None = None
    profile_set_up_at: datetime | str | None = None
    reader_installed_at: datetime | str | None = None
    publicationUsers: list[PublicationUser] = []
    is_guest: bool = False
    bestseller_tier: int | None = None
    status: UserStatus | None = None
