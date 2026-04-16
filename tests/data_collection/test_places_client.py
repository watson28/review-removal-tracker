from decimal import Decimal

import httpx
import pytest
from tenacity import wait_none

from review_removal_tracker.data_collection.places_client import (
    NEARBY_SEARCH_FIELDS,
    PLACE_DETAILS_FIELDS,
    TEXT_SEARCH_FIELDS,
    PlacesApiError,
    PlacesClient,
    PlacesRateLimitError,
)


def test_get_place_details_success(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        json={"userRatingCount": 523, "rating": 4.2},
    )
    result = places_client.get_place_details("ChIJ_abc123")
    assert result is not None
    assert result.place_id == "ChIJ_abc123"
    assert result.review_count == 523
    assert result.rating == Decimal("4.2")


def test_get_place_details_sets_field_mask(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        json={"userRatingCount": 100, "rating": 4.0},
    )
    places_client.get_place_details("ChIJ_abc123")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Goog-FieldMask"] == "userRatingCount,rating"


def test_get_place_details_sets_api_key(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        json={"userRatingCount": 100, "rating": 4.0},
    )
    places_client.get_place_details("ChIJ_abc123")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Goog-Api-Key"] == "test-api-key"


def test_get_place_details_404_returns_none(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_gone",
        status_code=404,
    )
    result = places_client.get_place_details("ChIJ_gone")
    assert result is None


def test_get_place_details_429_raises_rate_limit(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        status_code=429,
    )
    with pytest.raises(PlacesRateLimitError):
        places_client.get_place_details("ChIJ_abc123")


def test_get_place_details_retries_on_transport_error(httpx_mock):
    client = PlacesClient(
        api_key="test-key",
        http_client=httpx.Client(),
        wait=wait_none(),
    )
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_retry",
        json={"userRatingCount": 10, "rating": 3.5},
    )
    result = client.get_place_details("ChIJ_retry")
    assert result is not None
    assert result.review_count == 10


def test_get_place_details_non_404_error_raises(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        status_code=500,
        text="Internal Server Error",
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.get_place_details("ChIJ_abc123")
    assert exc_info.value.status_code == 500


def test_search_text_success(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={
            "places": [
                {
                    "id": "ChIJ_rest1",
                    "displayName": {"text": "Pizza Roma"},
                    "formattedAddress": "Unter den Linden 1, Berlin",
                    "location": {"latitude": 52.5, "longitude": 13.4},
                    "primaryType": "restaurant",
                },
                {
                    "id": "ChIJ_rest2",
                    "displayName": {"text": "Burger Haus"},
                    "formattedAddress": "Friedrichstr 10, Berlin",
                    "location": {"latitude": 52.51, "longitude": 13.39},
                    "primaryType": "restaurant",
                },
            ]
        },
    )
    results = places_client.search_text("restaurant in Mitte, Berlin")
    assert len(results) == 2
    assert results[0].place_id == "ChIJ_rest1"
    assert results[0].name == "Pizza Roma"
    assert results[0].lat == Decimal("52.5")
    assert results[0].primary_type == "restaurant"


def test_search_text_sets_field_mask(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={"places": []},
    )
    places_client.search_text("restaurant in Mitte, Berlin")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Goog-FieldMask"] == TEXT_SEARCH_FIELDS


def test_search_text_request_body(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={"places": []},
    )
    places_client.search_text("restaurant in Mitte, Berlin")
    request = httpx_mock.get_request()
    assert request is not None
    import json
    body = json.loads(request.content)
    assert body["textQuery"] == "restaurant in Mitte, Berlin"
    assert body["languageCode"] == "de"


def test_search_text_primary_type_none(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={
            "places": [
                {
                    "id": "ChIJ_notype",
                    "displayName": {"text": "Some Place"},
                    "formattedAddress": "Somewhere",
                    "location": {"latitude": 52.5, "longitude": 13.4},
                }
            ]
        },
    )
    results = places_client.search_text("restaurant in Mitte, Berlin")
    assert results[0].primary_type is None


def test_search_text_429_raises_rate_limit(httpx_mock, places_client):
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        status_code=429,
    )
    with pytest.raises(PlacesRateLimitError):
        places_client.search_text("restaurant in Mitte, Berlin")


# --- Pydantic validation tests ---

def test_get_place_details_invalid_response_shape_raises(httpx_mock, places_client):
    # userRatingCount must be an int — a non-coercible string should fail validation
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        json={"userRatingCount": "not_a_number", "rating": 4.2},
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.get_place_details("ChIJ_abc123")
    assert exc_info.value.status_code == 200
    assert "unexpected response shape" in str(exc_info.value)


def test_get_place_details_missing_fields_uses_defaults(httpx_mock, places_client):
    # Empty response body — both fields should fall back to their defaults (0)
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        json={},
    )
    result = places_client.get_place_details("ChIJ_abc123")
    assert result is not None
    assert result.review_count == 0
    assert result.rating == Decimal("0.0")


def test_get_place_details_extra_fields_are_ignored(httpx_mock, places_client):
    # Google may return additional fields not in the field mask — should be ignored
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places/ChIJ_abc123",
        json={"userRatingCount": 200, "rating": 4.5, "name": "Some Place", "unknownField": True},
    )
    result = places_client.get_place_details("ChIJ_abc123")
    assert result is not None
    assert result.review_count == 200


def test_search_text_invalid_response_shape_raises(httpx_mock, places_client):
    # places must be a list — an object should fail validation
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={"places": "not_a_list"},
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.search_text("restaurant in Mitte, Berlin")
    assert exc_info.value.status_code == 200
    assert "unexpected response shape" in str(exc_info.value)


def test_search_text_place_missing_id_raises(httpx_mock, places_client):
    # id is required on each place entry — missing it should fail validation
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={"places": [{"displayName": {"text": "No ID Place"}}]},
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.search_text("restaurant in Mitte, Berlin")
    assert "unexpected response shape" in str(exc_info.value)


def test_search_text_missing_optional_fields_uses_defaults(httpx_mock, places_client):
    # Only id is required — all other fields should fall back to defaults
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={"places": [{"id": "ChIJ_minimal"}]},
    )
    results = places_client.search_text("restaurant in Mitte, Berlin")
    assert len(results) == 1
    assert results[0].place_id == "ChIJ_minimal"
    assert results[0].name == ""
    assert results[0].formatted_address == ""
    assert results[0].lat == Decimal("0.0")
    assert results[0].lng == Decimal("0.0")
    assert results[0].primary_type is None


def test_search_text_invalid_location_type_raises(httpx_mock, places_client):
    # location.latitude must be a float — a string should fail validation
    httpx_mock.add_response(
        url="https://places.googleapis.com/v1/places:searchText",
        json={"places": [{"id": "ChIJ_bad", "location": {"latitude": "north", "longitude": 13.4}}]},
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.search_text("restaurant in Mitte, Berlin")
    assert "unexpected response shape" in str(exc_info.value)


# --- search_nearby tests ---

NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"


def test_search_nearby_success(httpx_mock, places_client):
    httpx_mock.add_response(
        url=NEARBY_URL,
        json={
            "places": [
                {
                    "id": "ChIJ_n1",
                    "displayName": {"text": "Bistro Alpha"},
                    "rating": 4.3,
                    "userRatingCount": 812,
                    "location": {"latitude": 52.52, "longitude": 13.405},
                    "primaryType": "restaurant",
                },
                {
                    "id": "ChIJ_n2",
                    "displayName": {"text": "Cafe Beta"},
                    "rating": 4.7,
                    "userRatingCount": 145,
                    "location": {"latitude": 52.521, "longitude": 13.404},
                    "primaryType": "cafe",
                },
            ]
        },
    )
    results = places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    assert len(results) == 2
    assert results[0].place_id == "ChIJ_n1"
    assert results[0].name == "Bistro Alpha"
    assert results[0].review_count == 812
    assert results[0].rating == Decimal("4.3")
    assert results[0].lat == Decimal("52.52")
    assert results[0].lng == Decimal("13.405")
    assert results[0].primary_type == "restaurant"
    assert results[1].review_count == 145


def test_search_nearby_sets_field_mask(httpx_mock, places_client):
    httpx_mock.add_response(url=NEARBY_URL, json={"places": []})
    places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Goog-FieldMask"] == NEARBY_SEARCH_FIELDS


def test_search_nearby_sets_api_key(httpx_mock, places_client):
    httpx_mock.add_response(url=NEARBY_URL, json={"places": []})
    places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Goog-Api-Key"] == "test-api-key"


def test_search_nearby_request_body(httpx_mock, places_client):
    httpx_mock.add_response(url=NEARBY_URL, json={"places": []})
    places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"], max_results=20,
    )
    request = httpx_mock.get_request()
    assert request is not None
    import json
    body = json.loads(request.content)
    assert body["includedTypes"] == ["restaurant"]
    assert body["maxResultCount"] == 20
    assert body["locationRestriction"]["circle"]["center"] == {
        "latitude": 52.52, "longitude": 13.405,
    }
    assert body["locationRestriction"]["circle"]["radius"] == 500.0
    assert body["languageCode"] == "de"


def test_search_nearby_429_raises_rate_limit(httpx_mock, places_client):
    httpx_mock.add_response(url=NEARBY_URL, status_code=429)
    with pytest.raises(PlacesRateLimitError):
        places_client.search_nearby(
            lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
        )


def test_search_nearby_non_200_error_raises(httpx_mock, places_client):
    httpx_mock.add_response(url=NEARBY_URL, status_code=500, text="boom")
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.search_nearby(
            lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
        )
    assert exc_info.value.status_code == 500


def test_search_nearby_empty_response(httpx_mock, places_client):
    # Pruned/empty cells legitimately return no places — must succeed, not raise.
    httpx_mock.add_response(url=NEARBY_URL, json={})
    results = places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    assert results == []


def test_search_nearby_missing_optional_fields_uses_defaults(httpx_mock, places_client):
    httpx_mock.add_response(
        url=NEARBY_URL,
        json={"places": [{"id": "ChIJ_minimal"}]},
    )
    results = places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    assert len(results) == 1
    assert results[0].place_id == "ChIJ_minimal"
    assert results[0].name == ""
    assert results[0].review_count == 0
    assert results[0].rating == Decimal("0.0")
    assert results[0].lat == Decimal("0.0")
    assert results[0].lng == Decimal("0.0")
    assert results[0].primary_type is None


def test_search_nearby_place_missing_id_raises(httpx_mock, places_client):
    httpx_mock.add_response(
        url=NEARBY_URL,
        json={"places": [{"displayName": {"text": "No ID"}}]},
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.search_nearby(
            lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
        )
    assert "unexpected response shape" in str(exc_info.value)


def test_search_nearby_invalid_rating_type_raises(httpx_mock, places_client):
    httpx_mock.add_response(
        url=NEARBY_URL,
        json={"places": [{"id": "ChIJ_x", "rating": "great"}]},
    )
    with pytest.raises(PlacesApiError) as exc_info:
        places_client.search_nearby(
            lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
        )
    assert "unexpected response shape" in str(exc_info.value)


def test_search_nearby_extra_fields_ignored(httpx_mock, places_client):
    httpx_mock.add_response(
        url=NEARBY_URL,
        json={"places": [
            {
                "id": "ChIJ_extra",
                "displayName": {"text": "Place"},
                "rating": 4.1,
                "userRatingCount": 50,
                "location": {"latitude": 52.5, "longitude": 13.4},
                "primaryType": "restaurant",
                "businessStatus": "OPERATIONAL",
                "unknownField": True,
            }
        ]},
    )
    results = places_client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    assert len(results) == 1
    assert results[0].review_count == 50


def test_search_nearby_retries_on_transport_error(httpx_mock):
    client = PlacesClient(
        api_key="test-key",
        http_client=httpx.Client(),
        wait=wait_none(),
    )
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    httpx_mock.add_response(
        url=NEARBY_URL,
        json={"places": [{"id": "ChIJ_ok", "rating": 4.0, "userRatingCount": 12}]},
    )
    results = client.search_nearby(
        lat=52.52, lng=13.405, radius_m=500.0, included_types=["restaurant"],
    )
    assert len(results) == 1
    assert results[0].place_id == "ChIJ_ok"
