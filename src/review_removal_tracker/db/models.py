from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Business:
    place_id: str
    name: str
    category: str
    district: str
    lat: Decimal
    lng: Decimal
    first_seen: date | None = None
    is_active: bool = True
    id: int | None = None


@dataclass
class DailySnapshot:
    business_id: int
    snapshot_date: date
    review_count: int
    rating: Decimal
    id: int | None = None


@dataclass
class ComputedMetrics:
    business_id: int
    computed_date: date
    window_days: int
    gross_additions: int
    gross_removals: int
    rrr: Decimal | None
    rgr: Decimal | None
    delta_r: Decimal | None
    cri: Decimal | None
    mcs: Decimal | None
    id: int | None = None
