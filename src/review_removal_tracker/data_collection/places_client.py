import logging
from dataclasses import dataclass
from decimal import Decimal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

logger = logging.getLogger(__name__)

PLACES_BASE_URL = "https://places.googleapis.com/v1"
PLACE_DETAILS_FIELDS = "places.userRatingCount,places.rating"
TEXT_SEARCH_FIELDS = "places.id,places.displayName,places.formattedAddress,places.location,places.primaryType"


class PlacesApiError(Exception):
    def __init__(self, status_code: int, place_id: str | None, detail: str) -> None:
        self.status_code = status_code
        self.place_id = place_id
        self.detail = detail
        super().__init__(f"Places API error {status_code} for {place_id!r}: {detail}")


class PlacesRateLimitError(PlacesApiError):
    def __init__(self, place_id: str | None = None) -> None:
        super().__init__(429, place_id, "rate limit exceeded after retries")


@dataclass
class PlaceDetails:
    place_id: str
    review_count: int
    rating: Decimal


@dataclass
class DiscoveredPlace:
    place_id: str
    name: str
    formatted_address: str
    lat: Decimal
    lng: Decimal
    primary_type: str | None


class PlacesClient:
    def __init__(
        self,
        api_key: str,
        http_client: httpx.Client | None = None,
        wait: wait_base | None = None,
    ) -> None:
        self._api_key = api_key
        self._http = http_client or httpx.Client()
        self._wait = wait or wait_exponential(multiplier=1, min=1, max=30)

    def get_place_details(self, place_id: str) -> PlaceDetails | None:
        def _call() -> httpx.Response:
            return self._http.get(
                f"{PLACES_BASE_URL}/places/{place_id}",
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": PLACE_DETAILS_FIELDS,
                },
            )

        retrying = retry(
            retry=retry_if_exception_type(httpx.TransportError),
            wait=self._wait,
            stop=stop_after_attempt(4),
            reraise=True,
        )
        response: httpx.Response = retrying(_call)()

        if response.status_code == 404:
            return None

        if response.status_code == 429:
            raise PlacesRateLimitError(place_id)

        if response.status_code != 200:
            raise PlacesApiError(response.status_code, place_id, response.text)

        data = response.json()
        return PlaceDetails(
            place_id=place_id,
            review_count=int(data.get("userRatingCount", 0)),
            rating=Decimal(str(data.get("rating", 0))),
        )

    def search_text(self, text_query: str, max_results: int = 20) -> list[DiscoveredPlace]:
        results: list[DiscoveredPlace] = []
        next_page_token: str | None = None

        while len(results) < max_results:
            body: dict = {"textQuery": text_query, "languageCode": "de"}
            if next_page_token:
                body["pageToken"] = next_page_token

            def _call(b: dict = body) -> httpx.Response:
                return self._http.post(
                    f"{PLACES_BASE_URL}/places:searchText",
                    json=b,
                    headers={
                        "X-Goog-Api-Key": self._api_key,
                        "X-Goog-FieldMask": TEXT_SEARCH_FIELDS,
                    },
                )

            retrying = retry(
                retry=retry_if_exception_type(httpx.TransportError),
                wait=self._wait,
                stop=stop_after_attempt(4),
                reraise=True,
            )
            response: httpx.Response = retrying(_call)()

            if response.status_code == 429:
                raise PlacesRateLimitError()

            if response.status_code != 200:
                raise PlacesApiError(response.status_code, None, response.text)

            data = response.json()
            for place in data.get("places", []):
                location = place.get("location", {})
                results.append(DiscoveredPlace(
                    place_id=place["id"],
                    name=place.get("displayName", {}).get("text", ""),
                    formatted_address=place.get("formattedAddress", ""),
                    lat=Decimal(str(location.get("latitude", 0))),
                    lng=Decimal(str(location.get("longitude", 0))),
                    primary_type=place.get("primaryType"),
                ))

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return results[:max_results]
