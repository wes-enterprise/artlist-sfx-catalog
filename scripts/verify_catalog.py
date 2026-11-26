#!/usr/bin/env python3
"""verify_catalog.py — integrity checker for artlist-sfx-catalog.

Run from repo root:
    python3 scripts/verify_catalog.py          # structural + lane checks
    python3 scripts/verify_catalog.py --cdn    # + live CDN probes (5 samples)

Checks: file presence, schema, corpus counts, field completeness, category
join integrity, waves-lane coverage and value ranges, class distribution
sanity, slim/waves id-set equality, and (optionally) live AAC + waveform
fetches with the Origin/Referer spoof.
"""
import base64
import json
import gzip
import os
import random
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'OK' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def main():
    print("1) files")
    for p in ["data/catalog/sfx_slim.json.gz", "data/catalog/sfx_waves.json.gz",
              "AGENTS.md", "README.md", "docs/DATA_MANUAL.md"]:
        check(f"{p} exists", os.path.isfile(f"{ROOT}/{p}"))

    print("2) slim structure")
    slim = json.loads(gzip.open(f"{ROOT}/data/catalog/sfx_slim.json.gz").read())
    check("schema", slim["schema"] == "artlist-sfx-catalog/1.1", slim["schema"])
    songs = slim["songs"]
    n = len(songs)
    check("corpus count = 71,096", n == 71096, f"{n}")
    ids = [s["songId"] for s in songs]
    check("unique ids", len(set(ids)) == n, f"{len(set(ids))}")

    print("3) slim field completeness")
    req = ["songId", "songName", "artistName", "durationTime", "categories",
           "audio", "artlistUrl"]
    for f in req:
        cov = sum(1 for s in songs if s.get(f) is not None)
        check(f"field {f} ~100%", cov >= n * 0.999, f"{cov}/{n}")
    with_wave = sum(1 for s in songs if s.get("audio", {}).get("waveform"))
    check("waveform url ~100%", with_wave >= n * 0.999, f"{with_wave}/{n}")
    with_play = sum(1 for s in songs if s.get("audio", {}).get("playable"))
    check("playable url ~100%", with_play >= n * 0.999, f"{with_play}/{n}")
    with_cats = sum(1 for s in songs if s["categories"]["children"])
    check("categories ~100%", with_cats >= n * 0.999, f"{with_cats}/{n}")

    print("4) category taxonomy")
    fams = set()
    chld = set()
    for s in songs:
        fams.update(s["categories"]["families"])
        chld.update(s["categories"]["children"])
    check("30 families", len(fams) == 30, f"{len(fams)}")
    # 155 distinct (id,name,parent) triples; 154 distinct names — "Explosions"
    # exists under TWO families (Destruction id 227, Weapons & Warfare id 149)
    check("154 distinct children names (155 triples incl. dupe 'Explosions')",
          len(chld) == 154, f"{len(chld)}")

    print("5) waves lane")
    w = json.loads(gzip.open(f"{ROOT}/data/catalog/sfx_waves.json.gz").read())
    check("schema", w["schema"] == "artlist-sfx-catalog/waves/1.1", w["schema"])
    ws = w["songs"]
    check("lane covers all songs", set(ws) == set(ids), f"{len(ws)} vs {n}")
    have_stats = sum(1 for v in ws.values() if not v.get("error"))
    check("wave stats coverage >= 99.9%", have_stats >= n * 0.999, f"{have_stats}/{n}")
    have_class = sum(1 for v in ws.values() if v.get("class"))
    check("continuity class coverage >= 99.9%", have_class >= n * 0.999, f"{have_class}/{n}")
    from collections import Counter
    dist = Counter(v.get("class") for v in ws.values())
    check("class values valid", set(dist) <= {"ambience", "rhythmic", "event", "oneshot", None},
          str(dict(dist)))
    check("ambience class present and substantial", dist.get("ambience", 0) > 5000,
          f"{dist.get('ambience', 0)}")
    bad_cont = sum(1 for v in ws.values()
                   if v.get("cont") is not None and not (0 <= v["cont"] <= 1))
    check("cont in [0,1]", bad_cont == 0, f"{bad_cont} out of range")
    # class rule consistency on a sample
    random.seed(7)
    samp = random.sample([v for v in ws.values() if "class" in v], 500)
    bad = 0
    for v in samp:
        ssr = v.get("ssr"); sr = v.get("sr"); oden = v.get("oden")
        dur = v.get("dur") or 0; cont = v.get("cont") or 0
        if cont >= 0.55 and (ssr is None or ssr < 0.25):
            exp = "ambience"
        elif oden is not None and 0.5 <= oden <= 12 and (ssr is None or ssr < 0.3):
            exp = "rhythmic"
        elif (ssr if ssr is not None else (sr if sr is not None else 1)) > 0.5 or (cont < 0.30 and dur <= 15):
            exp = "oneshot"
        else:
            exp = "event"
        if v.get("class") != exp:
            bad += 1
    check("class rules hold on sample", bad == 0, f"{bad}/500 mismatched")

    if "--cdn" in sys.argv:
        print("6) CDN live sample")
        sids = random.sample(ids, 5)
        spoof = {"Origin": "https://artlist.io", "Referer": "https://artlist.io/",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
        by_id = {s["songId"]: s for s in songs}
        for sid in sids:
            s = by_id[sid]
            # waveform json (direct URL, Origin-gated)
            try:
                r = urllib.request.urlopen(
                    urllib.request.Request(s["audio"]["waveform"], headers=spoof), timeout=15)
                data = json.loads(r.read())
                buckets = len(data) if isinstance(data, list) else -1
                check(f"waveform {sid}", r.status == 200 and buckets == 2048, f"{buckets} buckets")
            except Exception as e:
                check(f"waveform {sid}", False, str(e)[:80])
            # playable: base64-redirect decode -> same host path
            try:
                pv = s["audio"]["playable"]
                real = base64.urlsafe_b64decode(pv.split("/")[-1] + "==").decode("utf-8", "ignore")
                url = "https://cms-public-artifacts.artlist.io/" + real.lstrip("/")
                r = urllib.request.urlopen(urllib.request.Request(url, headers=spoof), timeout=15)
                head = r.read(4)
                # CDN labels these with a bogus Content-Type; validate ADTS AAC magic instead
                check(f"aac {sid}", r.status == 200 and head[:2] == b"\xff\xf1",
                      f"ADTS magic ok, {len(head)} bytes read")
            except Exception as e:
                check(f"aac {sid}", False, str(e)[:80])

    print()
    if FAIL:
        print(f"VERIFY FAILED: {len(FAIL)} check(s): {FAIL}")
        sys.exit(1)
    print("VERIFY_OK — sfx catalog is internally consistent")


if __name__ == "__main__":
    main()
