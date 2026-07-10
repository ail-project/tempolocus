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
activity on public-holiday calendars, including Orthodox calendar references for
countries such as Bulgaria, Greece, Romania, Russia, Serbia, and Ukraine; expanded
European references for the Baltics, Balkans, Iceland, and Luxembourg; North
American calendars for Canada, Costa Rica, Cuba, the Dominican Republic,
Guatemala, Mexico, Panama, and the United States; Asia-Pacific calendars for
Australia, China, India, Japan, Malaysia, New Zealand, North Korea, the
Philippines, Singapore, South Korea, Thailand, and Vietnam; South American
calendars for Argentina, Brazil, Chile, Colombia, Peru, and Uruguay; African
calendars for Côte d'Ivoire, Ethiopia, Ghana, Kenya, Nigeria, Senegal, and
South Africa; plus Arabic-region and Israel vacation references for Algeria,
Bahrain, Egypt, Israel, Jordan, Kuwait, Lebanon, Morocco, Oman, Qatar, Saudi
Arabia, Tunisia, and the United Arab Emirates.
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
