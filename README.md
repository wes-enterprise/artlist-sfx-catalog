# artlist-sfx-catalog

Static, versioned data catalog of the **Artlist.io SFX library — the full
50,977-sound corpus** (capture 2026-11-21), packaged for programmatic
consumption by AI agents. Companion to
[wes-enterprise/artlist-bgm-catalog](https://github.com/wes-enterprise/artlist-bgm-catalog)
(music).

- `data/catalog/sfx_slim.json.gz` — every sound with all API-exposed fields:
  names, ids, durations, 154-name category taxonomy (155 id-triples), audio + waveform URLs.
- `data/catalog/sfx_waves.json.gz` — **waveform-derived continuity lane**:
  per-song envelope stats + `cont` score + class
  (`ambience` / `rhythmic` / `event` / `oneshot`). The Artlist API has no
  loopable/ambience flag (audited exhaustively) — this lane is how you find
  continuous, loopable ambience vs spotty one-shots.

**Start with [AGENTS.md](AGENTS.md)** — onboarding for consumer agents
(continuity classes and their calibration, audio playback rules, query
recipes, honest gaps). Full field reference and probe evidence:
[docs/DATA_MANUAL.md](docs/DATA_MANUAL.md).

Integrity check after cloning:

```bash
python3 scripts/verify_catalog.py        # structural + continuity-lane checks
python3 scripts/verify_catalog.py --cdn  # + live CDN probes
```

Provenance: sfxList GraphQL walk 2026-11-21 (`wesisad5/artlist-scraper`
lineage); waveform harvest + continuity classification 2026-11-26.
Licensing of any sound found here happens at artlist.io.
