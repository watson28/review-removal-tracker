from pathlib import Path

import pytest

from review_removal_tracker.grid.city import CityConfig, load_city_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BERLIN_CONFIG = PROJECT_ROOT / "config" / "cities" / "berlin.toml"


@pytest.fixture
def berlin() -> CityConfig:
    return load_city_config(BERLIN_CONFIG)
