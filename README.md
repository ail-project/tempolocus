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
```

The output is probabilistic JSON. Weekly inputs rank timezone offsets and
representative IANA zones. Yearly inputs rank broad regions by comparing
activity spikes or drops with public-holiday calendars.

This is a heuristic first pass. Weekly data cannot uniquely identify an IANA
timezone without dates, and yearly data is sensitive to the meaning of the
activity counter.
