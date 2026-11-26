# DATA_MANUAL — artlist-sfx-catalog field reference

Full field-level documentation for the two data files, plus the probe
evidence behind the metadata audit (2026-11-26).

## File: `data/catalog/sfx_slim.json.gz`

Top level: `schema` (`artlist-sfx-catalog/1.0`), `description`,
`generated_at`, `source`, `songs[]` — **all 71,096 sounds** (the FULL SFX
corpus at capture; no sampling).

Per-song fields:

| field | type | meaning |
| --- | --- | --- |
| `songId` | string | Artlist SFX id (stable key; joins to the waves lane) |
| `songName` | string | display name, usually `"<album/collection> - <description>"` |
| `nameForURL` | string | slug for the canonical page URL |
| `artistId` / `artistName` | string | the sound designer / studio |
| `albumId` / `albumName` / `albumNameForURL` | string | the pack/collection the sound belongs to |
| `duration` | string | display `m:ss` — DERIVED from `durationTime` (API field is display-only; we recomputed) |
| `durationTime` | int | duration in seconds |
| `assetTypeId` | int | always `2` (= SFX) in this corpus |
| `categories.children` | string[] | leaf category labels (154 distinct names, 155 id-triples; avg ~2.6 per sound) |
| `categories.families` | string[] | parent families (30 distinct), sorted |
| `categoryIds` | int[] | raw category ids (for API re-queries via `sfxList(categoryIds:)`) |
| `audio.playable` | string | base64-redirect URL → AAC on `cms-public-artifacts.artlist.io` (decode last segment; Origin/Referer headers required) |
| `audio.waveform` | string | 2048-bucket peak-envelope JSON URL (Origin-gated) |
| `art.image` / `art.thumb` | string | pack artwork (imgix, no auth) |
| `artlistUrl` | string | `https://artlist.io/sfx/<slug>/<id>` (canonical page) |

## File: `data/catalog/sfx_waves.json.gz`

Top level: `schema`, `description`, `generated_at`, `stats_definition`
(the formulas), `calibration`, `songs` (map songId → record).

Per-song record:

| key | type | meaning |
| --- | --- | --- |
| `n` | int | bucket count (2048 everywhere observed) |
| `peak` | float | max bucket amplitude (per-file normalized) |
| `sr` | float | silence ratio — buckets < 2% of peak (raw envelope) |
| `qr` | float | quiet ratio — buckets < 25% of peak |
| `rms` | float | sqrt(mean(bucket²)) — loudness density |
| `cf` | float | crest factor peak/rms — low ≈ 3.7–3.9 beds, high ≈ 6+ transients |
| `ec` | int | envelope crossings (active↔inactive at 10% of peak) |
| `fill` | float | longest active run / n (raw) |
| `oden` | float | onset density — crossings per second |
| `ssr` / `sfill` / `scf` | float | smoothed-envelope variants (±20-bucket moving average) — **prefer these**; they bridge sub-2% gaps (a chirp every 5s doesn't split a meadow bed) |
| `cont` | float | continuity score 0..1 (geometric mean of 4 components; any collapse → 0) |
| `class` | string | `ambience` \| `rhythmic` \| `event` \| `oneshot` |
| `dur` | int | duration in seconds (copied for convenience) |

Class rules: `ambience` = cont≥0.55 and ssr<0.25; `rhythmic` = 0.5≤oden≤12
and ssr<0.3; `oneshot` = ssr>0.5 or (cont<0.30 and dur≤15); `event` = else.

20 sounds (0.04%) have `{"error": true}` — waveform fetch failed after 3
retries; the verifier lists them.

## The 30 families / 154 distinct children (155 id-triples — "Explosions" spans two families)

Families (sounds carrying ≥1 child in family): Elements of Nature 5,086 ·
Transport 5,085 · Industry & Commercial 5,076 · Interfaces 4,997 · Human
4,995 · Home 4,972 · Sci-Fi & Fantasy 4,758 · Foley 4,701 · Cartoon 4,671 ·
Domestic 4,639 · Whooshes & Transitions 4,630 · Sport 4,630 · Crowds 4,629 ·
Made with Music 4,610 · Military 4,590 · City 4,575 · Web 2.0 4,573 ·
Indoor Ambiences 4,554 · Fantasy 4,553 · Nature 4,510 · Loops & Phrases
4,514 · Medical 4,498 · Animals 4,393 · Logos 4,383 · Weather 3,078 · …
(30 total; the union overlaps — one sound usually carries children from
several families)

Top children: Metal 2,757 · Gaming 2,433 · Water 2,318 · Cars 2,267 ·
Walla 1,850 · Household Objects 1,793 · Short Whooshes 1,666 · Epic
Transitions 1,626 · Horror Transitions 1,615 · Sci-Fi Machines 1,596 ·
Musical Logos 1,503 · Business & Office 1,475 · Alerts 1,473 · Melodic
Loops 1,462 · Pubs 1,444 …

## Probe evidence (the metadata audit, 2026-11-26)

All facts below were established by live GraphQL probes
(`download/probe_sfx/p1–p10`, scripts preserved in the parent project).

### The SFX API surface

- Endpoint: `https://search-api.artlist.io/v2/graphql` (anonymous POST with
  browser-like headers: UA + Origin + Referer — bare requests 403).
- Query: `sfxList(categoryIds: String!, page: Float!, sortBy:
  SfxListRequestSortByOptions!, term: String!)` → `SfxListResponse
  { songs: [Sfx!]!, page }`. **12 items per page**; deep pages return empty
  (cat 110 stops at page 48; cat 210 at page 121 under NEWEST).
- `sortBy` enum has exactly two values: `TOP_DOWNLOADS`, `NEWEST`.
- `songs(ids: [...])` — the music batch surface — **returns empty for SFX
  ids**. There is no per-id fetch for SFX; the only read surface is the
  paginated `sfxList` (and the public site's `trackPage`-style pages).
- v1 graphql endpoint: exists but no richer SFX surface.

### Fields the Sfx type HAS (20 scalars + 1 object)

`songId, songName, artistName, artistId, albumId, albumName,
albumNameForURL, duration, durationTime, isNew, isOriginal, nameForURL,
lyrics, originalVersionID, assetTypeId, sitePlayableFilePath,
waveSurferFilePath, albumImageFilePath, albumThumbFilePath, similarSongs`
+ `grandChildCategories { id name parentName }`.

`similarSongs` is a **String** (not an object list) and returned `null` on
every probe.

### Fields the Sfx type does NOT have (bruteforced, all rejected)

`loopable, loop, loops, isLoopable, seamless, isSeamless, ambience,
isAmbience, ambient, isAmbient, continuity, variations, version, versions,
similarSounds, soundType, fileFormat, sampleRate, bitDepth, channels,
bitrate, fileName, filePath, playableFilePath, downloadFilePath,
previewUrl, audioUrl, waveformUrl, thumbnailUrl, downloads, downloadCount,
views, popularity, plays, isFeatured, isPremium, proOnly, studioOnly,
keywords, description, notes, meta, metadata, createdAt, updatedAt,
publishedAt, addedAt, discoveredAt, bpm, tempo, vocals, tags, categories,
genreCategories, childCategories, parentCategories, explicit, isPreRelease,
featuredArtists, primaryArtists, numberOfStems, officialReleaseDate,
hook30Start, hook30End, durationInSeconds, size, fileSize, parentName,
family, soundFamily, isDelisted, status, artlistUrl, url, slug, image,
thumb, wave, audio, …`

**Conclusion: there is no API signal for loopable/ambience/continuity.**
That is why this repo computes one from the public waveform JSONs.

### Field values we sampled but don't carry (and why)

- `duration` (display string) — derivable from `durationTime`; recomputed.
- `lyrics` — `null` on every sampled SFX (music-family leftover).
- `isOriginal` — `false` everywhere sampled.
- `originalVersionID` — `"-1"` everywhere sampled.
- `isNew` — captured in the walk (`0% covered` per the original walk notes).
- `similarSongs` — `null` everywhere sampled.
- `assetTypeId` — always `2`; carried for completeness.

### Fidelity

Re-fetched category pages on 2026-11-26 and compared with our stored
records: `songName`, `durationTime`, album/artist values all match. (An
earlier "mismatch" report was a probe-script bug — the query hadn't
selected `songName`.) Live category membership can drift: sounds appear
under additional categories on the live site (e.g. new "Blades"→"Metal"
cross-listings), and per-category live counts exceed ours where new sounds
have been added since 2026-11-21.

## Provenance & capture notes

- Corpus: sfxList GraphQL walk 2026-11-21 (lineage `wesisad5/artlist-scraper`
  → `data/sfx/chunks`, 11 × 5,000-row chunks, build manifest `build.json`
  with content hashes).
- Waveform harvest: 2026-11-26, all 71,096 `waveSurferFilePath` JSONs
  fetched with Origin/Referer spoof, 24 threads, ~4 min; 20 failures
  retried 3× each then marked `error`.
- Continuity classification: 2026-11-26 (`scripts/classify_continuity.py`
  in the parent project; calibration stats in the waves file header).
- AAC URLs: pre-signed CloudFront on `cms-public-artifacts.artlist.io`
  (base64-redirect form for SFX). Copy verbatim; the signature covers the
  full query string.
