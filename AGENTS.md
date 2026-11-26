# AGENTS.md — artlist-sfx-catalog usage for consumer agents

> You are an agent that needs sound effects for a video, app, or product.
> This repo is a **read-only data catalog**. Everything you need is in `data/`.
> Read this file top-to-bottom once; after that, `docs/DATA_MANUAL.md` is the reference.

## What this is

A static, versioned snapshot of the **Artlist.io SFX catalog — the FULL corpus,
71,096 sounds** (v1.1 full-field walk 2026-11-26), packaged for programmatic
consumption by AI agents. Companion repo to `wes-enterprise/artlist-bgm-catalog`
(music).

Two files:

- **`data/catalog/sfx_slim.json.gz`** — every sound with all API-exposed fields:
  names, artist/album ids, duration, category tree, audio + waveform URLs, art.
- **`data/catalog/sfx_waves.json.gz`** — per-song **waveform stats + continuity
  class** (our computation — see "The loopable question" below). This lane is
  the reason this repo exists beyond a mirror: it answers "is this sound a
  continuous bed or a spotty one-shot?" which the Artlist API cannot.

## The one thing to know: continuity class

Every sound has a waveform-derived class + `cont` score (0..1):

| class | meaning | count | typical |
| --- | --- | --- | --- |
| `ambience` | continuous bed — no silence gaps, few onsets | 25,347 (36%) | rain, city room tone, server hum, wind |
| `rhythmic` | patterned and continuous but event-y — periodic onsets | 3,959 (6%) | drum loops, ticking clocks, drips |
| `event` | mid-ground: active but gappy, longer form | 4,652 (7%) | foley sequences, distant thunder, speech |
| `oneshot` | transient event surrounded by silence | 37,112 (52%) | gunshots, clicks, door slams, barks |

```python
import gzip, json
slim = json.loads(gzip.open('data/catalog/sfx_slim.json.gz').read())['songs']
waves = json.loads(gzip.open('data/catalog/sfx_waves.json.gz').read())['songs']
by_id = {s['songId']: s for s in slim}

# continuous beds for a scene: ambience class, longer is better
beds = [(w['cont'], sid) for sid, w in waves.items()
        if w['class'] == 'ambience' and w.get('dur', 0) >= 60]
# loopable material also includes short rhythmic loops:
rhythmic_loops = [sid for sid, w in waves.items() if w['class'] == 'rhythmic']
```

**Calibration (honest):** classes were validated on name-labeled exemplars —
95% agreement for ambience-named sounds (4,920/5,158), 85% for oneshot-named
(1,394/1,634);
category-family cross-check: City 94% / Indoor Ambiences 93% / Weather 93%
classified ambience, vs Logos 28%. The remaining disagreement is mostly
**semantics, not error**: a gong's 15-second decay *is* waveform-continuous
(classed `ambience`) even though it's named "Single Strike"; a "Loop"-named
sound can be a bed loop (→ `ambience`), a gated rhythmic loop (→ `rhythmic`),
or a one-shot loop point (→ `oneshot`). **Filter by waveform class when you
mean texture; use the name when you mean intent.**

### The loopable question (how we answered it)

The Artlist API **has no loopable/ambience/seamless flag** — we bruteforced
the Sfx GraphQL type (`loopable`, `loop`, `ambience`, `isAmbient`, `seamless`,
`continuity`, `variations`, `soundType`, `sampleRate`, … all absent; full list
in DATA_MANUAL). What the API does give every sound is a
`waveSurferFilePath` — a 2048-bucket peak-envelope JSON. We fetched all
71,070 with waveforms (5 minutes, Origin-spoofed; 26 sounds have no waveform
URL in the API itself) and computed:

- raw stats: silence ratio, quiet ratio, crest factor (peak/rms), envelope
  crossings, longest active run, onset density (crossings/second)
- **smoothed stats** (±20-bucket moving average): same measures on an
  envelope with sub-2% gaps bridged — a 150s meadow ambience with a bird
  chirp every 5 seconds is still one continuous bed
- `cont` = geometric mean of the four continuity components; any collapsed
  component (e.g. >12 onsets/second) zeroes it

Separation is clean (medians): ambience sr=0.005 / cf=3.9 / 0.8 onsets-per-s
vs oneshot sr=0.62 / cf=6.4 / 16.5 onsets-per-s.

**Caveats:** peaks are 2048 buckets regardless of length — resolution is
~13 buckets/second on a 150s file, so micro-gaps (<80ms) are invisible;
amplitude is peak-normalized per file, so "silence" is relative to the loudest
moment (a quiet rain bed under one thunder clap reads as silence-heavy on the
RAW stats — use the smoothed ones). Loopability also needs the start and end
to match, which a peak envelope cannot prove — `class: ambience` + short
duration + stable `rms` is the best proxy, not a guarantee.

## Categories (the SFX taxonomy)

Sounds carry `categories.children` (leaf labels: 154 distinct names, 155 id-triples — "Explosions" spans two families) and
`categories.families` (parents, 30 distinct), plus raw `categoryIds`.

- **30 families**: Animals, Cartoon, City, Crowds, Domestic, Elements of
  Nature, Fantasy, Foley, Home, Human, Indoor Ambiences, Industry &
  Commercial, Interfaces, Loops & Phrases, Made with Music, Medical,
  Military, Nature, Science Fiction & Fantasy, Sport, Transport, Weather,
  Web 2.0, Whooshes & Transitions, … (full list with counts in DATA_MANUAL)
- **154 children** (155 id-triples — "Explosions" appears under both
  Destruction and Weapons & Warfare) incl. Metal (2,757), Gaming (2,433),
  Water (2,318), Cars (2,267), Walla (1,850), Household Objects (1,793),
  Short Whooshes (1,666), Epic Transitions (1,626), Horror Transitions
  (1,615), Sci-Fi Machines (1,596), Musical Logos (1,503),
  Business & Office (1,475), Alerts (1,473), Melodic Loops (1,462), …
- Multi-category sounds are the norm (avg ~2.6 children/sound): a "Rome
  Market Ambience" is Household Objects **and** Metal **and** Crowds.

## Audio access (READ THIS — playback rules)

1. **AAC (`audio.playable`) — base64-redirect URL.** Decode the last path
   segment as urlsafe-base64 to get the real CDN path
   (`content/sfx/aac/<file>.aac`); fetch that path on the same host WITH
   `Origin: https://artlist.io` + `Referer: https://artlist.io/` headers
   (bare requests get 403). Returns `audio/aac`.
2. **Waveform JSON (`audio.waveform`) — same Origin/Referer rule.** Returns
   the flat 2048-float array (this is what our stats lane was computed from).
3. **Never hotlink in production UIs** without mirroring. This catalog is for
   research/selection; licensing happens at artlist.io (`artlistUrl` field,
   canonical `https://artlist.io/sfx/<slug>/<id>`).
4. The URLs belong to Artlist's CDN; they are stable as captured but not
   ours to serve.

## Quickstart recipes

```python
import gzip, json

slim = json.loads(gzip.open('data/catalog/sfx_slim.json.gz').read())['songs']
waves = json.loads(gzip.open('data/catalog/sfx_waves.json.gz').read())['songs']

# 1) rainy city bed, 60s+, top continuity
picks = [(w['cont'], s['songName']) for s in slim
         for w in [waves.get(s['songId'])]
         if w and w['class'] == 'ambience'
         and 'Weather' in s['categories']['families']
         and 'City' in s['categories']['families']
         and (w.get('dur') or s['durationTime']) >= 60]
picks.sort(reverse=True)

# 2) all short metallic one-shots for UI feedback
ui = [s for s in slim
      if (waves.get(s['songId']) or {}).get('class') == 'oneshot'
      and 'Metal' in s['categories']['children']
      and s['durationTime'] <= 3]

# 3) melodic loops that are actually beds (for under-score)
beds = [s for s in slim
        if 'Melodic Loops' in s['categories']['children']
        and (waves.get(s['songId']) or {}).get('cont', 0) > 0.8]

# 4) find a sound by name across the corpus
hits = [s for s in slim if 'thunder' in (s['songName'] or '').lower()]
```

`scripts/verify_catalog.py` re-validates everything (counts, join integrity,
continuity-lane coverage, live CDN probes) — run it after cloning.

## Metadata honesty (what we DON'T have)

- **No loopable/seamless flag** — the API doesn't expose one (probed
  exhaustively, see DATA_MANUAL "Fields the API does NOT have"). The
  continuity lane is our inference from public waveform data.
- **No numeric bpm/key** — SFX has no tempo concept in the API (music-side
  fields like `bpm`/`tempo` don't exist on the Sfx type).
- **No tags** — unlike music (SongV2 has `tags`), SFX has no free-text tag
  field. Search relies on names + category tree.
- **No vocals/lyrics** — the fields exist on the Sfx type but return
  `null`/`false`/`"-1"` for every sound we sampled (they're music-family
  leftovers).
- **No per-sound download counts / popularity** — `sfxList` sorts by
  TOP_DOWNLOADS but never exposes the counts.
- **Similar sounds** — `similarSongs` field exists but returned `null` on
  every probe; the similar-sounds UI on artlist.io is computed elsewhere.
- **Coverage vs live site** — v1.1 full-field walk 2026-11-26 (all 155
  category ids x NEWEST + TOP_DOWNLOADS; the API rate-limits sustained walks,
  82 of 310 windows were unreachable that day). We hold 71,096 sounds vs the
  68,540-id same-day census floor (+2,556 beyond it); ~166 census ids (0.24%)
  remain uncaptured, and the live catalog keeps growing.
- **26 sounds have no waveform URL** in the API itself (`missing_wave` in the
  waves lane) — not a fetch failure.
- **137 records carry 16 fields** (v1.0 capture shape: no
  isOriginal/originalVersionID/albumThumbFilePath/lyrics/duration): they sit
  outside both sort windows and were not reachable by term/category search;
  100 of the original 237 such records were upgraded to full 20-field
  records in v1.1.
- **2 sounds (138784, 139403) have NULL categories** — live-verified the
  API returns no grandChildCategories for them; upstream data gap.

## Repo layout

```
data/catalog/sfx_slim.json.gz    # FULL corpus: 71,096 sounds, all API fields
data/catalog/sfx_waves.json.gz   # wave stats + continuity class per songId
docs/DATA_MANUAL.md              # full field reference + probe evidence
scripts/verify_catalog.py        # integrity checker
AGENTS.md                        # this file
```

## Changelog

- **v1.1 (2026-11-26)** — full-field re-walk: +20,119 sounds vs v1.0
  (71,096 total = 70,859 dual-sort walk + 237 v1.0 records kept), all 20
  API fields (v1.0 chunks carried 16 — the E2E audit caught this); wave
  stats + continuity extended to all 71,070 sounds with waveforms;
  end-to-end audit 19/19 PASS (capture completeness, field fidelity,
  pipeline recompute, output integrity, live CDN probes).
- **v1.0 (2026-11-26)** — initial release: 50,977-sound single-sort walk;
  waveform stats + continuity lane (ambience/rhythmic/event/oneshot with
  cont score); metadata audit vs the live Sfx GraphQL type; 154-name
  (155 id-triple) taxonomy with ids.

## Updates

Capture lineage: sfxList GraphQL walks 2026-11-21 (single-sort, 16-field)
and 2026-11-26 (dual-sort full-field); waveform harvest + continuity
classification 2026-11-26. To refresh, re-run the dual-sort walk
(`scripts/walk_sfx_full.py`, resumable, rate-limit aware); to refresh wave
stats, re-run the harvest (resumable, ~5 min for 71k warm).
