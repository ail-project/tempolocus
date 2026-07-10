"""Core inference logic for tempolocus.

The first implementation is deliberately dependency-free and heuristic-based.
It does not try to identify a precise home address or city. It ranks timezone
offsets from weekly hourly patterns and broad regions from yearly calendar
activity.
"""

from __future__ import annotations

import calendar
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


class DetectionError(ValueError):
    """Raised when an input file cannot be interpreted."""


@dataclass(frozen=True)
class Holiday:
    day: date
    name: str


OFFSET_LABELS: dict[int, tuple[str, list[str]]] = {
    -12: ("UTC-12 Baker/Howland Islands", ["Etc/GMT+12"]),
    -11: ("UTC-11 American Samoa / Niue", ["Pacific/Pago_Pago", "Pacific/Niue"]),
    -10: ("UTC-10 Hawaii / Tahiti", ["Pacific/Honolulu", "Pacific/Tahiti"]),
    -9: ("UTC-09 Alaska", ["America/Anchorage"]),
    -8: ("UTC-08 Pacific North America", ["America/Los_Angeles", "America/Vancouver"]),
    -7: ("UTC-07 Mountain North America", ["America/Denver", "America/Phoenix"]),
    -6: ("UTC-06 Central North America", ["America/Chicago", "America/Mexico_City"]),
    -5: (
        "UTC-05 Eastern North America / Andean",
        ["America/New_York", "America/Toronto", "America/Bogota"],
    ),
    -4: (
        "UTC-04 Atlantic / western South America",
        ["America/Halifax", "America/Santiago", "America/Caracas"],
    ),
    -3: (
        "UTC-03 Argentina / eastern Brazil",
        ["America/Argentina/Buenos_Aires", "America/Sao_Paulo"],
    ),
    -2: ("UTC-02 Mid-Atlantic", ["Atlantic/South_Georgia"]),
    -1: ("UTC-01 Azores / Cape Verde", ["Atlantic/Azores", "Atlantic/Cape_Verde"]),
    0: (
        "UTC+00 Western Europe / West Africa",
        ["Europe/London", "Europe/Dublin", "Africa/Accra"],
    ),
    1: (
        "UTC+01 Central Europe / West Africa",
        ["Europe/Paris", "Europe/Berlin", "Africa/Lagos"],
    ),
    2: (
        "UTC+02 Eastern Europe / southern Africa",
        ["Europe/Athens", "Europe/Helsinki", "Africa/Johannesburg"],
    ),
    3: (
        "UTC+03 East Africa / Arabia / Moscow",
        ["Europe/Moscow", "Asia/Riyadh", "Africa/Nairobi"],
    ),
    4: ("UTC+04 Gulf / Caucasus", ["Asia/Dubai", "Asia/Baku", "Indian/Mauritius"]),
    5: ("UTC+05 Pakistan / western Central Asia", ["Asia/Karachi", "Asia/Tashkent"]),
    6: ("UTC+06 Bangladesh / central Asia", ["Asia/Dhaka", "Asia/Almaty"]),
    7: (
        "UTC+07 mainland Southeast Asia",
        ["Asia/Bangkok", "Asia/Jakarta", "Asia/Ho_Chi_Minh"],
    ),
    8: (
        "UTC+08 China / Singapore / Western Australia",
        ["Asia/Shanghai", "Asia/Singapore", "Australia/Perth"],
    ),
    9: ("UTC+09 Japan / Korea", ["Asia/Tokyo", "Asia/Seoul"]),
    10: (
        "UTC+10 eastern Australia / western Pacific",
        ["Australia/Sydney", "Pacific/Guam"],
    ),
    11: ("UTC+11 western Pacific", ["Pacific/Noumea", "Asia/Magadan"]),
    12: ("UTC+12 New Zealand / Fiji", ["Pacific/Auckland", "Pacific/Fiji"]),
    13: ("UTC+13 Samoa / Tonga", ["Pacific/Apia", "Pacific/Tongatapu"]),
    14: ("UTC+14 Line Islands", ["Pacific/Kiritimati"]),
}


COUNTRY_TIMEZONE_OFFSETS: dict[str, tuple[str, set[int]]] = {
    "US": ("United States", {-10, -9, -8, -7, -6, -5}),
    "CA": ("Canada", {-8, -7, -6, -5, -4}),
    "MX": ("Mexico", {-8, -7, -6}),
    "AR": ("Argentina", {-3}),
    "BR": ("Brazil", {-5, -4, -3, -2}),
    "CL": ("Chile", {-6, -4}),
    "CO": ("Colombia", {-5}),
    "EC": ("Ecuador", {-6, -5}),
    "PE": ("Peru", {-5}),
    "UY": ("Uruguay", {-3}),
    "PT": ("Portugal", {-1, 0}),
    "ES": ("Spain", {0, 1}),
    "FR": ("France", {-10, -4, -3, 1, 3, 4, 11, 12}),
    "GB": ("United Kingdom", {-8, -4, -3, -2, 0, 6}),
    "RU": ("Russia", {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}),
    "KZ": ("Kazakhstan", {5, 6}),
    "MN": ("Mongolia", {7, 8}),
    "ID": ("Indonesia", {7, 8, 9}),
    "AU": ("Australia", {8, 9, 10}),
    "FM": ("Micronesia", {10, 11}),
    "KI": ("Kiribati", {12, 13, 14}),
    "NZ": ("New Zealand", {-10, 12, 13}),
}


LOCAL_ACTIVITY_PROFILE = {
    0: 0.04,
    1: 0.02,
    2: 0.01,
    3: 0.01,
    4: 0.03,
    5: 0.08,
    6: 0.22,
    7: 0.50,
    8: 0.78,
    9: 0.95,
    10: 1.00,
    11: 0.98,
    12: 0.82,
    13: 0.88,
    14: 0.98,
    15: 1.00,
    16: 0.93,
    17: 0.78,
    18: 0.58,
    19: 0.42,
    20: 0.30,
    21: 0.21,
    22: 0.13,
    23: 0.07,
}


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def detect(
    data: Any,
    kind: str = "auto",
    top: int = 5,
    holiday_profile: str = "standard",
    activity_signal: str = "lack",
) -> dict[str, Any]:
    if top < 1:
        raise DetectionError("top must be >= 1")

    detected = _detect_kind(data) if kind == "auto" else kind
    if detected == "weekly":
        return infer_weekly(data, top=top)
    if detected == "yearly":
        return infer_yearly(
            data,
            top=top,
            holiday_profile=holiday_profile,
            activity_signal=activity_signal,
        )
    raise DetectionError(f"unsupported input kind: {detected}")


def _detect_kind(data: Any) -> str:
    if isinstance(data, list) and data:
        if all(
            isinstance(item, dict) and {"day", "hour", "count"} <= set(item)
            for item in data
        ):
            return "weekly"
    if isinstance(data, dict) and isinstance(data.get("nb"), list):
        return "yearly"
    raise DetectionError("could not auto-detect input kind")


def infer_weekly(data: Any, top: int = 5) -> dict[str, Any]:
    rows = _parse_weekly_rows(data)
    hourly = [0.0] * 24
    daily = [0.0] * 7
    for day, hour, count in rows:
        hourly[hour] += count
        daily[day] += count

    total = sum(hourly)
    if total <= 0:
        raise DetectionError("weekly input has no activity")

    quiet_start, quiet_sum = _lowest_window(hourly, window=6)
    quiet_center = (quiet_start + 2.5) % 24
    quiet_ratio = quiet_sum / (total * 6 / 24)
    contrast = max(0.0, min(1.0, 1.0 - quiet_ratio))

    candidates = []
    for offset in range(-12, 15):
        profile = (
            sum(
                count * LOCAL_ACTIVITY_PROFILE[(hour + offset) % 24]
                for hour, count in enumerate(hourly)
            )
            / total
        )
        local_quiet_center = (quiet_center + offset) % 24
        sleep_distance = _circular_distance(local_quiet_center, 2.5, 24)
        sleep_score = math.exp(-((sleep_distance / 3.8) ** 2))
        raw_score = (0.63 * profile) + (0.37 * sleep_score)
        raw_score *= 0.72 + (0.28 * contrast)
        label, zones = OFFSET_LABELS[offset]
        candidates.append(
            {
                "kind": "timezone",
                "id": _format_offset(offset),
                "label": label,
                "timezone_candidates": zones,
                "score": raw_score,
                "evidence": {
                    "utc_quiet_window": _format_hour_window(quiet_start, 6),
                    "local_quiet_window": _format_hour_window(
                        (quiet_start + offset) % 24, 6
                    ),
                    "quiet_activity_ratio": round(quiet_ratio, 3),
                    "local_quiet_center": round(local_quiet_center, 2),
                },
            }
        )

    _attach_probabilities(candidates, temperature=10.0)
    candidates.sort(key=lambda item: item["probability"], reverse=True)

    weekday_total = sum(daily[:5])
    weekend_total = sum(daily[5:])
    weekend_share = weekend_total / (weekday_total + weekend_total)
    inferred_offset = _parse_offset(candidates[0]["id"])
    local_rows = _shift_weekly_rows(rows, inferred_offset)
    activity_analysis = analyze_weekly_activity(local_rows)
    activity_analysis["basis"] = (
        f"weekly business-hours versus weekend/off-hours activity after shifting "
        f"UTC buckets by inferred offset {candidates[0]['id']}"
    )
    activity_analysis["timezone_offset"] = candidates[0]["id"]
    top_timezone_candidates = candidates[:top]
    probable_countries = _probable_countries_from_timezones(top_timezone_candidates)
    return {
        "input_type": "weekly_timeseries",
        "confidence": _distribution_confidence(candidates),
        "analysis": activity_analysis,
        "assumptions": [
            "Hourly buckets are interpreted as UTC; timezone candidates are offsets that make the activity look locally human.",
            "Weekly data cannot distinguish all IANA zones sharing the same offset, and daylight saving time is not inferable without dates.",
        ],
        "signals": {
            "total_activity": int(total) if total.is_integer() else total,
            "utc_quiet_window": _format_hour_window(quiet_start, 6),
            "quiet_activity_ratio": round(quiet_ratio, 3),
            "weekend_share": round(weekend_share, 3),
        },
        "probable_countries": probable_countries,
        "results": top_timezone_candidates,
    }


def infer_yearly(
    data: Any,
    top: int = 5,
    holiday_profile: str = "standard",
    activity_signal: str = "lack",
) -> dict[str, Any]:
    if holiday_profile not in {"standard", "public-worker"}:
        raise DetectionError("holiday_profile must be standard or public-worker")
    if activity_signal not in {"lack", "peak"}:
        raise DetectionError("activity_signal must be lack or peak")

    observed = _parse_yearly_rows(data)
    if not observed:
        raise DetectionError("yearly input has no activity")

    first_day = min(observed)
    last_day = max(observed)
    full_series = _fill_dates(observed, first_day, last_day)
    percentiles = _percentiles(full_series)
    counts = list(full_series.values())
    baseline = median(counts)

    candidates = []
    for region_id, label, holidays in _candidate_holidays(
        first_day.year, include_public_worker=(holiday_profile == "public-worker")
    ).values():
        relevant = [
            holiday for holiday in holidays if first_day <= holiday.day <= last_day
        ]
        if not relevant:
            continue

        holiday_percentiles = [percentiles[holiday.day] for holiday in relevant]
        signal = "holiday_drop" if activity_signal == "lack" else "holiday_spike"
        signal_score = mean(
            1.0 - value if activity_signal == "lack" else value
            for value in holiday_percentiles
        )

        top_dates = _top_fraction(
            percentiles, fraction=0.10, high=(activity_signal == "peak")
        )
        holiday_days = {holiday.day for holiday in relevant}
        hits = sorted(day for day in top_dates if day in holiday_days)
        expected = max(0.001, len(holiday_days) / len(full_series))
        observed_hit_rate = len(hits) / max(1, len(top_dates))
        enrichment = max(0.0, min(1.0, observed_hit_rate / (expected * 4.0)))

        raw_score = (0.78 * signal_score) + (0.22 * enrichment)
        if len(relevant) < 3:
            raw_score *= 0.72

        candidates.append(
            {
                "kind": "region",
                "id": region_id,
                "label": label,
                "score": raw_score,
                "signal": signal,
                "evidence": {
                    "matched_holidays": [
                        {
                            "date": day.isoformat(),
                            "count": full_series[day],
                            "name": _holiday_name(day, relevant),
                        }
                        for day in hits[:6]
                    ],
                    "holiday_dates_seen": len(relevant),
                    "median_daily_activity": baseline,
                },
            }
        )

    if not candidates:
        raise DetectionError(
            "no yearly candidates could be evaluated for the observed date range"
        )

    _attach_probabilities(candidates, temperature=7.0)
    candidates.sort(key=lambda item: item["probability"], reverse=True)
    activity_analysis = analyze_yearly_activity(full_series)
    return {
        "input_type": "yearly_daily_activity",
        "confidence": _distribution_confidence(candidates),
        "analysis": activity_analysis,
        "assumptions": [
            "Daily buckets are compared with representative public-holiday calendars.",
            (
                "The public-worker holiday profile adds public-sector closure days where they are distinct from general public holidays."
                if holiday_profile == "public-worker"
                else "Only general public holidays are used unless the public-worker holiday profile is requested."
            ),
            (
                "Yearly holiday matching treats low-count days as the signal; pass activity_signal='peak' if high-count days are meaningful."
                if activity_signal == "lack"
                else "Yearly holiday matching treats high-count days as the signal; use activity_signal='lack' for closure or inactivity patterns."
            ),
            "This first implementation ranks broad regions; it is not a legal or forensic geolocation result.",
        ],
        "signals": {
            "date_range": {"start": first_day.isoformat(), "end": last_day.isoformat()},
            "days_seen": len(observed),
            "days_evaluated": len(full_series),
            "median_daily_activity": baseline,
            "max_daily_activity": max(counts),
            "holiday_profile": holiday_profile,
            "activity_signal": activity_signal,
        },
        "results": candidates[:top],
    }


def analyze_activity(data: Any, kind: str = "auto") -> dict[str, Any]:
    """Classify temporal activity as work-time, vacation-time, or mixed-time."""
    detected = _detect_kind(data) if kind == "auto" else kind
    if detected == "weekly":
        return analyze_weekly_activity(_parse_weekly_rows(data))
    if detected == "yearly":
        observed = _parse_yearly_rows(data)
        if not observed:
            raise DetectionError("yearly input has no activity")
        return analyze_yearly_activity(
            _fill_dates(observed, min(observed), max(observed))
        )
    raise DetectionError(f"unsupported input kind: {detected}")


def analyze_weekly_activity(rows: list[tuple[int, int, float]]) -> dict[str, Any]:
    totals = {"work": 0.0, "vacation": 0.0, "other": 0.0}
    total = 0.0
    for day, hour, count in rows:
        total += count
        if day <= 4 and 8 <= hour <= 17:
            totals["work"] += count
        elif day >= 5 or hour < 8 or hour >= 18:
            totals["vacation"] += count
        else:
            totals["other"] += count
    if total <= 0:
        raise DetectionError("weekly input has no activity")

    work_share = totals["work"] / total
    vacation_share = totals["vacation"] / total
    other_share = totals["other"] / total
    expected_work_share = sum(
        1 for day in range(5) for hour in range(8, 18)
    ) / (7 * 24)
    expected_vacation_share = sum(
        1
        for day in range(7)
        for hour in range(24)
        if day >= 5 or hour < 8 or hour >= 18
    ) / (7 * 24)
    work_lift = work_share - expected_work_share
    vacation_lift = vacation_share - expected_vacation_share
    if work_lift >= 0.12 and work_lift >= vacation_lift:
        activity_type = "work-time"
        confidence = work_lift
    elif vacation_lift >= 0.12 and vacation_lift > work_lift:
        activity_type = "vacation-time"
        confidence = vacation_lift
    else:
        activity_type = "mixed-time"
        confidence = max(abs(work_lift), abs(vacation_lift))
    return {
        "activity_type": activity_type,
        "confidence": round(confidence, 6),
        "basis": "weekly business-hours versus weekend/off-hours activity",
        "shares": {
            "work_time": round(work_share, 6),
            "vacation_time": round(vacation_share, 6),
            "other_time": round(other_share, 6),
            "expected_work_time": round(expected_work_share, 6),
            "expected_vacation_time": round(expected_vacation_share, 6),
        },
    }


def analyze_yearly_activity(series: dict[date, float]) -> dict[str, Any]:
    total = sum(series.values())
    if total <= 0:
        raise DetectionError("yearly input has no activity")
    weekday_total = sum(count for day, count in series.items() if day.weekday() < 5)
    weekend_total = total - weekday_total
    weekday_days = sum(1 for day in series if day.weekday() < 5)
    weekend_days = len(series) - weekday_days
    weekday_share = weekday_total / total
    weekend_share = weekend_total / total
    expected_weekday_share = weekday_days / len(series)
    expected_weekend_share = weekend_days / len(series)
    weekday_lift = weekday_share - expected_weekday_share
    weekend_lift = weekend_share - expected_weekend_share

    if weekday_lift >= 0.12:
        activity_type = "work-time"
        confidence = weekday_lift
    elif weekend_lift >= 0.12:
        activity_type = "vacation-time"
        confidence = weekend_lift
    else:
        activity_type = "mixed-time"
        confidence = max(abs(weekday_lift), abs(weekend_lift))
    return {
        "activity_type": activity_type,
        "confidence": round(confidence, 6),
        "basis": "yearly weekday versus weekend activity balance",
        "shares": {
            "weekday_activity": round(weekday_share, 6),
            "weekend_activity": round(weekend_share, 6),
            "expected_weekday_days": round(expected_weekday_share, 6),
            "expected_weekend_days": round(expected_weekend_share, 6),
        },
    }


def _parse_weekly_rows(data: Any) -> list[tuple[int, int, float]]:
    if not isinstance(data, list):
        raise DetectionError("weekly input must be a JSON list")
    rows = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise DetectionError(f"weekly row {index} is not an object")
        try:
            day = int(item["day"])
            hour = int(item["hour"])
            count = float(item["count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DetectionError(
                f"weekly row {index} must contain numeric day, hour, and count"
            ) from exc
        if not 0 <= day <= 6:
            raise DetectionError(f"weekly row {index} has invalid day: {day}")
        if not 0 <= hour <= 23:
            raise DetectionError(f"weekly row {index} has invalid hour: {hour}")
        if count < 0:
            raise DetectionError(f"weekly row {index} has negative count")
        rows.append((day, hour, count))
    return rows


def _parse_yearly_rows(data: Any) -> dict[date, float]:
    if not isinstance(data, dict) or not isinstance(data.get("nb"), list):
        raise DetectionError("yearly input must be an object containing an nb list")
    observed = {}
    for index, row in enumerate(data["nb"]):
        if not isinstance(row, list) or len(row) != 2:
            raise DetectionError(f"yearly row {index} must be [date, count]")
        try:
            day = date.fromisoformat(row[0])
            count = float(row[1])
        except (TypeError, ValueError) as exc:
            raise DetectionError(
                f"yearly row {index} contains an invalid date or count"
            ) from exc
        if count < 0:
            raise DetectionError(f"yearly row {index} has negative count")
        observed[day] = observed.get(day, 0.0) + count
    return observed


def _lowest_window(values: list[float], window: int) -> tuple[int, float]:
    best_start = 0
    best_sum = math.inf
    for start in range(len(values)):
        total = sum(values[(start + offset) % len(values)] for offset in range(window))
        if total < best_sum:
            best_start = start
            best_sum = total
    return best_start, best_sum


def _shift_weekly_rows(
    rows: list[tuple[int, int, float]], offset: int
) -> list[tuple[int, int, float]]:
    shifted = []
    for day, hour, count in rows:
        shifted_hour_total = hour + offset
        shifted_day = (day + math.floor(shifted_hour_total / 24)) % 7
        shifted_hour = shifted_hour_total % 24
        shifted.append((shifted_day, shifted_hour, count))
    return shifted


def _parse_offset(offset_id: str) -> int:
    if not offset_id.startswith("UTC") or not offset_id.endswith(":00"):
        raise DetectionError(f"invalid timezone offset id: {offset_id}")
    return int(offset_id[3:-3])


def _probable_countries_from_timezones(
    timezone_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rank countries whose multiple timezones appear in the top weekly offsets."""
    if not timezone_candidates:
        return []

    probabilities_by_offset = {
        _parse_offset(candidate["id"]): candidate["probability"]
        for candidate in timezone_candidates
    }
    country_candidates = []
    for country_id, (label, country_offsets) in COUNTRY_TIMEZONE_OFFSETS.items():
        matched_offsets = sorted(set(probabilities_by_offset) & country_offsets)
        if not matched_offsets:
            continue

        probability_mass = sum(
            probabilities_by_offset[offset] for offset in matched_offsets
        )
        matched_count = len(matched_offsets)
        coverage = matched_count / len(country_offsets)
        multi_timezone_bonus = 1.0 + (0.18 * (matched_count - 1))
        score = probability_mass * (0.78 + (0.22 * coverage)) * multi_timezone_bonus
        country_candidates.append(
            {
                "kind": "country",
                "id": country_id,
                "label": label,
                "score": score,
                "matched_timezone_offsets": [
                    _format_offset(offset) for offset in matched_offsets
                ],
                "matched_timezone_count": matched_count,
                "country_timezone_count": len(country_offsets),
                "evidence": {
                    "top_timezone_probability_mass": round(probability_mass, 6),
                    "top_timezone_coverage": round(coverage, 6),
                    "multiple_timezone_match": matched_count > 1,
                },
            }
        )

    _attach_probabilities(country_candidates, temperature=4.0)
    country_candidates.sort(key=lambda item: item["probability"], reverse=True)
    return country_candidates[: min(5, len(country_candidates))]


def _format_offset(offset: int) -> str:
    sign = "+" if offset >= 0 else "-"
    return f"UTC{sign}{abs(offset):02d}:00"


def _format_hour_window(start: int | float, width: int) -> str:
    start_int = int(start) % 24
    end_int = (start_int + width) % 24
    return f"{start_int:02d}:00-{end_int:02d}:00"


def _circular_distance(a: float, b: float, modulo: int) -> float:
    diff = abs(a - b) % modulo
    return min(diff, modulo - diff)


def _attach_probabilities(items: list[dict[str, Any]], temperature: float) -> None:
    if not items:
        return
    max_score = max(item["score"] for item in items)
    weights = [math.exp((item["score"] - max_score) * temperature) for item in items]
    total = sum(weights)
    for item, weight in zip(items, weights):
        item["probability"] = round(weight / total, 6)
        item["score"] = round(item["score"], 6)


def _distribution_confidence(items: list[dict[str, Any]]) -> float:
    probabilities = sorted((item["probability"] for item in items), reverse=True)
    if not probabilities:
        return 0.0
    if len(probabilities) == 1:
        return probabilities[0]
    confidence = max(0.0, probabilities[0] - probabilities[1]) + probabilities[0]
    return round(min(1.0, confidence), 6)


def _fill_dates(
    observed: dict[date, float], start: date, end: date
) -> dict[date, float]:
    series = {}
    current = start
    while current <= end:
        series[current] = observed.get(current, 0.0)
        current += timedelta(days=1)
    return series


def _percentiles(series: dict[date, float]) -> dict[date, float]:
    ordered = sorted(series.items(), key=lambda item: (item[1], item[0]))
    if len(ordered) == 1:
        return {ordered[0][0]: 1.0}
    return {
        day: rank / (len(ordered) - 1) for rank, (day, _count) in enumerate(ordered)
    }


def _top_fraction(
    percentiles: dict[date, float], fraction: float, high: bool
) -> set[date]:
    count = max(1, round(len(percentiles) * fraction))
    reverse = high
    return {
        day
        for day, _value in sorted(
            percentiles.items(), key=lambda item: item[1], reverse=reverse
        )[:count]
    }


def _holiday_name(day: date, holidays: Iterable[Holiday]) -> str:
    names = [holiday.name for holiday in holidays if holiday.day == day]
    return ", ".join(names)


def _candidate_holidays(
    year: int, include_public_worker: bool = False
) -> dict[str, tuple[str, str, list[Holiday]]]:
    easter = _easter_sunday(year)
    orthodox_easter = _orthodox_easter_sunday(year)
    candidates = {
        "US": ("US", "United States", _us_holidays(year)),
        "CA": ("CA", "Canada", _canada_holidays(year, easter)),
        "GB": ("GB", "United Kingdom", _uk_holidays(year, easter)),
        "IE": ("IE", "Ireland", _ireland_holidays(year, easter)),
        "FR": ("FR", "France", _france_holidays(year, easter)),
        "DE": ("DE", "Germany", _germany_holidays(year, easter)),
        "IT": ("IT", "Italy", _italy_holidays(year, easter)),
        "ES": ("ES", "Spain", _spain_holidays(year, easter)),
        "PT": ("PT", "Portugal", _portugal_holidays(year, easter)),
        "BE": ("BE", "Belgium", _belgium_holidays(year, easter)),
        "NL": ("NL", "Netherlands", _netherlands_holidays(year, easter)),
        "CH": ("CH", "Switzerland", _switzerland_holidays(year, easter)),
        "AT": ("AT", "Austria", _austria_holidays(year, easter)),
        "PL": ("PL", "Poland", _poland_holidays(year, easter)),
        "CZ": ("CZ", "Czechia", _czechia_holidays(year, easter)),
        "SK": ("SK", "Slovakia", _slovakia_holidays(year, easter)),
        "HU": ("HU", "Hungary", _hungary_holidays(year, easter)),
        "RO": ("RO", "Romania", _romania_holidays(year, orthodox_easter)),
        "GR": ("GR", "Greece", _greece_holidays(year, orthodox_easter)),
        "BG": ("BG", "Bulgaria", _bulgaria_holidays(year, orthodox_easter)),
        "RS": ("RS", "Serbia", _serbia_holidays(year, orthodox_easter)),
        "UA": ("UA", "Ukraine", _ukraine_holidays(year, orthodox_easter)),
        "RU": ("RU", "Russia", _russia_holidays(year, orthodox_easter)),
        "DK": ("DK", "Denmark", _denmark_holidays(year, easter)),
        "NO": ("NO", "Norway", _norway_holidays(year, easter)),
        "SE": ("SE", "Sweden", _sweden_holidays(year, easter)),
        "FI": ("FI", "Finland", _finland_holidays(year, easter)),
        "JP": ("JP", "Japan", _japan_holidays(year)),
        "KR": ("KR", "South Korea", _south_korea_holidays(year)),
        "CN": ("CN", "China", _china_holidays(year)),
        "IN": ("IN", "India", _india_holidays(year)),
        "BR": ("BR", "Brazil", _brazil_holidays(year, easter)),
        "CL": ("CL", "Chile", _chile_holidays(year, easter)),
        "CO": ("CO", "Colombia", _colombia_holidays(year, easter)),
        "PE": ("PE", "Peru", _peru_holidays(year, easter)),
        "UY": ("UY", "Uruguay", _uruguay_holidays(year, easter)),
        "MX": ("MX", "Mexico", _mexico_holidays(year)),
        "AR": ("AR", "Argentina", _argentina_holidays(year, easter)),
        "AU": ("AU", "Australia", _australia_holidays(year, easter)),
        "NZ": ("NZ", "New Zealand", _new_zealand_holidays(year, easter)),
    }
    if include_public_worker:
        candidates.update(_public_worker_holiday_candidates(year, candidates))
    return candidates


def _public_worker_holiday_candidates(
    year: int, standard: dict[str, tuple[str, str, list[Holiday]]]
) -> dict[str, tuple[str, str, list[Holiday]]]:
    return {
        "US-PUBLIC-WORKER": (
            "US-PUBLIC-WORKER",
            "United States public-sector worker",
            _merge_holidays(
                standard["US"][2],
                [
                    _fixed(year, 2, 12, "Lincoln's Birthday / state worker holiday"),
                    _nth_weekday(year, 11, 1, 1, "Election Day / state worker holiday"),
                    _relative(
                        _nth_weekday(year, 11, 3, 4, "Thanksgiving").day,
                        1,
                        "Day after Thanksgiving / state worker holiday",
                    ),
                    _fixed(year, 12, 24, "Christmas Eve / public-sector closure"),
                    _fixed(year, 12, 31, "New Year's Eve / public-sector closure"),
                ],
            ),
        ),
        "ES-PUBLIC-WORKER": (
            "ES-PUBLIC-WORKER",
            "Spain public-sector worker",
            _merge_holidays(
                standard["ES"][2],
                [
                    _fixed(year, 5, 22, "Santa Rita / civil-servant reference day"),
                    _fixed(year, 12, 24, "Christmas Eve / public-sector closure"),
                    _fixed(year, 12, 31, "New Year's Eve / public-sector closure"),
                ],
            ),
        ),
        "FR-PUBLIC-WORKER": (
            "FR-PUBLIC-WORKER",
            "France public-sector worker",
            _merge_holidays(
                standard["FR"][2],
                [
                    _fixed(year, 5, 9, "Europe Day / institutional reference day"),
                    _fixed(year, 12, 24, "Christmas Eve / administrative closure"),
                    _fixed(year, 12, 31, "New Year's Eve / administrative closure"),
                ],
            ),
        ),
        "CN-PUBLIC-WORKER": (
            "CN-PUBLIC-WORKER",
            "China public-sector worker",
            _merge_holidays(
                standard["CN"][2],
                _china_public_worker_holidays(year),
            ),
        ),
        "RU-PUBLIC-WORKER": (
            "RU-PUBLIC-WORKER",
            "Russia public-sector worker",
            _merge_holidays(
                standard["RU"][2],
                _russia_public_worker_holidays(year),
            ),
        ),
        "AR-PUBLIC-WORKER": (
            "AR-PUBLIC-WORKER",
            "Argentina public-sector worker",
            _merge_holidays(
                standard["AR"][2],
                _south_america_public_worker_holidays(year),
            ),
        ),
        "BR-PUBLIC-WORKER": (
            "BR-PUBLIC-WORKER",
            "Brazil public-sector worker",
            _merge_holidays(
                standard["BR"][2],
                _south_america_public_worker_holidays(year),
            ),
        ),
        "CL-PUBLIC-WORKER": (
            "CL-PUBLIC-WORKER",
            "Chile public-sector worker",
            _merge_holidays(
                standard["CL"][2],
                _south_america_public_worker_holidays(year),
            ),
        ),
        "CO-PUBLIC-WORKER": (
            "CO-PUBLIC-WORKER",
            "Colombia public-sector worker",
            _merge_holidays(
                standard["CO"][2],
                _south_america_public_worker_holidays(year),
            ),
        ),
        "PE-PUBLIC-WORKER": (
            "PE-PUBLIC-WORKER",
            "Peru public-sector worker",
            _merge_holidays(
                standard["PE"][2],
                _south_america_public_worker_holidays(year),
            ),
        ),
        "UY-PUBLIC-WORKER": (
            "UY-PUBLIC-WORKER",
            "Uruguay public-sector worker",
            _merge_holidays(
                standard["UY"][2],
                _south_america_public_worker_holidays(year),
            ),
        ),
    }


def _merge_holidays(*holiday_lists: list[Holiday]) -> list[Holiday]:
    merged: dict[tuple[date, str], Holiday] = {}
    for holidays in holiday_lists:
        for holiday in holidays:
            merged[(holiday.day, holiday.name)] = holiday
    return sorted(merged.values(), key=lambda holiday: (holiday.day, holiday.name))


def _fixed(year: int, month: int, day: int, name: str) -> Holiday:
    return Holiday(date(year, month, day), name)


def _relative(base: date, days: int, name: str) -> Holiday:
    return Holiday(base + timedelta(days=days), name)


def _monday_on_or_after(day: date, name: str) -> Holiday:
    return Holiday(day + timedelta(days=(7 - day.weekday()) % 7), name)


def _nth_weekday(year: int, month: int, weekday: int, nth: int, name: str) -> Holiday:
    current = date(year, month, 1)
    while current.weekday() != weekday:
        current += timedelta(days=1)
    current += timedelta(days=7 * (nth - 1))
    return Holiday(current, name)


def _last_weekday(year: int, month: int, weekday: int, name: str) -> Holiday:
    current = date(year, month, calendar.monthrange(year, month)[1])
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return Holiday(current, name)


def _orthodox_easter_sunday(year: int) -> date:
    """Return Orthodox Easter Sunday in the Gregorian calendar."""
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    return date(year, month, day) + timedelta(days=13)


def _easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _us_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _nth_weekday(year, 1, 0, 3, "Martin Luther King Jr. Day"),
        _nth_weekday(year, 2, 0, 3, "Presidents' Day"),
        _last_weekday(year, 5, 0, "Memorial Day"),
        _fixed(year, 6, 19, "Juneteenth"),
        _fixed(year, 7, 4, "Independence Day"),
        _nth_weekday(year, 9, 0, 1, "Labor Day"),
        _nth_weekday(year, 10, 0, 2, "Columbus Day"),
        _fixed(year, 11, 11, "Veterans Day"),
        _nth_weekday(year, 11, 3, 4, "Thanksgiving"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _canada_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -2, "Good Friday"),
        _last_weekday(year, 5, 0, "Victoria Day"),
        _fixed(year, 7, 1, "Canada Day"),
        _nth_weekday(year, 9, 0, 1, "Labour Day"),
        _nth_weekday(year, 10, 0, 2, "Thanksgiving"),
        _fixed(year, 11, 11, "Remembrance Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Boxing Day"),
    ]


def _uk_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _nth_weekday(year, 5, 0, 1, "Early May Bank Holiday"),
        _last_weekday(year, 5, 0, "Spring Bank Holiday"),
        _last_weekday(year, 8, 0, "Summer Bank Holiday"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Boxing Day"),
    ]


def _ireland_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 3, 17, "Saint Patrick's Day"),
        _relative(easter, 1, "Easter Monday"),
        _nth_weekday(year, 5, 0, 1, "May Day"),
        _nth_weekday(year, 6, 0, 1, "June Bank Holiday"),
        _nth_weekday(year, 8, 0, 1, "August Bank Holiday"),
        _last_weekday(year, 10, 0, "October Bank Holiday"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Saint Stephen's Day"),
    ]


def _france_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 8, "Victory Day"),
        _relative(easter, 39, "Ascension Day"),
        _fixed(year, 7, 14, "Bastille Day"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 11, 11, "Armistice Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _germany_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 39, "Ascension Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 10, 3, "German Unity Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _italy_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 4, 25, "Liberation Day"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 6, 2, "Republic Day"),
        _fixed(year, 8, 15, "Ferragosto"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Saint Stephen's Day"),
    ]


def _spain_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, -2, "Good Friday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 10, 12, "National Day"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 6, "Constitution Day"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _portugal_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -2, "Good Friday"),
        _fixed(year, 4, 25, "Freedom Day"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 6, 10, "Portugal Day"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 10, 5, "Republic Day"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 1, "Restoration of Independence"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _belgium_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 39, "Ascension Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 7, 21, "National Day"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 11, 11, "Armistice Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _netherlands_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 4, 27, "King's Day"),
        _fixed(year, 5, 5, "Liberation Day"),
        _relative(easter, 39, "Ascension Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _switzerland_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 2, "Berchtold's Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _relative(easter, 39, "Ascension Day"),
        _fixed(year, 8, 1, "National Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Saint Stephen's Day"),
    ]


def _austria_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "State Holiday"),
        _relative(easter, 39, "Ascension Day"),
        _relative(easter, 50, "Whit Monday"),
        _relative(easter, 60, "Corpus Christi"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 10, 26, "National Day"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Saint Stephen's Day"),
    ]


def _poland_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "State Holiday"),
        _fixed(year, 5, 3, "Constitution Day"),
        _relative(easter, 60, "Corpus Christi"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 11, 11, "Independence Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _czechia_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 8, "Liberation Day"),
        _fixed(year, 7, 5, "Saints Cyril and Methodius Day"),
        _fixed(year, 7, 6, "Jan Hus Day"),
        _fixed(year, 9, 28, "Statehood Day"),
        _fixed(year, 10, 28, "Independence Day"),
        _fixed(year, 11, 17, "Freedom and Democracy Day"),
        _fixed(year, 12, 24, "Christmas Eve"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _slovakia_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "Republic Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 8, "Victory Day"),
        _fixed(year, 7, 5, "Saints Cyril and Methodius Day"),
        _fixed(year, 8, 29, "National Uprising Day"),
        _fixed(year, 9, 1, "Constitution Day"),
        _fixed(year, 9, 15, "Our Lady of Sorrows"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 11, 17, "Freedom and Democracy Day"),
        _fixed(year, 12, 24, "Christmas Eve"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Saint Stephen's Day"),
    ]


def _hungary_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 3, 15, "National Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 8, 20, "State Foundation Day"),
        _fixed(year, 10, 23, "National Day"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _romania_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 2, "Second New Year's Day"),
        _fixed(year, 1, 24, "Unification Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 11, 30, "Saint Andrew's Day"),
        _fixed(year, 12, 1, "National Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _greece_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _fixed(year, 3, 25, "Independence Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 10, 28, "Ochi Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Synaxis of the Mother of God"),
    ]


def _bulgaria_holidays(year: int, orthodox_easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 3, 3, "Liberation Day"),
        _relative(orthodox_easter, -2, "Orthodox Good Friday"),
        _relative(orthodox_easter, -1, "Orthodox Holy Saturday"),
        Holiday(orthodox_easter, "Orthodox Easter Sunday"),
        _relative(orthodox_easter, 1, "Orthodox Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 6, "Saint George's Day"),
        _fixed(year, 5, 24, "Culture and Literacy Day"),
        _fixed(year, 9, 6, "Unification Day"),
        _fixed(year, 9, 22, "Independence Day"),
        _fixed(year, 12, 24, "Christmas Eve"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _serbia_holidays(year: int, orthodox_easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 2, "Second New Year's Day"),
        _fixed(year, 1, 7, "Orthodox Christmas Day"),
        _fixed(year, 2, 15, "Statehood Day"),
        _fixed(year, 2, 16, "Second Statehood Day"),
        _relative(orthodox_easter, -2, "Orthodox Good Friday"),
        Holiday(orthodox_easter, "Orthodox Easter Sunday"),
        _relative(orthodox_easter, 1, "Orthodox Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 2, "Second Labour Day"),
        _fixed(year, 11, 11, "Armistice Day"),
    ]


def _ukraine_holidays(year: int, orthodox_easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 7, "Orthodox Christmas Day"),
        _fixed(year, 3, 8, "International Women's Day"),
        Holiday(orthodox_easter, "Orthodox Easter Sunday"),
        _relative(orthodox_easter, 49, "Orthodox Pentecost"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 8, "Day of Remembrance and Victory"),
        _fixed(year, 6, 28, "Constitution Day"),
        _fixed(year, 8, 24, "Independence Day"),
        _fixed(year, 10, 14, "Defenders Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _russia_holidays(year: int, orthodox_easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 7, "Orthodox Christmas Day"),
        _fixed(year, 2, 23, "Defender of the Fatherland Day"),
        _fixed(year, 3, 8, "International Women's Day"),
        Holiday(orthodox_easter, "Orthodox Easter Sunday"),
        _fixed(year, 5, 1, "Spring and Labour Day"),
        _fixed(year, 5, 9, "Victory Day"),
        _fixed(year, 6, 12, "Russia Day"),
        _fixed(year, 11, 4, "Unity Day"),
    ]


def _denmark_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -3, "Maundy Thursday"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _relative(easter, 26, "Great Prayer Day"),
        _relative(easter, 39, "Ascension Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _norway_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -3, "Maundy Thursday"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 17, "Constitution Day"),
        _relative(easter, 39, "Ascension Day"),
        _relative(easter, 50, "Whit Monday"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _sweden_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 39, "Ascension Day"),
        _fixed(year, 6, 6, "National Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _finland_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 6, "Epiphany"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 5, 1, "May Day"),
        _relative(easter, 39, "Ascension Day"),
        _fixed(year, 12, 6, "Independence Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Second Day of Christmas"),
    ]


def _japan_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _nth_weekday(year, 1, 0, 2, "Coming of Age Day"),
        _fixed(year, 2, 11, "National Foundation Day"),
        _fixed(year, 2, 23, "Emperor's Birthday"),
        _fixed(year, 3, 20, "Vernal Equinox Day"),
        _fixed(year, 4, 29, "Showa Day"),
        _fixed(year, 5, 3, "Constitution Memorial Day"),
        _fixed(year, 5, 4, "Greenery Day"),
        _fixed(year, 5, 5, "Children's Day"),
        _nth_weekday(year, 7, 0, 3, "Marine Day"),
        _fixed(year, 8, 11, "Mountain Day"),
        _nth_weekday(year, 9, 0, 3, "Respect for the Aged Day"),
        _fixed(year, 9, 23, "Autumnal Equinox Day"),
        _nth_weekday(year, 10, 0, 2, "Sports Day"),
        _fixed(year, 11, 3, "Culture Day"),
        _fixed(year, 11, 23, "Labour Thanksgiving Day"),
    ]


def _south_korea_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 3, 1, "Independence Movement Day"),
        _fixed(year, 5, 5, "Children's Day"),
        _fixed(year, 6, 6, "Memorial Day"),
        _fixed(year, 8, 15, "Liberation Day"),
        _fixed(year, 10, 3, "National Foundation Day"),
        _fixed(year, 10, 9, "Hangul Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _china_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 10, 1, "National Day"),
    ]


def _china_public_worker_holidays(year: int) -> list[Holiday]:
    holidays = [
        _fixed(year, 4, 5, "Qingming Festival / public-sector closure"),
        _fixed(year, 5, 2, "Labour Day Golden Week / public-sector closure"),
        _fixed(year, 5, 3, "Labour Day Golden Week / public-sector closure"),
        _fixed(year, 10, 2, "National Day Golden Week / public-sector closure"),
        _fixed(year, 10, 3, "National Day Golden Week / public-sector closure"),
        _fixed(year, 10, 4, "National Day Golden Week / public-sector closure"),
        _fixed(year, 10, 5, "National Day Golden Week / public-sector closure"),
        _fixed(year, 10, 6, "National Day Golden Week / public-sector closure"),
        _fixed(year, 10, 7, "National Day Golden Week / public-sector closure"),
    ]
    if lunar_new_year := _chinese_new_year(year):
        holidays.extend(
            Holiday(
                lunar_new_year + timedelta(days=offset),
                "Spring Festival / public-sector closure",
            )
            for offset in range(7)
        )
    return holidays


def _south_america_public_worker_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 2, "New Year bridge day / public-sector closure"),
        _fixed(year, 12, 24, "Christmas Eve / public-sector closure"),
        _fixed(year, 12, 31, "New Year's Eve / public-sector closure"),
    ]


def _russia_public_worker_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, day, "New Year holidays / public-sector closure")
        for day in range(2, 9)
    ] + [
        _fixed(
            year, 2, 22, "Defender of the Fatherland bridge day / public-sector closure"
        ),
        _fixed(
            year, 3, 7, "International Women's Day bridge day / public-sector closure"
        ),
        _fixed(year, 5, 2, "May holidays / public-sector closure"),
        _fixed(year, 5, 3, "May holidays / public-sector closure"),
        _fixed(year, 5, 10, "Victory Day bridge day / public-sector closure"),
        _fixed(year, 11, 3, "Unity Day bridge day / public-sector closure"),
        _fixed(year, 12, 31, "New Year's Eve / public-sector closure"),
    ]


def _chinese_new_year(year: int) -> date | None:
    dates = {
        2018: (2, 16),
        2019: (2, 5),
        2020: (1, 25),
        2021: (2, 12),
        2022: (2, 1),
        2023: (1, 22),
        2024: (2, 10),
        2025: (1, 29),
        2026: (2, 17),
        2027: (2, 6),
        2028: (1, 26),
        2029: (2, 13),
        2030: (2, 3),
    }
    if year not in dates:
        return None
    month, day = dates[year]
    return date(year, month, day)


def _india_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 26, "Republic Day"),
        _fixed(year, 8, 15, "Independence Day"),
        _fixed(year, 10, 2, "Gandhi Jayanti"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _brazil_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -47, "Carnival Monday"),
        _relative(easter, -46, "Carnival Tuesday"),
        _relative(easter, -2, "Good Friday"),
        _fixed(year, 4, 21, "Tiradentes"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 60, "Corpus Christi"),
        _fixed(year, 9, 7, "Independence Day"),
        _fixed(year, 10, 12, "Our Lady of Aparecida"),
        _fixed(year, 11, 2, "All Souls' Day"),
        _fixed(year, 11, 15, "Republic Proclamation Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _chile_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, -1, "Holy Saturday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 21, "Navy Day"),
        _fixed(year, 6, _chile_winter_solstice_day(year), "National Indigenous Peoples Day"),
        _fixed(year, 7, 16, "Our Lady of Mount Carmel"),
        _fixed(year, 8, 15, "Assumption of Mary"),
        _fixed(year, 9, 18, "Independence Day"),
        _fixed(year, 9, 19, "Army Day"),
        _fixed(year, 10, 12, "Encounter of Two Worlds"),
        _fixed(year, 10, 31, "Reformation Day"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _chile_winter_solstice_day(year: int) -> int:
    solstice_days = {
        2020: 20,
        2021: 21,
        2022: 21,
        2023: 21,
        2024: 20,
        2025: 21,
        2026: 21,
        2027: 21,
        2028: 20,
        2029: 21,
        2030: 21,
    }
    return solstice_days.get(year, 21)


def _colombia_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _monday_on_or_after(date(year, 1, 6), "Epiphany observed"),
        _monday_on_or_after(date(year, 3, 19), "Saint Joseph's Day observed"),
        _relative(easter, -3, "Maundy Thursday"),
        _relative(easter, -2, "Good Friday"),
        _fixed(year, 5, 1, "Labour Day"),
        _relative(easter, 43, "Ascension Day observed"),
        _relative(easter, 64, "Corpus Christi observed"),
        _relative(easter, 71, "Sacred Heart observed"),
        _monday_on_or_after(date(year, 6, 29), "Saint Peter and Saint Paul observed"),
        _fixed(year, 7, 20, "Independence Day"),
        _fixed(year, 8, 7, "Battle of Boyaca"),
        _monday_on_or_after(date(year, 8, 15), "Assumption of Mary observed"),
        _monday_on_or_after(date(year, 10, 12), "Columbus Day observed"),
        _monday_on_or_after(date(year, 11, 1), "All Saints' Day observed"),
        _monday_on_or_after(date(year, 11, 11), "Independence of Cartagena observed"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _peru_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -3, "Maundy Thursday"),
        _relative(easter, -2, "Good Friday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 6, 7, "Battle of Arica and Flag Day"),
        _fixed(year, 6, 29, "Saint Peter and Saint Paul"),
        _fixed(year, 7, 28, "Independence Day"),
        _fixed(year, 7, 29, "Independence Day holiday"),
        _fixed(year, 8, 6, "Battle of Junin"),
        _fixed(year, 8, 30, "Saint Rose of Lima"),
        _fixed(year, 10, 8, "Battle of Angamos"),
        _fixed(year, 11, 1, "All Saints' Day"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 9, "Battle of Ayacucho"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _uruguay_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -48, "Carnival Monday"),
        _relative(easter, -47, "Carnival Tuesday"),
        _relative(easter, -3, "Tourism Week Thursday"),
        _relative(easter, -2, "Tourism Week Friday"),
        _fixed(year, 4, 19, "Landing of the Thirty-Three Orientals"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 18, "Battle of Las Piedras"),
        _fixed(year, 6, 19, "Birth of Artigas"),
        _fixed(year, 7, 18, "Constitution Day"),
        _fixed(year, 8, 25, "Independence Day"),
        _fixed(year, 10, 12, "Day of the Americas"),
        _fixed(year, 11, 2, "All Souls' Day"),
        _fixed(year, 12, 25, "Christmas Day / Family Day"),
    ]


def _mexico_holidays(year: int) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _nth_weekday(year, 2, 0, 1, "Constitution Day"),
        _nth_weekday(year, 3, 0, 3, "Benito Juarez Day"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 9, 16, "Independence Day"),
        _nth_weekday(year, 11, 0, 3, "Revolution Day"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _argentina_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _relative(easter, -48, "Carnival Monday"),
        _relative(easter, -47, "Carnival Tuesday"),
        _fixed(year, 3, 24, "Day of Remembrance"),
        _fixed(year, 4, 2, "Malvinas Day"),
        _relative(easter, -2, "Good Friday"),
        _fixed(year, 5, 1, "Labour Day"),
        _fixed(year, 5, 25, "May Revolution Day"),
        _fixed(year, 7, 9, "Independence Day"),
        _fixed(year, 12, 8, "Immaculate Conception"),
        _fixed(year, 12, 25, "Christmas Day"),
    ]


def _australia_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 26, "Australia Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 4, 25, "Anzac Day"),
        _nth_weekday(year, 6, 0, 2, "King's Birthday"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Boxing Day"),
    ]


def _new_zealand_holidays(year: int, easter: date) -> list[Holiday]:
    return [
        _fixed(year, 1, 1, "New Year's Day"),
        _fixed(year, 1, 2, "Day after New Year's Day"),
        _fixed(year, 2, 6, "Waitangi Day"),
        _relative(easter, -2, "Good Friday"),
        _relative(easter, 1, "Easter Monday"),
        _fixed(year, 4, 25, "Anzac Day"),
        _nth_weekday(year, 6, 0, 1, "King's Birthday"),
        _nth_weekday(year, 10, 0, 4, "Labour Day"),
        _fixed(year, 12, 25, "Christmas Day"),
        _fixed(year, 12, 26, "Boxing Day"),
    ]
