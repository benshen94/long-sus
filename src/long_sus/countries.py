from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountrySpec:
    slug: str
    name: str
    location_id: int
    cache_slug: str
    default_analytic_preset_id: str


SUPPORTED_COUNTRIES = (
    CountrySpec(
        slug="usa",
        name="USA",
        location_id=840,
        cache_slug="usa",
        default_analytic_preset_id="usa_period_2024_both_hazard",
    ),
    CountrySpec(
        slug="world",
        name="World",
        location_id=900,
        cache_slug="world",
        default_analytic_preset_id="world_period_2024_both_hazard",
    ),
    CountrySpec(
        slug="italy",
        name="Italy",
        location_id=380,
        cache_slug="italy",
        default_analytic_preset_id="italy_period_2024_both_hazard",
    ),
    CountrySpec(
        slug="south_africa",
        name="South Africa",
        location_id=710,
        cache_slug="south_africa",
        default_analytic_preset_id="south_africa_period_2024_both_hazard",
    ),
    CountrySpec(
        slug="uganda",
        name="Uganda",
        location_id=800,
        cache_slug="uganda",
        default_analytic_preset_id="uganda_period_2024_both_hazard",
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
