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


def test_weekly_sample_produces_probable_country_candidates():
    result = detect(load_sample("weekfull-chan1.json"), top=5)

    assert result["probable_countries"]
    assert result["probable_countries"][0]["kind"] == "country"
    assert (
        result["probable_countries"][0]["probability"]
        >= result["probable_countries"][1]["probability"]
    )
    assert any(
        country["evidence"]["multiple_timezone_match"]
        for country in result["probable_countries"]
    )
    top_offsets = {item["id"] for item in result["results"]}
    for country in result["probable_countries"]:
        assert set(country["matched_timezone_offsets"]) <= top_offsets


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
    result = detect(load_sample("year.json"), top=120, holiday_profile="public-worker")

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
    result = detect(load_sample("year.json"), top=120, holiday_profile="public-worker")

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


def test_weekly_analysis_uses_inferred_local_offset():
    data = []
    for day in range(7):
        for hour in range(24):
            count = 10 if day <= 4 and 0 <= hour <= 7 else 1
            data.append({"day": day, "hour": hour, "count": count})

    result = detect(data, kind="weekly")

    assert result["analysis"]["timezone_offset"] == result["results"][0]["id"]
    assert result["analysis"]["activity_type"] != "vacation-time"
    assert "inferred offset" in result["analysis"]["basis"]


def test_standard_holiday_profile_includes_south_american_regions():
    candidates = _candidate_holidays(2026)

    assert {"AR", "BR", "CL", "CO", "PE", "UY"} <= set(candidates)
    assert any(
        holiday.day.isoformat() == "2026-07-28" and holiday.name == "Independence Day"
        for holiday in candidates["PE"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-09-18" and holiday.name == "Independence Day"
        for holiday in candidates["CL"][2]
    )


def test_colombia_holidays_use_source_date_observed_mondays():
    candidates = _candidate_holidays(2026)
    dates_by_name = {
        holiday.name: holiday.day.isoformat() for holiday in candidates["CO"][2]
    }

    assert dates_by_name["Saint Peter and Saint Paul observed"] == "2026-06-29"
    assert dates_by_name["Columbus Day observed"] == "2026-10-12"
    assert dates_by_name["Assumption of Mary observed"] == "2026-08-17"
    assert dates_by_name["All Saints' Day observed"] == "2026-11-02"
    assert dates_by_name["Independence of Cartagena observed"] == "2026-11-16"


def test_chile_indigenous_peoples_day_uses_winter_solstice_date():
    candidates = _candidate_holidays(2026)

    assert any(
        holiday.day.isoformat() == "2026-06-21"
        and holiday.name == "National Indigenous Peoples Day"
        for holiday in candidates["CL"][2]
    )


def test_public_worker_holiday_profile_adds_south_american_references():
    result = detect(load_sample("year.json"), top=120, holiday_profile="public-worker")

    ids = {item["id"] for item in result["results"]}
    assert {
        "AR-PUBLIC-WORKER",
        "BR-PUBLIC-WORKER",
        "CL-PUBLIC-WORKER",
        "CO-PUBLIC-WORKER",
        "PE-PUBLIC-WORKER",
        "UY-PUBLIC-WORKER",
    } <= ids


def test_south_america_public_worker_profile_includes_bridge_closures():
    candidates = _candidate_holidays(2026, include_public_worker=True)
    dates = {
        holiday.day.isoformat()
        for holiday in candidates["BR-PUBLIC-WORKER"][2]
        if "public-sector closure" in holiday.name
    }

    assert {"2026-01-02", "2026-12-24", "2026-12-31"} <= dates


def test_standard_holiday_profile_includes_arabic_region_and_israel_references():
    candidates = _candidate_holidays(2026)

    assert {
        "AE",
        "SA",
        "EG",
        "IL",
        "QA",
        "KW",
        "BH",
        "OM",
        "JO",
        "LB",
        "MA",
        "TN",
        "DZ",
    } <= set(candidates)
    assert any(
        holiday.day.isoformat() == "2026-12-02" and holiday.name == "National Day"
        for holiday in candidates["AE"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-02-22" and holiday.name == "Founding Day"
        for holiday in candidates["SA"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-09-21"
        and holiday.name == "Yom Kippur reference day"
        for holiday in candidates["IL"][2]
    )


def test_israel_holiday_references_follow_hebrew_calendar_by_year():
    candidates_2025 = _candidate_holidays(2025)
    candidates_2027 = _candidate_holidays(2027)

    israel_2025 = {
        (holiday.day.isoformat(), holiday.name) for holiday in candidates_2025["IL"][2]
    }
    israel_2027 = {
        (holiday.day.isoformat(), holiday.name) for holiday in candidates_2027["IL"][2]
    }

    assert ("2025-10-02", "Yom Kippur reference day") in israel_2025
    assert ("2027-10-11", "Yom Kippur reference day") in israel_2027
    assert ("2025-09-21", "Yom Kippur reference day") not in israel_2025
    assert ("2027-09-21", "Yom Kippur reference day") not in israel_2027


def test_arabic_region_profiles_include_eid_vacation_windows():
    candidates = _candidate_holidays(2026)
    uae_eid_al_fitr = {
        holiday.day.isoformat()
        for holiday in candidates["AE"][2]
        if holiday.name.startswith("Eid al-Fitr")
    }
    saudi_eid_al_adha = {
        holiday.day.isoformat()
        for holiday in candidates["SA"][2]
        if holiday.name.startswith("Eid al-Adha")
    }

    assert uae_eid_al_fitr == {"2026-03-20", "2026-03-21", "2026-03-22"}
    assert saudi_eid_al_adha == {
        "2026-05-27",
        "2026-05-28",
        "2026-05-29",
        "2026-05-30",
    }


def test_standard_holiday_profile_includes_expanded_asia_pacific_regions():
    candidates = _candidate_holidays(2026)

    assert {"JP", "KR", "KP", "CN", "VN", "TH", "SG", "MY", "PH", "IN"} <= set(
        candidates
    )
    assert any(
        holiday.day.isoformat() == "2026-04-15" and holiday.name == "Day of the Sun"
        for holiday in candidates["KP"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-04-13" and holiday.name == "Songkran"
        for holiday in candidates["TH"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-09-02" and holiday.name == "National Day"
        for holiday in candidates["VN"][2]
    )


def test_korean_holiday_profiles_include_lunar_seollal_and_chuseok_windows():
    candidates = _candidate_holidays(2026)
    south_korea_seollal = {
        holiday.day.isoformat()
        for holiday in candidates["KR"][2]
        if holiday.name == "Seollal"
    }
    south_korea_chuseok = {
        holiday.day.isoformat()
        for holiday in candidates["KR"][2]
        if holiday.name == "Chuseok"
    }
    north_korea_lunar = {
        (holiday.day.isoformat(), holiday.name) for holiday in candidates["KP"][2]
    }

    assert south_korea_seollal == {"2026-02-16", "2026-02-17", "2026-02-18"}
    assert south_korea_chuseok == {"2026-09-24", "2026-09-25", "2026-09-26"}
    assert ("2026-02-17", "Korean Lunar New Year") in north_korea_lunar
    assert ("2026-09-25", "Chuseok") in north_korea_lunar


def test_standard_holiday_profile_includes_expanded_african_regions():
    candidates = _candidate_holidays(2026)

    assert {"NG", "GH", "CI", "SN", "KE", "ET", "ZA"} <= set(candidates)
    assert any(
        holiday.day.isoformat() == "2026-06-12" and holiday.name == "Democracy Day"
        for holiday in candidates["NG"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-08-10"
        and holiday.name == "National Women's Day observed"
        for holiday in candidates["ZA"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-06-01" and holiday.name == "Madaraka Day"
        for holiday in candidates["KE"][2]
    )


def test_west_african_profiles_include_shared_eid_windows():
    candidates = _candidate_holidays(2026)
    nigeria_eid_al_fitr = {
        holiday.day.isoformat()
        for holiday in candidates["NG"][2]
        if holiday.name.startswith("Eid al-Fitr")
    }
    senegal_eid_al_adha = {
        holiday.day.isoformat()
        for holiday in candidates["SN"][2]
        if holiday.name.startswith("Eid al-Adha")
    }

    assert nigeria_eid_al_fitr == {"2026-03-20", "2026-03-21"}
    assert senegal_eid_al_adha == {
        "2026-05-27",
        "2026-05-28",
        "2026-05-29",
        "2026-05-30",
    }


def test_standard_holiday_profile_includes_expanded_north_america_regions():
    candidates = _candidate_holidays(2026)

    assert {"US", "CA", "MX", "CR", "GT", "PA", "CU", "DO"} <= set(candidates)
    assert any(
        holiday.day.isoformat() == "2026-09-15" and holiday.name == "Independence Day"
        for holiday in candidates["CR"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-11-03" and holiday.name == "Separation Day"
        for holiday in candidates["PA"][2]
    )


def test_standard_holiday_profile_includes_expanded_europe_regions():
    candidates = _candidate_holidays(2026)

    assert {"IS", "LU", "EE", "LV", "LT", "HR", "SI", "BA"} <= set(candidates)
    assert any(
        holiday.day.isoformat() == "2026-06-17" and holiday.name == "National Day"
        for holiday in candidates["IS"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-02-24" and holiday.name == "Independence Day"
        for holiday in candidates["EE"][2]
    )
    assert any(
        holiday.day.isoformat() == "2026-11-18" and holiday.name == "Remembrance Day"
        for holiday in candidates["HR"][2]
    )


def test_json_timestamp_list_is_detected_and_aggregated_as_weekly_activity():
    data = [
        "2026-01-05T09:15:00Z",
        "2026-01-05T09:45:00+00:00",
        "2026-01-06 10:00:00 UTC",
        1767603600,
    ]

    result = detect(data, top=3)

    assert result["input_type"] == "timestamp_list"
    assert result["signals"]["timestamps_seen"] == 4
    assert result["results"][0]["kind"] == "timezone"
    assert "Unix epoch seconds" in result["assumptions"][1]


def test_timestamp_list_can_be_forced():
    result = detect(["2026-01-05T09:15:00Z"], kind="timestamps", top=1)

    assert result["input_type"] == "timestamp_list"
    assert len(result["results"]) == 1
