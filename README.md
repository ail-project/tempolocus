# tempolocus

tempolocus look at time-series activity patterns to approximate a location inference.

## Using tempolocus 

`tempolocus` accepts two JSON shapes:

- Weekly hourly buckets: a list of objects containing `day`, `hour`, and `count`.
- Yearly daily buckets: an object containing `year`, `max`, and `nb`, where `nb`
  is a list of `[YYYY-MM-DD, count]` pairs.

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
```

The output is probabilistic JSON and includes a generic `analysis.activity_type`
classification of `work-time`, `vacation-time`, or `mixed-time`. Weekly inputs
rank timezone offsets and representative IANA zones. Yearly inputs rank broad regions by comparing
activity on public-holiday calendars, including Orthodox calendar references for
countries such as Bulgaria, Greece, Romania, Russia, Serbia, and Ukraine.
Yearly analysis treats a lack of activity on holidays as the default signal;
pass `--activity-signal peak` when unusually high activity is the indicator you
want to match instead. Yearly analysis defaults to standard public holidays;
pass `--holiday-profile public-worker` to add public-sector worker references,
such as state-worker, Golden Week, bridge-day, or administrative closure days,
alongside standard holidays. The public-worker profile includes additional
China and Russia references for government and public-sector closure patterns.

The generic activity analysis compares weekly business-hours against
weekend/off-hours activity, or yearly weekday activity against weekend activity.
It is intended as a broad activity-label heuristic rather than a declaration of
why the activity occurred.

This is a heuristic first pass. Weekly data cannot uniquely identify an IANA
timezone without dates, and yearly data is sensitive to the meaning of the
activity counter.

## License

This project is licensed under the GNU Affero General Public License v3.0 or
later. See [LICENSE](LICENSE) for details.
