import json
from pathlib import Path

from tempolocus import detect


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
