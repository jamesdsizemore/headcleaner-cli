"""Engine adapters — every supported document format has an Adapter here.

Adapters implement `Adapter` (see `base.py`):
    extract(source: Path) -> dict

The dict shape is consumed by `normalize.normalize()` which produces a
`CanonicalDoc`. To add a new format: drop a module in this package,
register the adapter in `router.py`, and add a row to `docs/FORMAT_MATRIX.md`.
"""

from .base import Adapter, AdapterError

__all__ = ["Adapter", "AdapterError"]
