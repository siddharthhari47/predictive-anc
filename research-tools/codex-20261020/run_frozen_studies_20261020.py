"""Download approved frozen inputs, or run one unchanged offline study exactly once."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(r"C:\Users\talk2.000\Desktop\Claude\predictive-anc")
sys.path.insert(0, str(ROOT))
API = "https://commons.wikimedia.org/w/api.php"
UA = "PredictiveANCResearch/0.6 (local offline experiment; frozen Commons audio inputs)"
AUTHORIZATION = "u have full autonomy proceed anddownload whatever u feel necessary"


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def sha(path, kind="sha256"):
    h = hashlib.new(kind)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def plain(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def request(url):
    for attempt in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=35)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or attempt == 3:
                raise
            wait = max(10*(attempt+1), min(30, float(e.headers.get("Retry-After") or 0)))
            print(f"HTTP {e.code}; retrying the same request in {wait:g} seconds.", flush=True)
            time.sleep(wait)


def module_for(study):
    if study == "04":
        from anc_lab import forecaster_study_04 as mod
    else:
        from anc_lab import forecaster_study_05 as mod
    return mod


def checked_protocol(mod):
    path = mod.STUDY / "protocol.json"
    p = json.loads(path.read_text(encoding="utf-8"))
    if p["code_sha256"] != mod._code_hashes():
        raise RuntimeError("Frozen source checksums changed.")
    if (mod.STUDY / "test").exists() or (mod.STUDY / "REPORT.md").exists():
        raise RuntimeError("Test/report already exists; do not repeat a held-out test.")
    return p, sha(path)


def download(study, resume=False):
    mod = module_for(study)
    p, phash = checked_protocol(mod)
    logdir = mod.STUDY / "download-20261020"
    if (logdir.exists() or mod.FRESH_AUDIO.exists()) and not resume:
        raise RuntimeError("Download output exists; inspect it rather than overwrite or repeat.")
    if resume:
        if not logdir.exists() or (logdir/'download_manifest.json').exists():
            raise RuntimeError("Resume only a partial download; a completed manifest must not be replaced.")
        attempt = len(list(logdir.glob('resume-*.json'))) + 1
        save(logdir/f'resume-{attempt:02d}.json', {'started_utc': now(), 'reason': 'Resume missing inputs after HTTP 429; preserve verified downloads.',
                                               'protocol_sha256': phash, 'direct_user_authorization': AUTHORIZATION})
        print('Allowing 30 seconds for the server rate limit before resuming missing files.', flush=True)
        time.sleep(30)
    else:
        logdir.mkdir()
        save(logdir / "authorization.json", {"recorded_utc": now(), "user_facing_date_India": "2026-10-20",
             "direct_user_authorization": AUTHORIZATION, "scope": f"Frozen study {study} recording batch and offline test",
             "protocol_sha256": phash, "files": [e["file"] for e in p["fresh_recordings"]]})
    params = {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5,
              "titles": "|".join(e["title"] for e in p["fresh_recordings"]), "prop": "imageinfo",
              "iiprop": "url|size|sha1|timestamp|mime|extmetadata",
              "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|Credit|ImageDescription"}
    url = API + "?" + urllib.parse.urlencode(params)
    print(f"Study {study}: checking current Commons metadata for {len(p['fresh_recordings'])} frozen inputs.", flush=True)
    if resume:
        metadata = json.loads((logdir/'commons_metadata.json').read_text(encoding='utf-8'))
    else:
        with request(url) as response:
            metadata = json.load(response)
        save(logdir / "commons_metadata.json", metadata)
    if "error" in metadata:
        raise RuntimeError(f"Commons API error: {metadata['error']}")
    pages = {page["title"]: page for page in metadata["query"]["pages"]}
    rows = []
    for entry in p["fresh_recordings"]:
        page = pages.get(entry["title"])
        ii = page.get("imageinfo", []) if page else []
        if not ii:
            rows.append({"file": entry["file"], "status": "missing", "reason": "No current imageinfo; not replaced."})
            continue
        info = ii[0]
        if info["sha1"] != entry["sha1"] or info["size"] != entry["bytes"]:
            raise RuntimeError(f"Current Commons size/SHA-1 differs from frozen protocol: {entry['file']}")
        parsed = urllib.parse.urlparse(info["url"])
        if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
            raise RuntimeError("Unexpected raw-audio download host.")
        ext = info.get("extmetadata", {})
        licence = plain(ext.get("LicenseShortName", {}).get("value", ""))
        if not (licence in {"CC0", "Public domain"} or re.fullmatch(r"CC BY(?:-SA)? [1-4]\.\d", licence)):
            raise RuntimeError(f"Unrecognized current free-licence label: {entry['file']}: {licence}")
        author = plain(ext.get("Artist", {}).get("value", ""))
        rows.append({"file": entry["file"], "status": "metadata_verified", "url": info["url"],
                     "source_page": info.get("descriptionurl"), "sha1": info["sha1"], "bytes": info["size"],
                     "current_author": author, "current_licence": licence,
                     "licence_url": ext.get("LicenseUrl", {}).get("value"),
                     "metadata_author_changed": author != entry["author"],
                     "metadata_licence_changed": licence != entry["licence"]})
    # Complete metadata validation for the entire batch before downloading the first file.
    mod.FRESH_AUDIO.mkdir(exist_ok=resume)
    for index, row in enumerate(rows, 1):
        if row["status"] == "missing":
            print(f"{index}/{len(rows)} unavailable: {row['file']}", flush=True)
            continue
        name = row["file"]
        if Path(name).name != name or any(c in name for c in ("/", "\\")):
            raise RuntimeError("Unsafe local filename.")
        target = mod.FRESH_AUDIO / name
        part = mod.FRESH_AUDIO / (name + ".part")
        if resume and target.exists():
            if target.stat().st_size != row['bytes'] or sha(target,'sha1') != row['sha1']:
                raise RuntimeError('Existing download differs from the frozen input.')
            previous = json.loads((logdir/f'file-{index:02d}.json').read_text(encoding='utf-8'))
            if previous['sha256'] != sha(target):
                raise RuntimeError('Existing download differs from the earlier verified receipt.')
            rows[index-1] = previous
            print(f'{index}/{len(rows)} already verified; retained {name}', flush=True)
            continue
        if target.exists() or part.exists():
            raise RuntimeError("Download target exists.")
        time.sleep(3)
        print(f"{index}/{len(rows)} downloading {name} ({row['bytes']/1e6:.2f} MB)", flush=True)
        try:
            with request(row["url"]) as response, part.open("xb") as dest:
                final = urllib.parse.urlparse(response.geturl())
                if final.scheme != "https" or final.hostname != "upload.wikimedia.org":
                    raise RuntimeError("Unexpected redirect host.")
                count = 0
                for chunk in iter(lambda: response.read(256*1024), b""):
                    count += len(chunk)
                    if count > row["bytes"]:
                        raise RuntimeError("Downloaded stream exceeds frozen byte length.")
                    dest.write(chunk)
            if part.stat().st_size != row["bytes"] or sha(part, "sha1") != row["sha1"]:
                raise RuntimeError(f"Downloaded bytes/SHA-1 mismatch: {name}")
            row["sha256"] = sha(part)
            part.rename(target)
            row["status"] = "verified_download"
            row["completed_utc"] = now()
        except urllib.error.HTTPError as e:
            if e.code not in (404, 410, 429, 502, 503, 504):
                raise
            row.update(status="missing", reason=f"HTTP {e.code} after bounded retries/backoff; not replaced",
                       failure_detail=str(e), failed_utc=now())
            print(f"{name} remains unavailable (HTTP {e.code}); record as missing under the frozen rule.", flush=True)
        save(logdir / f"file-{index:02d}.json", row)
    result = {"completed_utc": now(), "protocol_sha256": phash,
              "direct_user_authorization": AUTHORIZATION, "files": rows,
              "downloaded": sum(r["status"] == "verified_download" for r in rows),
              "missing": [r["file"] for r in rows if r["status"] == "missing"],
              "bytes_verified": sum(r["bytes"] for r in rows if r["status"] == "verified_download")}
    save(logdir / "download_manifest.json", result)
    sources = [f"# Study {study}: frozen Wikimedia Commons audio inputs", "",
               "Downloaded locally with Sid's direct authorization on 20 Oct 2026 (India time). "
               "Raw audio remains local. Exact sizes/SHA-1s match the already-frozen protocol; no substitutes.", "",
               "| File | Credited author | Current licence | Source |", "|---|---|---|---|"]
    for row in rows:
        if row["status"] == "verified_download":
            sources.append(f"| {row['file']} | {row['current_author'].replace(chr(10),' ')} | "
                           f"{row['current_licence']} | [Commons file page]({row['source_page']}) |")
    sources += ["", f"Full request, metadata, authorization and checksums: `results-tone-forecaster-{study}/download-20261020/`." ]
    with (mod.FRESH_AUDIO / "SOURCES.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sources)+"\n")
    for e in p["fresh_recordings"]:
        mod.fs2.fresh_path(e, mod.FRESH_AUDIO)
    print(json.dumps({k:result[k] for k in ("downloaded", "missing", "bytes_verified")}), flush=True)


def run(study, workers):
    mod = module_for(study)
    p, phash = checked_protocol(mod)
    manifest_path = mod.STUDY / "download-20261020/download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != phash:
        raise RuntimeError("Download manifest belongs to another protocol.")
    receipt = mod.STUDY / "execution-20261020.json"
    save(receipt, {"started_utc": now(), "study": study, "protocol_sha256": phash, "workers": workers,
                  "direct_user_authorization": AUTHORIZATION, "frozen_runner": f"forecaster_study_{study}.run_test",
                  "frozen_source_files_checked": len(p["code_sha256"]), "single_test_attempt": True})
    stopped = threading.Event()
    start = time.monotonic()
    def heartbeat():
        import psutil
        proc = psutil.Process()
        while not stopped.wait(30):
            children = proc.children(recursive=True)
            rss = 0
            for child in children:
                try: rss += child.memory_info().rss
                except psutil.NoSuchProcess: pass
            print(f"Study {study} processing: {(time.monotonic()-start)/60:.1f} min elapsed; "
                  f"{len(children)} child processes; worker memory {rss/1e9:.2f} GB; "
                  f"system free {psutil.virtual_memory().available/1e9:.2f} GB.", flush=True)
    watcher = threading.Thread(target=heartbeat, daemon=True)
    watcher.start()
    print(f"Starting frozen study {study} once, {workers} workers. No playback or input stream.", flush=True)
    try:
        result = mod.run_test(workers=workers)
        save(mod.STUDY / "execution-complete-20261020.json",
             {"completed_utc": now(), "runtime_seconds": result["runtime_seconds"],
              "test_json_sha256": sha(mod.STUDY/"test/test.json"), "protocol_sha256": phash,
              "fresh_files": result["fresh_files"], "fresh_missing": result["fresh_missing"]})
        print(f"Study {study} complete in {result['runtime_seconds']/60:.2f} minutes. Report saved.", flush=True)
    except BaseException:
        save(mod.STUDY / "execution-failed-20261020.json",
             {"failed_utc": now(), "error": traceback.format_exc(), "instruction": "Preserve failed run; do not silently retest."})
        raise
    finally:
        stopped.set()
        watcher.join(timeout=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("download", "test"))
    parser.add_argument("study", choices=("04", "05"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT.resolve():
        raise RuntimeError("Run from the project root, never from the downloaded-audio folder.")
    if args.action == "download":
        download(args.study, args.resume)
    else:
        run(args.study, args.workers)
