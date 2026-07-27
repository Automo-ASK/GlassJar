from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# In-memory limiter — fine at single-instance scale. Behind a multi-instance
# load balancer this needs a shared backend (e.g. Redis) or each instance
# enforces its own quota, letting an attacker multiply their effective limit
# by the instance count.
#
# Disabled under pytest (ENV=test): TestClient calls every route from the same
# synthetic client IP, so the suite's own traffic would trip the limit.
limiter = Limiter(key_func=get_remote_address, enabled=settings.env != "test")
