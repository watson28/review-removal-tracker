import pytest
from tenacity import wait_none

from review_removal_tracker.data_collection.places_client import PlacesClient


@pytest.fixture
def places_client(httpx_mock):
    import httpx
    client = PlacesClient(
        api_key="test-api-key",
        http_client=httpx.Client(),
        wait=wait_none(),
    )
    return client
