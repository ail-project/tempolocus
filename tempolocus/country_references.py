"""Fixed-date reference signals for countries without a detailed calendar.

These are deliberately partial modern calendars, not statutory holiday lists.
National-day dates can be checked against https://en.wikipedia.org/wiki/National_day
and each country's public-holiday calendar. Movable holidays, observed-day
substitutions, historical regimes and one-off closures are not reconstructed.
Keep these separate from the detailed calendars so callers can report coverage.
"""

# ISO 3166-1 alpha-2 codes, plus XK for Kosovo. Each row is
# code | display name | MM-DD holiday name; ...
FIXED_DATE_REFERENCES = """
AF|Afghanistan|08-19 Independence Day
AL|Albania|03-14 Summer Day;11-28 Independence Day;11-29 Liberation Day
AD|Andorra|03-14 Constitution Day;09-08 Our Lady of Meritxell
AO|Angola|02-04 Liberation Day;09-17 National Heroes Day;11-11 Independence Day
AG|Antigua and Barbuda|11-01 Independence Day;12-09 National Heroes Day
AM|Armenia|01-28 Army Day;05-28 Republic Day;09-21 Independence Day
AZ|Azerbaijan|05-28 Independence Day;06-15 National Salvation Day;11-08 Victory Day
BS|Bahamas|07-10 Independence Day;12-26 Boxing Day
BD|Bangladesh|02-21 Language Martyrs Day;03-26 Independence Day;12-16 Victory Day
BB|Barbados|04-28 National Heroes Day;08-01 Emancipation Day;11-30 Independence Day
BY|Belarus|05-09 Victory Day;07-03 Independence Day;11-07 October Revolution Day
BZ|Belize|09-10 Saint George's Caye Day;09-21 Independence Day
BJ|Benin|01-10 Traditional Religions Day;08-01 Independence Day
BT|Bhutan|02-21 King's Birthday;12-17 National Day
BO|Bolivia|01-22 Plurinational State Day;08-06 Independence Day
BW|Botswana|07-01 Sir Seretse Khama Day;09-30 Botswana Day
BN|Brunei|02-23 National Day;07-15 Sultan's Birthday
BF|Burkina Faso|08-05 Independence Day;12-11 Republic Day
BI|Burundi|02-05 Unity Day;07-01 Independence Day;10-21 President Ndadaye Day
CV|Cabo Verde|01-20 National Heroes Day;07-05 Independence Day
KH|Cambodia|01-07 Victory Day;09-24 Constitution Day;11-09 Independence Day
CM|Cameroon|02-11 Youth Day;05-20 National Day
CF|Central African Republic|03-29 Boganda Day;08-13 Independence Day;12-01 Republic Day
TD|Chad|08-11 Independence Day;12-01 Freedom and Democracy Day
KM|Comoros|07-06 Independence Day;11-12 Maore Day
CG|Republic of the Congo|08-15 Independence Day;11-28 Republic Day
CD|Democratic Republic of the Congo|01-17 Lumumba Day;06-30 Independence Day
CY|Cyprus|04-01 National Day;10-01 Independence Day
DJ|Djibouti|06-27 Independence Day
DM|Dominica|11-03 Independence Day;11-04 Community Service Day
EC|Ecuador|05-24 Battle of Pichincha;08-10 First Cry of Independence;10-09 Guayaquil Independence Day
SV|El Salvador|08-06 Feast of the Divine Saviour;09-15 Independence Day
GQ|Equatorial Guinea|08-03 Freedom Day;10-12 Independence Day
ER|Eritrea|05-24 Independence Day;06-20 Martyrs Day;09-01 Revolution Day
SZ|Eswatini|04-19 King's Birthday;09-06 Independence Day
FJ|Fiji|09-07 Constitution Day;10-10 Fiji Day
GA|Gabon|08-17 Independence Day
GM|Gambia|02-18 Independence Day
GE|Georgia|04-09 National Unity Day;05-26 Independence Day;11-23 Saint George's Day
GD|Grenada|02-07 Independence Day;10-25 Thanksgiving Day
GN|Guinea|10-02 Independence Day
GW|Guinea-Bissau|01-20 National Heroes Day;09-24 Independence Day
GY|Guyana|02-23 Republic Day;05-26 Independence Day;08-01 Emancipation Day
HT|Haiti|01-01 Independence Day;05-18 Flag Day;11-18 Battle of Vertieres
HN|Honduras|09-15 Independence Day
ID|Indonesia|06-01 Pancasila Day;08-17 Independence Day
IQ|Iraq|01-06 Army Day;10-03 National Day;12-10 Victory Day
JM|Jamaica|08-01 Emancipation Day;08-06 Independence Day
KZ|Kazakhstan|05-07 Defender of the Fatherland Day;08-30 Constitution Day;10-25 Republic Day;12-16 Independence Day
KI|Kiribati|07-12 Independence Day
XK|Kosovo|02-17 Independence Day;04-09 Constitution Day
KG|Kyrgyzstan|05-05 Constitution Day;08-31 Independence Day
LA|Laos|03-08 International Women's Day;12-02 National Day
LS|Lesotho|03-11 Moshoeshoe Day;07-17 King's Birthday;10-04 Independence Day
LR|Liberia|03-15 Joseph Jenkins Roberts Birthday;07-26 Independence Day;08-24 Flag Day
LY|Libya|02-17 Revolution Day;09-16 Martyrs Day;12-24 Independence Day
LI|Liechtenstein|08-15 National Day;12-08 Immaculate Conception
MG|Madagascar|03-29 Martyrs Day;06-26 Independence Day
MW|Malawi|03-03 Martyrs Day;07-06 Independence Day
MV|Maldives|07-26 Independence Day;11-11 Republic Day
ML|Mali|01-20 Army Day;09-22 Independence Day
MT|Malta|03-31 Freedom Day;06-07 Sette Giugno;09-08 Victory Day;09-21 Independence Day;12-13 Republic Day
MH|Marshall Islands|05-01 Constitution Day;11-17 President's Day
MR|Mauritania|11-28 Independence Day
MU|Mauritius|02-01 Abolition of Slavery;03-12 Independence and Republic Day;11-02 Arrival of Indentured Labourers
FM|Micronesia|05-10 Constitution Day;11-03 Independence Day
MD|Moldova|08-27 Independence Day;08-31 National Language Day
MC|Monaco|01-27 Saint Devota's Day;11-19 National Day
MN|Mongolia|07-11 Naadam;07-12 Naadam;07-13 Naadam;11-26 Republic Day
ME|Montenegro|05-21 Independence Day;05-22 Independence Day;07-13 Statehood Day;07-14 Statehood Day
MZ|Mozambique|02-03 Heroes Day;06-25 Independence Day;09-25 Armed Forces Day;10-04 Peace and Reconciliation Day
MM|Myanmar|01-04 Independence Day;02-12 Union Day;03-27 Armed Forces Day
NA|Namibia|03-21 Independence Day;05-04 Cassinga Day;08-26 Heroes Day
NR|Nauru|01-31 Independence Day;10-26 Angam Day
NP|Nepal|09-20 Constitution Day
NI|Nicaragua|09-14 Battle of San Jacinto;09-15 Independence Day
NE|Niger|04-24 Concord Day;08-03 Independence Day;12-18 Republic Day
MK|North Macedonia|08-02 Republic Day;09-08 Independence Day;10-11 Uprising Day
PK|Pakistan|03-23 Pakistan Day;08-14 Independence Day;12-25 Quaid-e-Azam Day
PW|Palau|07-09 Constitution Day;10-01 Independence Day
PS|Palestine|11-15 Independence Day
PG|Papua New Guinea|07-23 National Remembrance Day;08-26 National Repentance Day;09-16 Independence Day
PY|Paraguay|05-14 Independence Day;05-15 Independence Day;06-12 Chaco Armistice Day
RW|Rwanda|02-01 Heroes Day;07-01 Independence Day;07-04 Liberation Day
KN|Saint Kitts and Nevis|09-16 National Heroes Day;09-19 Independence Day
LC|Saint Lucia|02-22 Independence Day;12-13 National Day
VC|Saint Vincent and the Grenadines|03-14 National Heroes Day;10-27 Independence Day
WS|Samoa|06-01 Independence Day
SM|San Marino|02-05 Liberation Day;09-03 Foundation Day;10-01 Investiture of Captains Regent
ST|Sao Tome and Principe|02-03 Martyrs Day;07-12 Independence Day;09-06 Armed Forces Day
SC|Seychelles|06-18 Constitution Day;06-29 Independence Day
SL|Sierra Leone|04-27 Independence Day
SB|Solomon Islands|07-07 Independence Day
SO|Somalia|06-26 Independence Day;07-01 Republic Day
SS|South Sudan|05-16 SPLA Day;07-09 Independence Day;07-30 Martyrs Day
LK|Sri Lanka|02-04 Independence Day
SD|Sudan|01-01 Independence Day
SR|Suriname|07-01 Emancipation Day;11-25 Independence Day
SY|Syria|04-17 Evacuation Day;05-06 Martyrs Day
TW|Taiwan|02-28 Peace Memorial Day;10-10 National Day
TJ|Tajikistan|06-27 National Unity Day;09-09 Independence Day;11-06 Constitution Day
TZ|Tanzania|04-26 Union Day;10-14 Nyerere Day;12-09 Independence Day
TL|Timor-Leste|05-20 Restoration of Independence;11-28 Proclamation of Independence
TG|Togo|04-27 Independence Day
TO|Tonga|06-04 Emancipation Day;07-04 King's Birthday;11-04 Constitution Day
TT|Trinidad and Tobago|08-01 Emancipation Day;08-31 Independence Day;09-24 Republic Day
TR|Türkiye|04-23 National Sovereignty and Children's Day;05-19 Youth and Sports Day;08-30 Victory Day;10-29 Republic Day
TM|Turkmenistan|05-18 Constitution Day;09-27 Independence Day;12-12 Neutrality Day
TV|Tuvalu|10-01 Independence Day;10-02 Independence Day
UG|Uganda|01-26 Liberation Day;06-09 Heroes Day;10-09 Independence Day
UZ|Uzbekistan|09-01 Independence Day;10-01 Teachers Day;12-08 Constitution Day
VU|Vanuatu|07-30 Independence Day;10-05 Constitution Day
VA|Vatican City|02-11 Lateran Treaty Day;06-29 Saints Peter and Paul
VE|Venezuela|04-19 Declaration of Independence;07-05 Independence Day;07-24 Simon Bolivar Birthday
YE|Yemen|05-22 Unity Day;09-26 Revolution Day;10-14 Liberation Day;11-30 Independence Day
ZM|Zambia|03-12 Youth Day;05-25 Africa Freedom Day;10-24 Independence Day
ZW|Zimbabwe|04-18 Independence Day;05-25 Africa Day;12-22 Unity Day
""".strip()


def fixed_date_references(year: int):
    """Yield (code, country name, [(date, holiday name), ...])."""
    from datetime import date

    for row in FIXED_DATE_REFERENCES.splitlines():
        code, label, entries = row.split("|")
        holidays = []
        for entry in entries.split(";"):
            day, name = entry.split(" ", 1)
            month, day = map(int, day.split("-"))
            holidays.append((date(year, month, day), name))
        yield code, label, holidays
