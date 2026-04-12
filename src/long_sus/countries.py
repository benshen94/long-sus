from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountrySpec:
    slug: str
    name: str
    location_id: int
    cache_slug: str
    default_analytic_preset_id: str
    iso3: str
    continent: str


SUPPORTED_COUNTRIES = (
    CountrySpec(
        slug="usa",
        name="USA",
        location_id=840,
        cache_slug="usa",
        default_analytic_preset_id="usa_period_2024_both_hazard",
        iso3="USA",
        continent="North America",
    ),
    CountrySpec(
        slug="world",
        name="World",
        location_id=900,
        cache_slug="world",
        default_analytic_preset_id="world_period_2024_both_hazard",
        iso3="OWID_WRL",
        continent="Global",
    ),
    CountrySpec(
        slug="china",
        name="China",
        location_id=156,
        cache_slug="china",
        default_analytic_preset_id="china_period_2024_both_hazard",
        iso3="CHN",
        continent="Asia",
    ),
    CountrySpec(
        slug="india",
        name="India",
        location_id=356,
        cache_slug="india",
        default_analytic_preset_id="india_period_2024_both_hazard",
        iso3="IND",
        continent="Asia",
    ),
    CountrySpec(
        slug="israel",
        name="Israel",
        location_id=376,
        cache_slug="israel",
        default_analytic_preset_id="israel_period_2024_both_hazard",
        iso3="ISR",
        continent="Asia",
    ),
    CountrySpec(
        slug="italy",
        name="Italy",
        location_id=380,
        cache_slug="italy",
        default_analytic_preset_id="italy_period_2024_both_hazard",
        iso3="ITA",
        continent="Europe",
    ),
    CountrySpec(
        slug="brazil",
        name="Brazil",
        location_id=76,
        cache_slug="brazil",
        default_analytic_preset_id="brazil_period_2024_both_hazard",
        iso3="BRA",
        continent="South America",
    ),
    CountrySpec(
        slug="nigeria",
        name="Nigeria",
        location_id=566,
        cache_slug="nigeria",
        default_analytic_preset_id="nigeria_period_2024_both_hazard",
        iso3="NGA",
        continent="Africa",
    ),
    CountrySpec(
        slug="south_africa",
        name="South Africa",
        location_id=710,
        cache_slug="south_africa",
        default_analytic_preset_id="south_africa_period_2024_both_hazard",
        iso3="ZAF",
        continent="Africa",
    ),
    CountrySpec(
        slug="uganda",
        name="Uganda",
        location_id=800,
        cache_slug="uganda",
        default_analytic_preset_id="uganda_period_2024_both_hazard",
        iso3="UGA",
        continent="Africa",
    ),
)


def _normalize_country_key(value: str) -> str:
    safe = value.strip().lower().replace("-", "_")
    return "_".join(part for part in safe.replace(" ", "_").split("_") if part)


def list_supported_country_specs() -> list[CountrySpec]:
    return list(SUPPORTED_COUNTRIES)


def list_supported_countries() -> list[dict[str, object]]:
    return [
        {
            "slug": country.slug,
            "country": country.name,
            "location_id": country.location_id,
            "cache_slug": country.cache_slug,
            "default_analytic_preset_id": country.default_analytic_preset_id,
            "iso3": country.iso3,
            "continent": country.continent,
        }
        for country in SUPPORTED_COUNTRIES
    ]


def get_country_spec(country: str) -> CountrySpec:
    normalized = _normalize_country_key(country)

    for entry in SUPPORTED_COUNTRIES:
        if normalized in {entry.slug, _normalize_country_key(entry.name)}:
            return entry

    supported = ", ".join(entry.name for entry in SUPPORTED_COUNTRIES)
    raise KeyError(f"Unsupported country: {country}. Supported countries: {supported}")
