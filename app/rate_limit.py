from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter — imported by main.py (for middleware registration) and by
# routers (for `@limiter.limit(...)` decorators). One instance => one storage
# backend, so limits aren't double-counted per import path.
limiter = Limiter(key_func=get_remote_address)
