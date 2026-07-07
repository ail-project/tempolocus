# tempolocus

tempolocus look at time-series activity patterns to approximate a location inference.

## First Python implementation

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
```

The output is probabilistic JSON. Weekly inputs rank timezone offsets and
representative IANA zones. Yearly inputs rank broad regions by comparing
activity spikes or drops with public-holiday calendars, including Orthodox
calendar references for countries such as Bulgaria, Greece, Romania, Russia,
Serbia, and Ukraine. Yearly analysis defaults to standard public holidays; pass
`--holiday-profile public-worker` to add public-sector worker references, such
as state-worker, Golden Week, bridge-day, or administrative closure days,
alongside standard holidays. The public-worker profile includes additional
China and Russia references for government and public-sector closure patterns.

This is a heuristic first pass. Weekly data cannot uniquely identify an IANA
timezone without dates, and yearly data is sensitive to the meaning of the
activity counter.
