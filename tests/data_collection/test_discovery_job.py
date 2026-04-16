from decimal import Decimal
from unittest.mock import MagicMock, patch

from review_removal_tracker.data_collection.discovery_job import run_discovery_job
from review_removal_tracker.data_collection.places_client import DiscoveredPlace

MODULE = "review_removal_tracker.data_collection.discovery_job"


def make_place(place_id: str = "ChIJ_p1", primary_type: str | None = "restaurant") -> DiscoveredPlace:
    return DiscoveredPlace(
        place_id=place_id,
        name="Test Place",
        formatted_address="Teststr. 1, Berlin",
        lat=Decimal("52.5"),
        lng=Decimal("13.4"),
        primary_type=primary_type,
    )


def test_discovery_job_upserts_found_businesses():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = [make_place("p1"), make_place("p2"), make_place("p3")]

    with patch(f"{MODULE}.upsert_business") as mock_upsert:
        result = run_discovery_job(conn, client, [("restaurant", "Mitte")])

    assert result.upserted == 3
    assert mock_upsert.call_count == 3


def test_discovery_job_maps_primary_type_to_category():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = [make_place("p1", primary_type="italian_restaurant")]

    with patch(f"{MODULE}.upsert_business") as mock_upsert:
        run_discovery_job(conn, client, [("restaurant", "Mitte")])

    business = mock_upsert.call_args[0][1]
    assert business.category == "italian_restaurant"


def test_discovery_job_falls_back_to_query_category_when_primary_type_none():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = [make_place("p1", primary_type=None)]

    with patch(f"{MODULE}.upsert_business") as mock_upsert:
        run_discovery_job(conn, client, [("restaurant", "Mitte")])

    business = mock_upsert.call_args[0][1]
    assert business.category == "restaurant"


def test_discovery_job_sets_district_from_query():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = [make_place("p1")]

    with patch(f"{MODULE}.upsert_business") as mock_upsert:
        run_discovery_job(conn, client, [("hotel", "Kreuzberg")])

    business = mock_upsert.call_args[0][1]
    assert business.district == "Kreuzberg"


def test_discovery_job_multiple_queries():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = [make_place("p1"), make_place("p2")]

    with patch(f"{MODULE}.upsert_business") as mock_upsert:
        result = run_discovery_job(conn, client, [("restaurant", "Mitte"), ("hotel", "Kreuzberg")])

    assert result.total_queries == 2
    assert result.upserted == 4
    assert mock_upsert.call_count == 4


def test_discovery_job_does_not_call_place_details():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = [make_place()]

    with patch(f"{MODULE}.upsert_business"):
        run_discovery_job(conn, client, [("restaurant", "Mitte")])

    client.get_place_details.assert_not_called()


def test_discovery_job_counts_errors():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.side_effect = Exception("API failure")

    with patch(f"{MODULE}.upsert_business"):
        result = run_discovery_job(conn, client, [("restaurant", "Mitte")])

    assert result.errors == 1
    assert result.upserted == 0


def test_discovery_job_query_text_format_defaults_to_berlin():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = []

    run_discovery_job(conn, client, [("hotel", "Prenzlauer Berg")])

    client.search_text.assert_called_once_with("hotel in Prenzlauer Berg, Berlin")


def test_discovery_job_query_text_format_uses_city_name():
    conn = MagicMock()
    client = MagicMock()
    client.search_text.return_value = []

    run_discovery_job(conn, client, [("cafe", "Eixample")], city_name="Barcelona")

    client.search_text.assert_called_once_with("cafe in Eixample, Barcelona")
