# tempolocus

tempolocus looks at time-series activity patterns to infer a location.

## Using tempolocus 

`tempolocus` accepts two JSON shapes plus timestamp-list imports:

- Weekly hourly buckets: a list of objects containing `day`, `hour`, and `count`.
- Yearly daily buckets: an object containing `year`, `max`, and `nb`, where `nb`
  is a list of `[YYYY-MM-DD, count]` pairs.
- Timestamp lists: either a JSON list of UTC timestamp strings / Unix epoch
  seconds, or a plain text file with one timestamp per line. This is useful for
  PE `TimeDateStamp` / compiled-timestamp values and other event lists that
  should be aggregated into weekly patterns.

Run it from the repository:

```bash
python -m tempolocus samples/weekfull-chan1.json
python -m tempolocus samples/year.json --format text
```

Or install the package locally:

```bash
python -m pip install -e .
tempolocus samples/year-chan1.json --top 10
tempolocus samples/year.json --holiday-profile public-worker --format text
tempolocus samples/year.json --activity-signal peak --format text
tempolocus timestamps.txt --kind timestamps --format text
```

Timestamp strings may use ISO-8601 forms such as `2026-01-05T09:15:00Z`
or `2026-01-05 09:15:00 UTC`; numeric entries are interpreted as Unix epoch
seconds in UTC. The output is probabilistic JSON and includes a generic `analysis.activity_type`
classification of `work-time`, `vacation-time`, or `mixed-time`. Weekly inputs
rank timezone offsets, representative IANA zones, and a `probable_countries`
list that highlights countries whose multiple timezones appear in the top
timezone-offset results. Yearly inputs rank broad regions by comparing
activity on public-holiday calendars.

### Supported yearly holiday regions

| Area | Supported regions |
| --- | --- |
| 🌍 Africa | 🇩🇿 Algeria, 🇨🇮 Côte d'Ivoire, 🇪🇬 Egypt, 🇪🇹 Ethiopia, 🇬🇭 Ghana, 🇰🇪 Kenya, 🇲🇦 Morocco, 🇳🇬 Nigeria, 🇸🇳 Senegal, 🇿🇦 South Africa, 🇹🇳 Tunisia |
| 🌏 Asia-Pacific | 🇦🇺 Australia, 🇨🇳 China, 🇮🇳 India, 🇯🇵 Japan, 🇲🇾 Malaysia, 🇳🇿 New Zealand, 🇰🇵 North Korea, 🇵🇭 Philippines, 🇸🇬 Singapore, 🇰🇷 South Korea, 🇹🇭 Thailand, 🇻🇳 Vietnam |
| 🇪🇺 Europe | 🇦🇹 Austria, 🇧🇪 Belgium, 🇧🇦 Bosnia and Herzegovina, 🇧🇬 Bulgaria, 🇭🇷 Croatia, 🇨🇿 Czechia, 🇩🇰 Denmark, 🇪🇪 Estonia, 🇫🇮 Finland, 🇫🇷 France, 🇩🇪 Germany, 🇬🇷 Greece, 🇭🇺 Hungary, 🇮🇸 Iceland, 🇮🇪 Ireland, 🇮🇹 Italy, 🇱🇻 Latvia, 🇱🇹 Lithuania, 🇱🇺 Luxembourg, 🇳🇱 Netherlands, 🇳🇴 Norway, 🇵🇱 Poland, 🇵🇹 Portugal, 🇷🇴 Romania, 🇷🇺 Russia, 🇷🇸 Serbia, 🇸🇰 Slovakia, 🇸🇮 Slovenia, 🇪🇸 Spain, 🇸🇪 Sweden, 🇨🇭 Switzerland, 🇺🇦 Ukraine, 🇬🇧 United Kingdom |
| 🌎 North America & Caribbean | 🇨🇦 Canada, 🇨🇷 Costa Rica, 🇨🇺 Cuba, 🇩🇴 Dominican Republic, 🇬🇹 Guatemala, 🇲🇽 Mexico, 🇵🇦 Panama, 🇺🇸 United States |
| 🕌 Middle East | 🇧🇭 Bahrain, 🇮🇱 Israel, 🇯🇴 Jordan, 🇰🇼 Kuwait, 🇱🇧 Lebanon, 🇴🇲 Oman, 🇶🇦 Qatar, 🇸🇦 Saudi Arabia, 🇦🇪 United Arab Emirates |
| 🌎 South America | 🇦🇷 Argentina, 🇧🇷 Brazil, 🇨🇱 Chile, 🇨🇴 Colombia, 🇵🇪 Peru, 🇺🇾 Uruguay |

Yearly analysis treats a lack of activity on holidays as the default signal;
pass `--activity-signal peak` when unusually high activity is the indicator you
want to match instead. Yearly analysis defaults to standard public holidays;
pass `--holiday-profile public-worker` to add public-sector worker references,
such as state-worker, Golden Week, bridge-day, or administrative closure days,
alongside standard holidays. The public-worker profile includes additional
China and Russia references for government and public-sector closure patterns,
and South American public-servant references with common administrative bridge
or year-end closure days.

The generic activity analysis compares weekly business-hours against
weekend/off-hours activity, or yearly weekday activity against weekend activity.
It is intended as a broad activity-label heuristic rather than a declaration of
why the activity occurred.

This is a heuristic first pass. Weekly data cannot uniquely identify an IANA
timezone without dates, and yearly data is sensitive to the meaning of the
activity counter.

## Using tempolocus as a Python library

Install `tempolocus` in the Python environment that will import it:

```bash
python -m pip install tempolocus
```

For development against a local checkout, install it in editable mode instead:

```bash
python -m pip install -e .
```

The public package entry points are `detect`, `analyze_activity`, and
`load_json`:

```python
from tempolocus import analyze_activity, detect, load_json

data = load_json("samples/weekfull-chan1.json")
result = detect(data, top=10)

print(result["input_type"])
print(result["results"][0]["label"])
print(result["analysis"]["activity_type"])

activity = analyze_activity(data)
print(activity["activity_type"])
```

### `detect(data, kind="auto", top=5, holiday_profile="standard", activity_signal="lack")`

Use `detect` when you want the full inference result. It accepts already-loaded
Python data structures rather than file paths, which makes it suitable for web
services, notebooks, pipelines, and tests. The return value is a dictionary with
metadata, assumptions, signal summaries, and ranked `results`.

Parameters:

- `data`: one of the supported input shapes described below.
- `kind`: `"auto"`, `"weekly"`, `"yearly"`, or `"timestamps"`. Use `"auto"`
  when the input shape is unambiguous; force a kind when your caller already
  knows what it provided.
- `top`: number of ranked candidates to include. Must be at least `1`.
- `holiday_profile`: for yearly inputs, `"standard"` or `"public-worker"`. The
  public-worker profile adds public-sector closure references where available.
- `activity_signal`: for yearly inputs, `"lack"` to match low activity on
  holidays or `"peak"` to match unusually high activity on holidays.

Weekly hourly bucket example:

```python
from tempolocus import detect

weekly_rows = [
    {"day": day, "hour": hour, "count": 10 if day <= 4 and 9 <= hour <= 17 else 1}
    for day in range(7)
    for hour in range(24)
]

result = detect(weekly_rows, kind="weekly", top=3)
for candidate in result["results"]:
    print(candidate["probability"], candidate["id"], candidate["label"])
```

Timestamp list example:

```python
from tempolocus import detect

timestamps = [
    "2026-01-05T09:15:00Z",
    "2026-01-06 10:30:00 UTC",
    1767605400,  # Unix epoch seconds in UTC
]

result = detect(timestamps, kind="timestamps")
print(result["signals"]["timestamps_seen"])
```

Yearly daily bucket example:

```python
from tempolocus import detect

yearly = {
    "year": 2026,
    "max": 42,
    "nb": [
        ["2026-01-01", 0],
        ["2026-01-02", 18],
        ["2026-01-03", 21],
    ],
}

result = detect(
    yearly,
    kind="yearly",
    top=5,
    holiday_profile="public-worker",
    activity_signal="lack",
)
print(result["results"][0]["id"], result["results"][0]["label"])
```

### `analyze_activity(data, kind="auto")`

Use `analyze_activity` when you only need the generic activity classification
without timezone or holiday-region rankings. It returns fields such as
`activity_type`, `score`, and `shares`. Weekly inputs are classified from local
business-hours versus weekend/off-hours activity; yearly inputs compare weekday
and weekend activity.

```python
from tempolocus import analyze_activity, load_json

activity = analyze_activity(load_json("samples/year.json"), kind="yearly")
print(activity["activity_type"], activity["score"])
```

### Input shape reference

| Kind | Python shape | Notes |
| --- | --- | --- |
| `weekly` | `list[dict]` with `day`, `hour`, and `count` | `day` is `0` through `6`; `hour` is `0` through `23`; buckets are interpreted as UTC. |
| `yearly` | `dict` with `year`, `max`, and `nb` | `nb` is a list of `[YYYY-MM-DD, count]` pairs. Missing days inside the observed range are filled as zero activity. |
| `timestamps` | `list[str | int | float]` | Strings are parsed as UTC timestamps; numbers are Unix epoch seconds in UTC. |

Invalid inputs raise `tempolocus.core.DetectionError`, a subclass of
`ValueError`. Catch it around user-supplied data if you need to return a custom
error response:

```python
from tempolocus import detect
from tempolocus.core import DetectionError

try:
    result = detect(user_supplied_data)
except DetectionError as error:
    result = {"error": str(error)}
```

## Example 

~~~
adulau@blakley:~/git/tempolocus$ python3 -m tempolocus samples/weekfull-chan1.json --format text  -n 10 --holiday-profile public-worker 
input_type: weekly_timeseries
confidence: 0.220
activity_type: mixed-time (0.009)
assumptions:
  - Hourly buckets are interpreted as UTC; timezone candidates are offsets that make the activity look locally human.
  - Weekly data cannot distinguish all IANA zones sharing the same offset, and daylight saving time is not inferable without dates.
probable_countries:
  0.970  Russia (UTC+02:00, UTC+03:00, UTC+04:00, UTC+05:00, UTC+06:00, UTC+07:00, UTC+08:00)
  0.009  France (UTC+01:00, UTC+03:00, UTC+04:00)
  0.008  Kazakhstan (UTC+05:00, UTC+06:00)
  0.003  United Kingdom (UTC+00:00, UTC+06:00)
  0.002  Mongolia (UTC+07:00, UTC+08:00)
results:
  0.208  timezone: UTC+05 Pakistan / western Central Asia
          utc_quiet_window=19:00-01:00; local_quiet_window=00:00-06:00; quiet_activity_ratio=0.366; local_quiet_center=2.5
  0.196  timezone: UTC+04 Gulf / Caucasus
          utc_quiet_window=19:00-01:00; local_quiet_window=23:00-05:00; quiet_activity_ratio=0.366; local_quiet_center=1.5
  0.143  timezone: UTC+06 Bangladesh / central Asia
          utc_quiet_window=19:00-01:00; local_quiet_window=01:00-07:00; quiet_activity_ratio=0.366; local_quiet_center=3.5
  0.129  timezone: UTC+03 East Africa / Arabia / Moscow
          utc_quiet_window=19:00-01:00; local_quiet_window=22:00-04:00; quiet_activity_ratio=0.366; local_quiet_center=0.5
  0.072  timezone: UTC+02 Eastern Europe / southern Africa
          utc_quiet_window=19:00-01:00; local_quiet_window=21:00-03:00; quiet_activity_ratio=0.366; local_quiet_center=23.5
  0.067  timezone: UTC+07 mainland Southeast Asia
          utc_quiet_window=19:00-01:00; local_quiet_window=02:00-08:00; quiet_activity_ratio=0.366; local_quiet_center=4.5
  0.039  timezone: UTC+01 Central Europe / West Africa
          utc_quiet_window=19:00-01:00; local_quiet_window=20:00-02:00; quiet_activity_ratio=0.366; local_quiet_center=22.5
  0.027  timezone: UTC+08 China / Singapore / Western Australia
          utc_quiet_window=19:00-01:00; local_quiet_window=03:00-09:00; quiet_activity_ratio=0.366; local_quiet_center=5.5
  0.023  timezone: UTC+00 Western Europe / West Africa
          utc_quiet_window=19:00-01:00; local_quiet_window=19:00-01:00; quiet_activity_ratio=0.366; local_quiet_center=21.5
  0.015  timezone: UTC-01 Azores / Cape Verde
          utc_quiet_window=19:00-01:00; local_quiet_window=18:00-00:00; quiet_activity_ratio=0.366; local_quiet_center=20.5
~~~

## License

This project is licensed under the GNU Affero General Public License v3.0 or
later. See [LICENSE](LICENSE) for details.
