import json
from pathlib import Path

from tempolocus import detect
from tempolocus.core import _candidate_holidays

ROOT = Path(__file__).resolve().parents[1]


def load_sample(name):
    return json.loads((ROOT / "samples" / name).read_text(encoding="utf-8"))


def test_weekly_sample_produces_timezone_candidates():
    result = detect(load_sample("weekfull-chan1.json"), top=3)

    assert result["input_type"] == "weekly_timeseries"
    assert len(result["results"]) == 3
    assert result["results"][0]["kind"] == "timezone"
    assert result["results"][0]["probability"] >= result["results"][1]["probability"]


def test_yearly_sample_produces_region_candidates():
    result = detect(load_sample("year.json"), top=5)

    assert result["input_type"] == "yearly_daily_activity"
    assert len(result["results"]) == 5
    assert result["results"][0]["kind"] == "region"
    assert result["results"][0]["probability"] >= result["results"][1]["probability"]


def test_kind_can_be_forced():
    result = detect(load_sample("year-chan1.json"), kind="yearly", top=2)

    assert result["input_type"] == "yearly_daily_activity"
    assert len(result["results"]) == 2


def test_public_worker_holiday_profile_adds_sector_references():
    result = detect(load_sample("year.json"), top=40, holiday_profile="public-worker")

    assert result["signals"]["holiday_profile"] == "public-worker"
    ids = {item["id"] for item in result["results"]}
    assert "US-PUBLIC-WORKER" in ids
    assert "ES-PUBLIC-WORKER" in ids
    assert "FR-PUBLIC-WORKER" in ids


def test_standard_holiday_profile_omits_public_worker_references():
    result = detect(load_sample("year.json"), top=40)

    ids = {item["id"] for item in result["results"]}
    assert "US-PUBLIC-WORKER" not in ids


def test_standard_holiday_profile_includes_orthodox_regions():
    candidates = _candidate_holidays(2024)

    assert {"BG", "RS", "UA", "RU"} <= set(candidates)
    assert any(
        holiday.day.isoformat() == "2024-05-05"
        and holiday.name == "Orthodox Easter Sunday"
        for holiday in candidates["RU"][2]
    )


def test_public_worker_holiday_profile_adds_china_and_russia_references():
    result = detect(load_sample("year.json"), top=50, holiday_profile="public-worker")

    ids = {item["id"] for item in result["results"]}
    assert "CN-PUBLIC-WORKER" in ids
    assert "RU-PUBLIC-WORKER" in ids


def test_china_public_worker_profile_includes_spring_festival_window():
    candidates = _candidate_holidays(2026, include_public_worker=True)
    dates = {
        holiday.day.isoformat()
        for holiday in candidates["CN-PUBLIC-WORKER"][2]
        if "Spring Festival" in holiday.name
    }

    assert dates == {
        "2026-02-17",
        "2026-02-18",
        "2026-02-19",
        "2026-02-20",
        "2026-02-21",
        "2026-02-22",
        "2026-02-23",
    }


def test_yearly_activity_signal_defaults_to_lack_of_activity():
    result = detect(load_sample("year.json"), top=5)

    assert result["signals"]["activity_signal"] == "lack"
    assert {item["signal"] for item in result["results"]} == {"holiday_drop"}


def test_yearly_activity_signal_can_match_activity_peaks():
    result = detect(load_sample("year.json"), top=5, activity_signal="peak")

    assert result["signals"]["activity_signal"] == "peak"
    assert {item["signal"] for item in result["results"]} == {"holiday_spike"}


def test_weekly_analysis_classifies_work_time():
    data = []
    for day in range(7):
        for hour in range(24):
            count = 10 if day <= 4 and 9 <= hour <= 16 else 1
            data.append({"day": day, "hour": hour, "count": count})

    result = detect(data, kind="weekly")

    assert result["analysis"]["activity_type"] == "work-time"
    assert (
        result["analysis"]["shares"]["work_time"]
        > result["analysis"]["shares"]["vacation_time"]
    )


def test_weekly_analysis_classifies_vacation_time():
    data = []
    for day in range(7):
        for hour in range(24):
            count = 10 if day >= 5 or hour >= 18 else 1
            data.append({"day": day, "hour": hour, "count": count})

    result = detect(data, kind="weekly")

    assert result["analysis"]["activity_type"] == "vacation-time"
    assert (
        result["analysis"]["shares"]["vacation_time"]
        > result["analysis"]["shares"]["work_time"]
    )


def test_weekly_analysis_classifies_mixed_time():
    data = []
    for day in range(7):
        for hour in range(24):
            data.append({"day": day, "hour": hour, "count": 1})

    result = detect(data, kind="weekly")

    assert result["analysis"]["activity_type"] == "mixed-time"
