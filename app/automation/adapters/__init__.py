"""Concrete portal adapters + the registry that resolves one by slug.

Each adapter is one module here (e.g. `uj.py`, `uct.py`) defining a
`UniversityAdapter` subclass plus its portal field schema. The runtime and
exception taxonomy are shared, so an adapter module only adds portal-specific
walkthrough logic.

Resolution: `get_adapter(slug)` by slug; `get_adapter_for_university(id)` for
adapters with a pinned `universities.id` (UJ); `slug_for_website(url)` maps a
university row's website domain to a slug — the robust path, since the seed
script generates row ids with uuid4 (nothing stable to pin).
"""

from typing import Optional
from uuid import UUID

from app.automation.adapters.uct import UCTAdapter
from app.automation.adapters.uj import UJAdapter
from app.automation.adapters.up import UPAdapter
from app.automation.base import UniversityAdapter

# Add new portals here as they're built.
_ADAPTER_CLASSES: tuple[type[UniversityAdapter], ...] = (
    UJAdapter,
    UCTAdapter,
    UPAdapter,
)
_BY_SLUG = {a.slug: a for a in _ADAPTER_CLASSES}
_BY_UNIVERSITY_ID = {a.university_id: a for a in _ADAPTER_CLASSES}

# University website domain → adapter slug (universities.website is seeded and
# stable; row ids are not).
_DOMAIN_SLUGS = {
    "uj.ac.za": "uj",
    "uct.ac.za": "uct",
    "wits.ac.za": "wits",
    "up.ac.za": "up",
}


def slug_for_website(website: Optional[str]) -> Optional[str]:
    """Adapter slug for a `universities.website` URL, or None."""
    if not website:
        return None
    host = website.lower().split("//")[-1].split("/")[0]
    for domain, slug in _DOMAIN_SLUGS.items():
        if host == domain or host.endswith("." + domain):
            return slug
    return None


def get_adapter(slug: str) -> Optional[UniversityAdapter]:
    """Fresh adapter instance for `slug`, or None if none is registered."""
    cls = _BY_SLUG.get(slug)
    return cls() if cls else None


def get_adapter_for_university(university_id: UUID) -> Optional[UniversityAdapter]:
    """Fresh adapter instance for a pinned `universities.id`, or None. Prefer
    `slug_for_website` resolution (see background.py) — only UJ has a pinned id."""
    cls = _BY_UNIVERSITY_ID.get(university_id)
    return cls() if cls else None


def registered_slugs() -> frozenset[str]:
    return frozenset(_BY_SLUG)


__all__ = [
    "UCTAdapter",
    "UJAdapter",
    "UPAdapter",
    "get_adapter",
    "get_adapter_for_university",
    "registered_slugs",
    "slug_for_website",
]
