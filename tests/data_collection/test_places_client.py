from decimal import Decimal

import httpx
import pytest
from tenacity import wait_none

from review_removal_tracker.data_collection.places_client import (
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
    assert request.headers["X-Goog-FieldMask"] == PLACE_DETAILS_FIELDS


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
