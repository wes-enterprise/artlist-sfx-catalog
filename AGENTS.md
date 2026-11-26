# AGENTS.md — artlist-sfx-catalog usage for consumer agents

> You are an agent that needs sound effects for a video, app, or product.
> This repo is a **read-only data catalog**. Everything you need is in `data/`.
> Read this file top-to-bottom once; after that, `docs/DATA_MANUAL.md` is the reference.

## What this is

A static, versioned snapshot of the **Artlist.io SFX catalog — the FULL corpus,
50,977 sounds** (capture 2026-11-21), packaged for programmatic consumption by
AI agents. Companion repo to `wes-enterprise/artlist-bgm-catalog` (music).

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
| `ambience` | continuous bed — no silence gaps, few onsets | 18,986 (37%) | rain, city room tone, server hum, wind |
| `rhythmic` | patterned and continuous but event-y — periodic onsets | 2,819 (6%) | drum loops, ticking clocks, drips |
| `event` | mid-ground: active but gappy, longer form | 3,289 (6%) | foley sequences, distant thunder, speech |
| `oneshot` | transient event surrounded by silence | 25,863 (51%) | gunshots, clicks, door slams, barks |

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

**Calibration (honest):** classes were validated on 6,105 name-labeled
exemplars — 95% agreement for ambience-named sounds, 83% for oneshot-named;
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
50,977 (10 minutes, Origin-spoofed) and computed:

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
- **Coverage vs live site** — capture 2026-11-21; the live catalog adds
  sounds continuously (live per-category counts can exceed ours).
- **31-ish known gaps**: 20 sounds failed waveform fetch (0.04%, listed by
  the verifier); category membership can drift (a sound we hold under
  "Blades" may today also carry "Metal").

## Repo layout

```
data/catalog/sfx_slim.json.gz    # FULL corpus: 50,977 sounds, all API fields
data/catalog/sfx_waves.json.gz   # wave stats + continuity class per songId
docs/DATA_MANUAL.md              # full field reference + probe evidence
scripts/verify_catalog.py        # integrity checker
AGENTS.md                        # this file
```

## Changelog

- **v1.0 (2026-11-26)** — initial release: full 50,977-sound corpus; waveform
  stats + continuity lane (ambience/rhythmic/event/oneshot with cont score)
  computed from all 50,977 waveform JSONs; metadata audit vs the live Sfx
  GraphQL type (no missed fields — the 6 we don't carry are constant/null
  for SFX); 154-name (155 id-triple) taxonomy with ids.

## Updates

Capture lineage: `wesisad5/artlist-scraper` sfxList walk 2026-11-21;
waveform harvest + continuity classification 2026-11-26. To refresh the
corpus, re-run the sfxList walk (per-category NEWEST pagination, 12/page);
to refresh wave stats, re-run the harvest (resumable, ~10 min for 51k).
