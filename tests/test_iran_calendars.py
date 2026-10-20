from datetime import date, timedelta

import pytest

from tempolocus import detect
from tempolocus.core import (
    _candidate_holidays,
    _iran_shia_holidays,
    _iran_solar_holidays,
    _solar_hijri_new_year,
    _zoroastrian_holidays,
)


@pytest.mark.parametrize(
    "year,expected",
    [(2023, "2023-03-21"), (2024, "2024-03-20"),
     (2025, "2025-03-21"), (2026, "2026-03-21"),
     (2028, "2028-03-20"), (2029, "2029-03-20")],
)
def test_nowruz_tracks_solar_hijri_leap_years(year, expected):
    assert _solar_hijri_new_year(year).isoformat() == expected


def test_iran_solar_holidays_cross_gregorian_year_boundary():
    holidays = {holiday.name: holiday.day for holiday in _iran_solar_holidays(2025)}
    assert holidays["Islamic Revolution Day"] == date(2025, 2, 10)
    assert holidays["Oil Nationalization Day"] == date(2025, 3, 19)
    assert holidays["Solar Hijri leap-year end"] == date(2025, 3, 20)
    assert holidays["Nowruz day 1"] == date(2025, 3, 21)
    assert holidays["Nowruz day 4"] == date(2025, 3, 24)
    assert holidays["Islamic Republic Day"] == date(2025, 4, 1)
    assert holidays["Nature's Day / Sizdah Bedar"] == date(2025, 4, 2)
    assert holidays["Death of Imam Khomeini"] == date(2025, 6, 4)
    assert holidays["15 Khordad Uprising"] == date(2025, 6, 5)
    assert not any("leap-year end" in h.name for h in _iran_solar_holidays(2026))


def test_iran_shia_calendar_includes_distinct_observances_and_short_eids():
    holidays = _iran_shia_holidays(2026)
    names = {h.name.removesuffix(" (estimated)") for h in holidays}
    assert len(names) == 17
    assert {"Tasua", "Ashura", "Arbaeen", "Eid al-Ghadir",
            "Martyrdom of Fatima", "Martyrdom of Imam Reza"} <= names
    assert {h.day for h in holidays if h.name.startswith("Eid al-Fitr")} == {
        date(2026, 3, 20), date(2026, 3, 21)
    }
    assert {h.day for h in holidays if h.name.startswith("Eid al-Adha")} == {
        date(2026, 5, 27)
    }
    assert {h.day for h in holidays if h.name.startswith("Birthday of Prophet")} == {
        date(2026, 8, 31)
    }
    assert all(h.name.endswith("(estimated)") for h in holidays)


def test_shia_lunar_calendar_handles_two_occurrences_in_one_year():
    birthdays = [h.day for h in _iran_shia_holidays(2026)
                 if h.name.startswith("Birthday of Imam Ali")]
    assert birthdays == [date(2026, 1, 2), date(2026, 12, 23)]
    # The existing Arabian helper's narrow year approximation misses 1900.
    assert len(_iran_shia_holidays(1900)) >= 17


@pytest.mark.parametrize(
    "variant,expected",
    [("Bastani", "2024-03-20"), ("Fasli", "2024-03-21"),
     ("Qadimi", "2024-07-16"), ("Shahanshahi", "2024-08-15")],
)
def test_zoroastrian_calendars_keep_their_distinct_new_years(variant, expected):
    holidays = _zoroastrian_holidays(2024, variant)
    nowruz = next(h.day for h in holidays if h.name.startswith("Nowruz"))
    assert nowruz.isoformat() == expected
    birth = next(h.day for h in holidays if h.name.startswith("Khordad Sal"))
    assert birth == nowruz + timedelta(days=5)
    assert all(h.day.year == 2024 for h in holidays)
    # A Gregorian leap year can include an extra day from festivals in two
    # different Zoroastrian years; the Bastani December festival shifts here.
    expected_gahambar_days = 31 if variant == "Bastani" else 30
    assert len([h for h in holidays if "Gahambar" in h.name]) == expected_gahambar_days


def test_nonintercalating_zoroastrian_years_drift_instead_of_resetting():
    for variant, expected in [("Qadimi", date(2025, 7, 16)),
                              ("Shahanshahi", date(2025, 8, 15))]:
        holidays = _zoroastrian_holidays(2025, variant)
        assert next(h.day for h in holidays if h.name.startswith("Nowruz")) == expected
    fasli = _zoroastrian_holidays(2026, "Fasli")
    assert next(h.day for h in fasli if h.name.startswith("Zartosht")) == date(2026, 12, 26)


def test_solar_model_range_does_not_break_other_region_candidates():
    assert _solar_hijri_new_year(400) is None
    assert _iran_solar_holidays(400) == []
    assert _zoroastrian_holidays(400, "Bastani") == []


def test_iran_references_are_available_in_both_holiday_profiles():
    required = {"IR", "IR-SOLAR", "IR-SHIA"} | {
        f"IR-ZOROASTRIAN-{variant}"
        for variant in ("BASTANI", "FASLI", "QADIMI", "SHAHANSHAHI")
    }
    for public_worker in (False, True):
        candidates = _candidate_holidays(2026, include_public_worker=public_worker)
        assert required <= candidates.keys()
        combined = {(h.day, h.name) for h in candidates["IR"][2]}
        assert combined == {(h.day, h.name) for key in ("IR-SOLAR", "IR-SHIA")
                            for h in candidates[key][2]}


@pytest.mark.parametrize("signal,holiday_count,normal_count", [("lack", 0, 100), ("peak", 100, 0)])
def test_iran_holidays_are_used_by_yearly_inference(signal, holiday_count, normal_count):
    iran_days = {h.day for h in _candidate_holidays(2026)["IR"][2]}
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
    data = {"year": 2026, "nb": [
        [day.isoformat(), holiday_count if day in iran_days else normal_count]
        for day in days
    ]}
    result = detect(data, top=200, activity_signal=signal)
    candidates = {item["id"]: item for item in result["results"]}
    assert candidates["IR"]["score"] > candidates["FR"]["score"]
    assert candidates["IR"]["evidence"]["matched_holidays"]
    assert candidates["IR"]["signal"] == ("holiday_drop" if signal == "lack" else "holiday_spike")
    assert "IR-ZOROASTRIAN-QADIMI" in candidates
