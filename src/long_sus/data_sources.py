from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
import time
import subprocess

import pandas as pd

from .config import (
    DEFAULT_BASE_YEAR,
    DEFAULT_FINAL_YEAR,
    RAW_HFD_DIR,
    RAW_HMD_DIR,
    RAW_WPP_DIR,
    SEX_ID_TO_NAME,
    WPP_API_BASE,
    WPP_INDICATORS,
    WPP_USA_LOCATION_ID,
    WPP_VARIANTS,
    WPP_WORLD_LOCATION_ID,
)
from .countries import CountrySpec, get_country_spec
from .external_paths import HMD_PERIOD_FILES


UNVERIFIED_SSL_CONTEXT = ssl._create_unverified_context()


@dataclass
class WppBundle:
    population: dict[str, pd.DataFrame]
    fertility: dict[str, pd.DataFrame]
    mortality: pd.DataFrame
    sex_ratio_at_birth: dict[str, pd.DataFrame]
    net_migration: dict[str, pd.DataFrame]
    metadata: dict[str, dict[str, Any]]


class WppApiClient:
    def __init__(self, base_url: str = WPP_API_BASE) -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_json(self, path: str) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(6):
            try:
                result = subprocess.run(
                    ["curl", "-ks", url],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=120,
                )
                return json.loads(result.stdout)
            except subprocess.CalledProcessError as error:
                last_error = error
                if attempt == 5:
                    raise
            except subprocess.TimeoutExpired as error:
                last_error = error
                if attempt == 5:
                    raise
            except json.JSONDecodeError as error:
                last_error = error
                if attempt == 5:
                    raise
            except HTTPError as error:
                last_error = error
                if error.code < 500 or attempt == 5:
                    raise
            except URLError as error:
                last_error = error
                if attempt == 5:
                    raise

            time.sleep(1.5 * (attempt + 1))

        if last_error is None:
            raise RuntimeError(f"Failed to fetch URL: {url}")
        raise last_error

    def fetch_indicator_metadata(self, indicator_id: int) -> dict[str, Any]:
        records = self.fetch_json(f"indicators/{indicator_id}")
        if not records:
            raise ValueError(f"No metadata returned for indicator {indicator_id}")

        return records[0]

    def fetch_indicator_records(
        self,
        indicator_id: int,
        years: list[int],
        ages: list[int],
        sexes: list[int],
        variant_id: int,
        location_id: int = WPP_USA_LOCATION_ID,
        categories: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        if not categories:
            categories = [0]
        ages_arg = ",".join(str(age) for age in ages)
        sexes_arg = ",".join(str(sex) for sex in sexes)
        categories_arg = ",".join(str(category) for category in categories)
        records: list[dict[str, Any]] = []

        for index in range(0, len(years), 10):
            year_chunk = years[index : index + 10]
            chunk_records = self._fetch_indicator_chunk(
                indicator_id=indicator_id,
                years=year_chunk,
                ages_arg=ages_arg,
                sexes_arg=sexes_arg,
                categories_arg=categories_arg,
                variant_id=variant_id,
                location_id=location_id,
            )
            records.extend(chunk_records)

        return records

    def _fetch_indicator_chunk(
        self,
        *,
        indicator_id: int,
        years: list[int],
        ages_arg: str,
        sexes_arg: str,
        categories_arg: str,
        variant_id: int,
        location_id: int,
    ) -> list[dict[str, Any]]:
        years_arg = ",".join(str(year) for year in years)
        path = (
            "data/indicators/"
            f"{indicator_id}/locations/{location_id}/years/{years_arg}"
            f"/vars/{variant_id}/ages/{ages_arg}/sexes/{sexes_arg}/cats/{categories_arg}"
        )
        response = self.fetch_json(path)
        if isinstance(response, list):
            return response

        fallback_records: list[dict[str, Any]] = []
        for year in years:
            single_year_path = (
                "data/indicators/"
                f"{indicator_id}/locations/{location_id}/years/{year}"
                f"/vars/{variant_id}/ages/{ages_arg}/sexes/{sexes_arg}/cats/{categories_arg}"
            )
            year_response = self.fetch_json(single_year_path)
            if isinstance(year_response, dict):
                message = year_response.get("Message", "Unknown WPP API response")
                raise ValueError(
                    f"WPP API returned a non-list payload for indicator {indicator_id}, year {year}: {message}"
                )
            fallback_records.extend(year_response)

        return fallback_records


def ensure_data_dirs() -> None:
    directories = [RAW_WPP_DIR, RAW_HMD_DIR, RAW_HFD_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def _wpp_cache_dir(cache_slug: str) -> Path:
    if cache_slug == "usa":
        return RAW_WPP_DIR
    return RAW_WPP_DIR / cache_slug


def _csv_covers_year_range(
    path: Path,
    start_year: int,
    end_year: int,
) -> bool:
    if not path.exists():
        return False

    frame = pd.read_csv(path, usecols=["year"])
    if frame.empty:
        return False

    min_year = int(frame["year"].min())
    max_year = int(frame["year"].max())
    return min_year <= start_year and max_year >= end_year


def _cache_complete(start_year: int, end_year: int) -> bool:
    return _cache_complete_for_dir(RAW_WPP_DIR, start_year, end_year)


def _cache_complete_for_dir(cache_dir: Path, start_year: int, end_year: int) -> bool:
    expected_paths = [cache_dir / "mortality_medium.csv"]
    for variant_name in WPP_VARIANTS:
        expected_paths.extend(
            [
                cache_dir / f"population_{variant_name}.csv",
                cache_dir / f"fertility_{variant_name}.csv",
                cache_dir / f"sex_ratio_at_birth_{variant_name}.csv",
                cache_dir / f"net_migration_{variant_name}.csv",
            ]
        )

    return all(_csv_covers_year_range(path, start_year, end_year) for path in expected_paths)


def _normalize_population(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame

    frame = frame.rename(columns={"timeLabel": "year", "ageLabel": "age", "value": "population"})
    frame["year"] = frame["year"].astype(int)
    frame["age"] = frame["age"].replace({"100+": "100"}).astype(int)
    frame["sex"] = frame["sexId"].map(SEX_ID_TO_NAME)
    columns = ["year", "sex", "age", "population"]
    return frame[columns].sort_values(columns[:-1]).reset_index(drop=True)


def _normalize_mortality(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame

    frame = frame.rename(columns={"timeLabel": "year", "ageLabel": "age", "value": "mx"})
    frame["year"] = frame["year"].astype(int)
    frame["age"] = frame["age"].replace({"100+": "100"}).astype(int)
    frame["sex"] = frame["sexId"].map(SEX_ID_TO_NAME)
    columns = ["year", "sex", "age", "mx"]
    return frame[columns].sort_values(columns[:-1]).reset_index(drop=True)


def _normalize_fertility(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame

    frame = frame.rename(columns={"timeLabel": "year", "ageLabel": "age", "value": "asfr"})
    frame["year"] = frame["year"].astype(int)
    frame["age"] = frame["age"].astype(int)
    columns = ["year", "age", "asfr"]
    return frame[columns].sort_values(columns).reset_index(drop=True)


def _normalize_total_indicator(records: list[dict[str, Any]], value_name: str) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame

    frame = frame.rename(columns={"timeLabel": "year", "value": value_name})
    frame["year"] = frame["year"].astype(int)
    return frame[["year", value_name]].sort_values("year").reset_index(drop=True)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _get_variant_metadata(metadata: dict[str, Any], variant_id: int) -> dict[str, Any]:
    variants = metadata["availableDimensions"]["variants"]
    for variant in variants:
        if variant["dimensionId"] == variant_id:
            return variant

    raise KeyError(f"Variant {variant_id} not found in metadata")


def _get_age_ids(metadata: dict[str, Any]) -> list[int]:
    return [item["dimensionId"] for item in metadata["availableDimensions"]["ages"]]


def _get_sex_ids(metadata: dict[str, Any], *, include_both: bool = False) -> list[int]:
    values = metadata["availableDimensions"]["sexes"]
    ids = [item["dimensionId"] for item in values]
    if include_both:
        return ids

    return [sex_id for sex_id in ids if sex_id in (1, 2)]


def download_wpp_bundle(
    *,
    location_id: int,
    cache_slug: str,
    start_year: int = DEFAULT_BASE_YEAR,
    end_year: int = DEFAULT_FINAL_YEAR,
    force: bool = False,
) -> WppBundle:
    ensure_data_dirs()
    cache_dir = _wpp_cache_dir(cache_slug)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not force and _cache_complete_for_dir(cache_dir, start_year, end_year):
        return load_cached_wpp_bundle(cache_slug=cache_slug)

    client = WppApiClient()
    years = list(range(start_year, end_year + 1))
    metadata: dict[str, dict[str, Any]] = {}

    population_frames: dict[str, pd.DataFrame] = {}
    fertility_frames: dict[str, pd.DataFrame] = {}
    srb_frames: dict[str, pd.DataFrame] = {}
    migration_frames: dict[str, pd.DataFrame] = {}

    for key, indicator_id in WPP_INDICATORS.items():
        metadata[key] = client.fetch_indicator_metadata(indicator_id)
        _write_json(cache_dir / f"{key}_metadata.json", metadata[key])

    population_meta = metadata["population"]
    fertility_meta = metadata["fertility"]
    mortality_meta = metadata["mortality"]
    srb_meta = metadata["sex_ratio_at_birth"]
    migration_meta = metadata["net_migration"]

    population_age_ids = _get_age_ids(population_meta)
    population_sex_ids = _get_sex_ids(population_meta)

    fertility_age_ids = _get_age_ids(fertility_meta)
    fertility_sex_ids = [3]

    mortality_age_ids = _get_age_ids(mortality_meta)
    mortality_sex_ids = _get_sex_ids(mortality_meta)

    total_age_ids = [188]
    both_sex_ids = [3]

    for variant_name, variant_id in WPP_VARIANTS.items():
        population_csv = RAW_WPP_DIR / f"population_{variant_name}.csv"
        fertility_csv = cache_dir / f"fertility_{variant_name}.csv"
        srb_csv = cache_dir / f"sex_ratio_at_birth_{variant_name}.csv"
        migration_csv = cache_dir / f"net_migration_{variant_name}.csv"
        population_csv = cache_dir / f"population_{variant_name}.csv"

        if (
            not force
            and population_csv.exists()
            and fertility_csv.exists()
            and srb_csv.exists()
            and migration_csv.exists()
        ):
            population_frames[variant_name] = pd.read_csv(population_csv)
            fertility_frames[variant_name] = pd.read_csv(fertility_csv)
            srb_frames[variant_name] = pd.read_csv(srb_csv)
            migration_frames[variant_name] = pd.read_csv(migration_csv)
            continue

        fertility_records = client.fetch_indicator_records(
            indicator_id=WPP_INDICATORS["fertility"],
            years=years,
            ages=fertility_age_ids,
            sexes=fertility_sex_ids,
            variant_id=variant_id,
            location_id=location_id,
        )
        srb_records = client.fetch_indicator_records(
            indicator_id=WPP_INDICATORS["sex_ratio_at_birth"],
            years=years,
            ages=total_age_ids,
            sexes=both_sex_ids,
            variant_id=variant_id,
            location_id=location_id,
        )
        _write_json(cache_dir / f"fertility_{variant_name}.json", fertility_records)
        _write_json(cache_dir / f"sex_ratio_at_birth_{variant_name}.json", srb_records)
        fertility_frames[variant_name] = _normalize_fertility(fertility_records)
        srb_frames[variant_name] = _normalize_total_indicator(srb_records, "sex_ratio_at_birth")
        _write_csv(fertility_csv, fertility_frames[variant_name])
        _write_csv(srb_csv, srb_frames[variant_name])

        if variant_name == "medium":
            population_records = client.fetch_indicator_records(
                indicator_id=WPP_INDICATORS["population"],
                years=years,
                ages=population_age_ids,
                sexes=population_sex_ids,
                variant_id=variant_id,
                location_id=location_id,
            )
            migration_records = client.fetch_indicator_records(
                indicator_id=WPP_INDICATORS["net_migration"],
                years=years,
                ages=total_age_ids,
                sexes=both_sex_ids,
                variant_id=variant_id,
                location_id=location_id,
            )

            _write_json(cache_dir / "population_medium.json", population_records)
            _write_json(cache_dir / "net_migration_medium.json", migration_records)

            population_frames["medium"] = _normalize_population(population_records)
            migration_frames["medium"] = _normalize_total_indicator(migration_records, "net_migration")

            _write_csv(population_csv, population_frames["medium"])
            _write_csv(migration_csv, migration_frames["medium"])
            continue

        population_frames[variant_name] = population_frames["medium"].copy()
        migration_frames[variant_name] = migration_frames["medium"].copy()
        _write_csv(population_csv, population_frames[variant_name])
        _write_csv(migration_csv, migration_frames[variant_name])

    mortality_csv = cache_dir / "mortality_medium.csv"
    if not force and mortality_csv.exists():
        mortality_frame = pd.read_csv(mortality_csv)
    else:
        mortality_records = client.fetch_indicator_records(
            indicator_id=WPP_INDICATORS["mortality"],
            years=years,
            ages=mortality_age_ids,
            sexes=mortality_sex_ids,
            variant_id=WPP_VARIANTS["medium"],
            location_id=location_id,
        )
        _write_json(cache_dir / "mortality_medium.json", mortality_records)
        mortality_frame = _normalize_mortality(mortality_records)
        _write_csv(mortality_csv, mortality_frame)

    return WppBundle(
        population=population_frames,
        fertility=fertility_frames,
        mortality=mortality_frame,
        sex_ratio_at_birth=srb_frames,
        net_migration=migration_frames,
        metadata=metadata,
    )


def download_usa_wpp_bundle(
    start_year: int = DEFAULT_BASE_YEAR,
    end_year: int = DEFAULT_FINAL_YEAR,
    force: bool = False,
) -> WppBundle:
    return download_country_wpp_bundle(
        country="USA",
        start_year=start_year,
        end_year=end_year,
        force=force,
    )


def download_world_wpp_bundle(
    start_year: int = DEFAULT_BASE_YEAR,
    end_year: int = DEFAULT_FINAL_YEAR,
    force: bool = False,
) -> WppBundle:
    return download_country_wpp_bundle(
        country="World",
        start_year=start_year,
        end_year=end_year,
        force=force,
    )


def _coerce_country_spec(country: str | CountrySpec) -> CountrySpec:
    if isinstance(country, CountrySpec):
        return country

    return get_country_spec(country)


def download_country_wpp_bundle(
    country: str | CountrySpec,
    start_year: int = DEFAULT_BASE_YEAR,
    end_year: int = DEFAULT_FINAL_YEAR,
    force: bool = False,
) -> WppBundle:
    country_spec = _coerce_country_spec(country)
    return download_wpp_bundle(
        location_id=country_spec.location_id,
        cache_slug=country_spec.cache_slug,
        start_year=start_year,
        end_year=end_year,
        force=force,
    )


def load_cached_wpp_bundle(cache_slug: str = "usa") -> WppBundle:
    cache_dir = _wpp_cache_dir(cache_slug)
    metadata: dict[str, dict[str, Any]] = {}
    for key in WPP_INDICATORS:
        metadata_path = cache_dir / f"{key}_metadata.json"
        if metadata_path.exists():
            metadata[key] = json.loads(metadata_path.read_text())
        else:
            metadata[key] = {}

    population = {
        variant_name: pd.read_csv(cache_dir / f"population_{variant_name}.csv")
        for variant_name in WPP_VARIANTS
    }
    fertility = {
        variant_name: pd.read_csv(cache_dir / f"fertility_{variant_name}.csv")
        for variant_name in WPP_VARIANTS
    }
    sex_ratio_at_birth = {
        variant_name: pd.read_csv(cache_dir / f"sex_ratio_at_birth_{variant_name}.csv")
        for variant_name in WPP_VARIANTS
    }
    net_migration = {
        variant_name: pd.read_csv(cache_dir / f"net_migration_{variant_name}.csv")
        for variant_name in WPP_VARIANTS
    }
    mortality = pd.read_csv(cache_dir / "mortality_medium.csv")

    return WppBundle(
        population=population,
        fertility=fertility,
        mortality=mortality,
        sex_ratio_at_birth=sex_ratio_at_birth,
        net_migration=net_migration,
        metadata=metadata,
    )


def load_cached_country_wpp_bundle(country: str | CountrySpec) -> WppBundle:
    country_spec = _coerce_country_spec(country)
    return load_cached_wpp_bundle(cache_slug=country_spec.cache_slug)


def load_hmd_period_data(sex: str) -> pd.DataFrame:
    if sex not in HMD_PERIOD_FILES:
        raise KeyError(f"Unsupported HMD sex: {sex}")

    frame = pd.read_csv(HMD_PERIOD_FILES[sex], sep=r"\s+")
    frame["Age"] = frame["Age"].str.rstrip("+").astype(int)
    frame["Year"] = frame["Year"].astype(int)
    frame["mx"] = pd.to_numeric(frame["mx"], errors="coerce")
    frame["qx"] = pd.to_numeric(frame["qx"], errors="coerce")
    frame["lx"] = pd.to_numeric(frame["lx"], errors="coerce")

    output = frame.rename(columns={"Year": "year", "Age": "age", "lx": "survivors"})
    output["sex"] = sex

    raw_path = RAW_HMD_DIR / f"usa_period_{sex}.csv"
    _write_csv(raw_path, output[["year", "age", "sex", "mx", "qx", "survivors"]])

    return output[["year", "age", "sex", "mx", "qx", "survivors"]].copy()


def load_hfd_if_available() -> pd.DataFrame | None:
    files = sorted(RAW_HFD_DIR.glob("*.csv"))
    if not files:
        return None

    frames = [pd.read_csv(path) for path in files]
    if not frames:
        return None

    return pd.concat(frames, ignore_index=True)
