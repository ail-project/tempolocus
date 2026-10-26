"""Country coverage and reference-calendar regression checks."""

import unittest
from datetime import date

from tempolocus import detect
from tempolocus.core import _candidate_holidays
from tempolocus.country_references import fixed_date_references


# 193 UN members, the two UN observer states, Kosovo and Taiwan.
EXPECTED_COUNTRIES = set("""
AF AL DZ AD AO AG AR AM AU AT AZ BS BH BD BB BY BE BZ BJ BT BO BA BW BR BN BG
BF BI CV KH CM CA CF TD CL CN CO KM CG CD CR CI HR CU CY CZ DK DJ DM DO EC EG
SV GQ ER EE SZ ET FJ FI FR GA GM GE DE GH GR GD GT GN GW GY HT VA HN HU IS IN
ID IR IQ IE IL IT JM JP JO KZ KE KI KP KR KW KG LA LV LB LS LR LY LI LT LU MG
MW MY MV ML MT MH MR MU MX FM MD MC MN ME MA MZ MM NA NR NP NL NZ NI NE NG MK
NO OM PK PW PS PA PG PY PE PH PL PT QA RO RU RW KN LC VC WS SM ST SA SN RS SC
SL SG SK SI SB SO ZA SS ES LK SD SR SE CH SY TW TJ TZ TH TL TG TO TT TN TR TM
TV UG UA AE GB US UY UZ VU VE VN YE ZM ZW XK
""".split())


class CountryCoverageTests(unittest.TestCase):
    def test_all_countries_in_both_profiles(self):
        for public_worker in (False, True):
            candidates = _candidate_holidays(2026, public_worker)
            self.assertEqual(EXPECTED_COUNTRIES, {k for k in candidates if len(k) == 2})

    def test_partial_calendars_are_explicit_and_dates_stay_in_year(self):
        for year in (2024, 2026, 2035):
            candidates = _candidate_holidays(year)
            rows = list(fixed_date_references(year))
            self.assertEqual(len(rows), len({row[0] for row in rows}))
            for code, _label, references in rows:
                self.assertIn('(partial)', candidates[code][1])
                self.assertTrue(references)
                self.assertTrue(all(day.year == year for day, _ in references))

    def test_country_specific_dates(self):
        candidates = _candidate_holidays(2026)
        for code, month, day, name in (
            ('ID', 8, 17, 'Independence Day'),
            ('PK', 3, 23, 'Pakistan Day'),
            ('EC', 5, 24, 'Battle of Pichincha'),
            ('TZ', 4, 26, 'Union Day'),
            ('MT', 9, 21, 'Independence Day'),
            ('VU', 7, 30, 'Independence Day'),
        ):
            self.assertIn((date(2026, month, day), name),
                          {(h.day, h.name) for h in candidates[code][2]})

    def test_existing_detailed_calendars_remain_detailed(self):
        candidates = _candidate_holidays(2026, True)
        self.assertEqual('France', candidates['FR'][1])
        self.assertIn('IR-SHIA', candidates)
        self.assertIn('CN-PUBLIC-WORKER', candidates)
        self.assertTrue(any(h.name == 'Bastille Day' for h in candidates['FR'][2]))

    def test_new_country_is_available_in_yearly_inference(self):
        result = detect({'year': 2026, 'max': 10,
                         'nb': [['2026-01-01', 10], ['2026-12-31', 10]]}, top=1000)
        indexed = {item['id']: item for item in result['results']}
        self.assertIn('ID', indexed)
        self.assertIn('(partial)', indexed['ID']['label'])


if __name__ == '__main__':
    unittest.main()
