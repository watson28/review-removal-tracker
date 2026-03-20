from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from review_removal_tracker.data_collection.places_client import PlaceDetails
from review_removal_tracker.data_collection.snapshot_job import SnapshotJobResult, run_snapshot_job
from review_removal_tracker.db.models import Business, DailySnapshot

MODULE = "review_removal_tracker.data_collection.snapshot_job"

TODAY = date(2026, 1, 31)


def make_business(place_id: str = "ChIJ_test", id: int = 1) -> Business:
    return Business(
        id=id,
        place_id=place_id,
        name="Test",
        category="restaurant",
        district="Mitte",
        lat=Decimal("52.5"),
        lng=Decimal("13.4"),
    )


def make_snapshot(business_id: int, review_count: int, days_ago: int = 0) -> DailySnapshot:
    from datetime import timedelta
    return DailySnapshot(
        business_id=business_id,
        snapshot_date=TODAY - timedelta(days=days_ago),
        review_count=review_count,
        rating=Decimal("4.0"),
    )


def test_snapshot_job_fetches_and_upserts():
    conn = MagicMock()
    client = MagicMock()
    client.get_place_details.return_value = PlaceDetails("ChIJ_test", 100, Decimal("4.2"))

    with (
        patch(f"{MODULE}.get_active_businesses", return_value=[make_business()]),
        patch(f"{MODULE}.get_latest_snapshot", return_value=None),
        patch(f"{MODULE}.get_snapshots_for_window", return_value=[]),
        patch(f"{MODULE}.upsert_snapshot") as mock_upsert,
        patch(f"{MODULE}.deactivate_business"),
    ):
        result = run_snapshot_job(conn, client, snapshot_date=TODAY)

    assert result.fetched == 1
    assert result.total == 1
    mock_upsert.assert_called_once()


def test_snapshot_job_multiple_businesses():
    conn = MagicMock()
    client = MagicMock()
    client.get_place_details.return_value = PlaceDetails("p", 100, Decimal("4.0"))
    businesses = [make_business("p1", id=1), make_business("p2", id=2)]

    with (
        patch(f"{MODULE}.get_active_businesses", return_value=businesses),
        patch(f"{MODULE}.get_latest_snapshot", return_value=None),
        patch(f"{MODULE}.get_snapshots_for_window", return_value=[]),
        patch(f"{MODULE}.upsert_snapshot") as mock_upsert,
        patch(f"{MODULE}.deactivate_business"),
    ):
        result = run_snapshot_job(conn, client, snapshot_date=TODAY)

    assert result.fetched == 2
    assert mock_upsert.call_count == 2


def test_snapshot_job_deactivates_on_404():
    conn = MagicMock()
    client = MagicMock()
    client.get_place_details.return_value = None

    with (
        patch(f"{MODULE}.get_active_businesses", return_value=[make_business()]),
        patch(f"{MODULE}.get_latest_snapshot", return_value=None),
        patch(f"{MODULE}.get_snapshots_for_window", return_value=[]),
        patch(f"{MODULE}.upsert_snapshot"),
        patch(f"{MODULE}.deactivate_business") as mock_deactivate,
    ):
        result = run_snapshot_job(conn, client, snapshot_date=TODAY)

    assert result.deactivated == 1
    assert result.fetched == 0
    mock_deactivate.assert_called_once_with(conn, "ChIJ_test")


def test_snapshot_job_skips_inactive():
    conn = MagicMock()
    client = MagicMock()
    latest = make_snapshot(1, review_count=100, days_ago=15)
    window = [make_snapshot(1, review_count=100, days_ago=14), make_snapshot(1, review_count=100, days_ago=0)]

    with (
        patch(f"{MODULE}.get_active_businesses", return_value=[make_business()]),
        patch(f"{MODULE}.get_latest_snapshot", return_value=latest),
        patch(f"{MODULE}.get_snapshots_for_window", return_value=window),
        patch(f"{MODULE}.upsert_snapshot"),
        patch(f"{MODULE}.deactivate_business"),
    ):
        result = run_snapshot_job(conn, client, snapshot_date=TODAY, skip_inactive_days=14)

    assert result.skipped == 1
    client.get_place_details.assert_not_called()


def test_snapshot_job_does_not_skip_if_review_count_changed():
    conn = MagicMock()
    client = MagicMock()
    client.get_place_details.return_value = PlaceDetails("ChIJ_test", 110, Decimal("4.2"))
    latest = make_snapshot(1, review_count=110, days_ago=15)
    window = [make_snapshot(1, review_count=100, days_ago=14), make_snapshot(1, review_count=110, days_ago=0)]

    with (
        patch(f"{MODULE}.get_active_businesses", return_value=[make_business()]),
        patch(f"{MODULE}.get_latest_snapshot", return_value=latest),
        patch(f"{MODULE}.get_snapshots_for_window", return_value=window),
        patch(f"{MODULE}.upsert_snapshot") as mock_upsert,
        patch(f"{MODULE}.deactivate_business"),
    ):
        result = run_snapshot_job(conn, client, snapshot_date=TODAY, skip_inactive_days=14)

    assert result.skipped == 0
    assert result.fetched == 1
    mock_upsert.assert_called_once()


def test_snapshot_job_counts_errors():
    conn = MagicMock()
    client = MagicMock()
    client.get_place_details.side_effect = Exception("API failure")

    with (
        patch(f"{MODULE}.get_active_businesses", return_value=[make_business()]),
        patch(f"{MODULE}.get_latest_snapshot", return_value=None),
        patch(f"{MODULE}.get_snapshots_for_window", return_value=[]),
        patch(f"{MODULE}.upsert_snapshot"),
        patch(f"{MODULE}.deactivate_business"),
    ):
        result = run_snapshot_job(conn, client, snapshot_date=TODAY)

    assert result.errors == 1
    assert result.fetched == 0


def test_snapshot_job_result_fields():
    result = SnapshotJobResult(total=5, fetched=3, skipped=1, deactivated=1, errors=0)
    assert result.total == 5
    assert result.fetched == 3
    assert result.skipped == 1
    assert result.deactivated == 1
