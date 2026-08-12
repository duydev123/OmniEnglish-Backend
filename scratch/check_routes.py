import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app
from fastapi.routing import _IncludedRouter

for r in app.routes:
    if isinstance(r, _IncludedRouter):
        print("IncludedRouter:", r.original_router)
        print("  _effective_candidates:", type(r._effective_candidates), len(r._effective_candidates) if r._effective_candidates else None)
        # What are the elements of _effective_candidates?
        if r._effective_candidates:
            for item in r._effective_candidates:
                print("    Candidate:", item)
        break
