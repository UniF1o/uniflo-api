"""Concrete portal adapters + the registry that resolves one by slug.

Each adapter is one module here (e.g. `uj.py`) defining a `UniversityAdapter`
subclass plus its portal field schema. The runtime and exception taxonomy are
shared, so an adapter module only adds portal-specific walkthrough logic.

`get_adapter(slug)` is how the runtime dispatch (background.py) turns a
`universities.slug` into a fresh adapter instance. Only UJ exists today.
"""

from typing import Optional
from uuid import UUID

from app.automation.adapters.uj import UJAdapter
from app.automation.base import UniversityAdapter

# Add new portals here as they're built. The `universities` table keys on `id`
# (no slug column), so the runtime resolves by university_id; `slug` is the
# stable handle used for field-mapping + logging.
_ADAPTER_CLASSES: tuple[type[UniversityAdapter], ...] = (UJAdapter,)
_BY_SLUG = {a.slug: a for a in _ADAPTER_CLASSES}
_BY_UNIVERSITY_ID = {a.university_id: a for a in _ADAPTER_CLASSES}


def get_adapter(slug: str) -> Optional[UniversityAdapter]:
    """Fresh adapter instance for `slug`, or None if none is registered."""
    cls = _BY_SLUG.get(slug)
    return cls() if cls else None


def get_adapter_for_university(university_id: UUID) -> Optional[UniversityAdapter]:
    """Fresh adapter instance for a `universities.id`, or None if that
    university's portal automation isn't built yet."""
    cls = _BY_UNIVERSITY_ID.get(university_id)
    return cls() if cls else None


def registered_slugs() -> frozenset[str]:
    return frozenset(_BY_SLUG)


__all__ = [
    "UJAdapter",
    "get_adapter",
    "get_adapter_for_university",
    "registered_slugs",
]
