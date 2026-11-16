# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-11-15

### Fixed
- **Option changes take effect immediately.** Changing the name, MQTT topic,
  thresholds or exclusion entities in the options dialog was saved but ignored
  until Home Assistant restarted: the topic subscription and the tracking of
  exclusion entities are set up once at start. The entry now reloads itself
  when its options change.

### Changed
- **One Water Saver entry per Home Assistant instance**
  (`single_config_entry`). The setup dialog used to accept a second entry for
  another topic, but entity unique IDs and the storage file are not
  entry-specific — the second entry's entities were rejected and both entries
  overwrote each other's period history. Existing single-entry installations
  are not affected.

## [0.1.2] - 2026-09-01

### Fixed
- **Pool / irrigation exclusion now covers the tail of a draw.** The exclusion
  window used to close purely on a grace timer (default 20 min) after the valve
  went off. Meters that report less often than that — a wM-Bus meter sending
  one telegram per hour, for instance — book most of the draw in a telegram
  that arrives *after* the window has closed, so it landed in today's effective
  volume and could trigger a today-high false alarm on every irrigation run.
  The window now also stays open until exactly one telegram has been booked
  since the draw ended, however long the meter takes. The grace period is kept
  as a time floor for meters that report faster than it, so both cadences are
  covered. The flag is cleared at the day boundary, which bounds it to the day
  it was armed in.

## [0.1.1] - 2026-08-30

### Fixed
- `DEFAULT_EXCLUDE_ENTITIES` no longer ships hard-coded entity IDs from the
  author's own installation. The default is now empty — exclusion entities are
  installation-specific and are picked in the options flow. Existing setups are
  unaffected: the options flow stores the list explicitly, so the default was
  never consulted.

## [0.1.0] - 2026-08-30

First release intended for general use. The 0.0.x line was an early prototype
built around YAML template sensors and `utility_meter`; everything is now
computed inside the integration and persisted across restarts.

### Added
- **Leak detection (continuous flow)** — alarm when every hour across a
  configurable window (default 12 h) shows consumption above 0 L.
- **Today-high detection** — alarm when today's consumption exceeds
  `14-day average × multiplier + buffer`, gated by a minimum volume and an
  earliest hour of day so a quiet morning never triggers it.
- **Rolling baseline** with 24 h / 14 d / 12 m history, averaged with the top
  values trimmed so a pool fill or a past leak does not raise the bar for the
  next alarm.
- **Pool / irrigation exclusion** — while a nominated entity is active, the
  meter delta is attributed to it and subtracted from today's total before the
  today-high threshold is checked, including a grace window that catches the
  meter's delayed lumps. Exposed as `excluded_today_l`, `effective_day_l` and
  `exclude_active` attributes on `binary_sensor.water_saver_today_high`.
- **Snooze** — `water_saver.snooze` / `water_saver.unsnooze` services plus a
  master switch and one switch per alarm type; turning the master switch off
  stops a running alarm within a second.
- **Binary sensors** `hour_active`, `leak_12h`, `today_high`, `alert`.
- **Comparison sensors** — today vs. 14-day average (delta and percent), month
  vs. 12-month average including an over/under split — and a leak-status text
  sensor.
- **Options flow** for every threshold, the exclusion entities and the grace
  window; no YAML required.
- **State persistence** — period starts, history and counters survive restarts.
- Availability handling: entities go unavailable after a configurable number of
  minutes without a telegram, instead of silently reporting zero consumption.
- Optional integration with the `herold` message broker: the topic
  `wasser/leck_alarm` is registered on startup when Herold is installed.
- Brand assets shipped in `custom_components/water_saver/brand/`.

### Changed
- Consumption per period is computed from meter deltas inside the integration;
  the `utility_meter` / template-sensor package (`water_saver.yaml`) is gone.
- `hacs.json` reduced to the keys HACS actually supports, and the country
  restriction removed — the integration works with any MQTT source.
- `manifest.json` gained `issue_tracker`; keys sorted as hassfest expects.

### Removed
- `custom_components/water_saver/water_saver.yaml` (superseded).
- A duplicate `hacs.json` inside the component directory.

## [0.0.10] - 2026-02-08
- Early prototype: MQTT JSON ingest, total / hour / day / week / month / year
  sensors, last seen, RSSI, battery, and a config flow for name and topic.

[0.1.1]: https://github.com/cnc-lasercraft/water_saver/releases/tag/v0.1.1
[0.1.0]: https://github.com/cnc-lasercraft/water_saver/releases/tag/v0.1.0
[0.0.10]: https://github.com/cnc-lasercraft/water_saver/releases/tag/v0.0.10
