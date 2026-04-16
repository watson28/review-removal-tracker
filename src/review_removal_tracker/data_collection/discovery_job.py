import logging
from dataclasses import dataclass

from sqlalchemy import Connection

from review_removal_tracker.data_collection.places_client import PlacesClient
from review_removal_tracker.db.crud.businesses import upsert_business
from review_removal_tracker.db.models import Business

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryJobResult:
    total_queries: int = 0
    upserted: int = 0
    errors: int = 0


def run_discovery_job(
    conn: Connection,
    client: PlacesClient,
    queries: list[tuple[str, str]],
    city_name: str = "Berlin",
) -> DiscoveryJobResult:
    result = DiscoveryJobResult(total_queries=len(queries))

    for category, district in queries:
        try:
            text_query = f"{category} in {district}, {city_name}"
            places = client.search_text(text_query)

            for place in places:
                upsert_business(conn, Business(
                    place_id=place.place_id,
                    name=place.name,
                    category=place.primary_type or category,
                    district=district,
                    lat=place.lat,
                    lng=place.lng,
                ))
                result.upserted += 1

        except Exception:
            logger.exception("Error running discovery for %s in %s", category, district)
            result.errors += 1

    return result
