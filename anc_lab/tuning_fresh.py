"""Fresh-recording test of the frozen tuner candidate SD-s30 against the original tuner. Never opens audio devices.

results-engine-smoothing-01 chose SD-s30 (search change + sequential check + the
alpha 0.3 engine smoother) on seen development rooms. Nothing in those modules
changes here. This study applies the same four-condition rule, one time, to rooms
built from recordings no earlier study has used.

Stages: freeze (identities and rule, before any media byte), download, rooms
(build scenes; tone menus are fixed before tuning), run, summarize.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import argparse
import csv
import hashlib
import json
import subprocess

import numpy as np
from threadpoolctl import threadpool_limits

from . import selector_headroom as h
from . import selector_room_scoring as scoring
from . import tuning_ablation as ab
from . import tuning_decision as td
from . import engine_smoothing as es
from . import antihum_study as room
from .antihum import FS, BLOCK
from .real_hum_study import load_any, prominent_tones
from .selector_stream_profile import cached_dpss

ROOT = h.ROOT
STUDY = ROOT/'results-tuning-fresh-01'
AUDIO = ROOT/'external-audio/wikimedia-commons-tuning-fresh-01'
LEAD = es.LEAD
ALPHA = es.ALPHAS['s30']
ARMS = ('O', 'SD-s30')
TUNERS = {'O': (False, False), 'SD-s30': (True, True)}
SIGMAS = td.SIGMAS
SEEDS = td.SEEDS
ROOMS_PER_SOURCE = 3
ROOM_SEED = 20261030
CAP_SECONDS = 90.
MIN_SECONDS = 51.
MIN_SOURCES = 12
MIN_ROOMS = 25
WORKERS = 20
NO_ORACLE = {'oracle': {'identifiable': False}}
FILES = ['anc_lab/tuning_fresh.py', 'tests/test_tuning_fresh.py', 'anc_lab/engine_smoothing.py', 'tests/test_engine_smoothing.py',
         'anc_lab/tuning_decision.py', 'anc_lab/tuning_ablation.py', 'anc_lab/tuning.py', 'anc_lab/antihum_study.py',
         'anc_lab/antihum.py', 'anc_lab/selector_room_scoring.py', 'anc_lab/selector_room_stream.py',
         'anc_lab/selector_compatibility.py', 'anc_lab/tuning_accuracy_diagnostic.py', 'anc_lab/real_hum_study.py',
         'docs/TUNING_FRESH_TEST.md', 'research-tools/tuning-fresh-01/freeze_tuning_fresh.py',
         'research-tools/tuning-fresh-01/discover_tuning_sources.py', 'research-tools/tuning-fresh-01/screen_tuning_sources.py',
         'research-tools/tuning-fresh-01/download_tuning_fresh.py', 'research-tools/tuning-fresh-01/picks.txt']


def room_seed(source_id, k):
    return int.from_bytes(hashlib.sha256(f'{ROOM_SEED}-{source_id}-{k}'.encode()).digest()[:4], 'big')


def needs_decode(entry):
    return entry['mime'].startswith('video/') or Path(entry['file']).suffix.lower() in ('.ogv', '.webm', '.mp4', '.mkv', '.opus')


def verified():
    p = h.read(STUDY/'protocol.json')
    assert h.sha(STUDY/'protocol.json') == h.read(STUDY/'frozen.json')['sha256']
    for name, digest in p['code_sha256'].items():
        assert h.sha(ROOT/name) == digest, name
    return p


# ---------------- rooms ----------------
def dry_signal(entry, download, decoder):
    """Channel zero of the first audio track, first 90 s, prefix-normalized as the earlier fresh test."""
    path = ROOT/download['local_path']
    assert h.sha(path) == download['sha256']
    decoded = path
    if needs_decode(entry):
        decoded = STUDY/'decoded'/f"{entry['id']}.wav"
    if decoded != path and not decoded.exists():
        run = subprocess.run([decoder, '-nostdin', '-v', 'error', '-n', '-i', str(path), '-t', '90', '-map', '0:a:0', '-vn',
                              '-c:a', 'pcm_f64le', str(decoded)], capture_output=True, text=True, timeout=180, cwd=str(STUDY))
        if run.returncode:
            raise ValueError('no decodable first audio track: '+run.stderr[-300:])
    x, info = load_any(decoded, max_seconds=CAP_SECONDS)
    if len(x)/FS < MIN_SECONDS:
        raise ValueError(f'only {len(x)/FS:.1f} s of audio')
    prefix = int(.4*len(x))
    if np.std(x[:prefix]) < 1e-12:
        raise ValueError('silent prefix')
    return (x-float(np.mean(x[:prefix])))/float(np.std(x[:prefix])), info, prefix


def build_room(dry, seed):
    """Same draw order as selector_room_study.preparation_task for a saved reference."""
    rng = np.random.default_rng(seed)
    geometry = room.draw_room(rng)
    scene = room.prepare_scene(dry, geometry, int(rng.integers(1 << 30)))
    scene['trace'] = {'v2': scene['arrays']}
    return geometry, scene


def room_task(args):
    entry, download, decoder = args
    out = {'source_id': entry['id'], 'title': entry['title'], 'cases': []}
    try:
        dry, info, prefix = dry_signal(entry, download, decoder)
    except Exception as exc:
        return {**out, 'status': 'excluded', 'reason': f'{type(exc).__name__}: {exc}'}
    tones = prominent_tones(dry[prefix:])
    with threadpool_limits(limits=1), cached_dpss(True):
        for k in range(ROOMS_PER_SOURCE):
            seed = room_seed(entry['id'], k)
            geometry, scene = build_room(dry, seed)
            case_id = f"{entry['id']}-r{k}"
            out['cases'].append({'case_id': case_id, 'source_id': entry['id'], 'room_index': k, 'seed': seed,
                                 'menu_tones': len(scene['tones']), 'tone_hz': [t['frequency'] for t in scene['tones']],
                                 'seeds': td.seeds_for(case_id, seed)})
    return {**out, 'status': 'built', 'audio': info, 'reference_tones_hz': tones, 'samples': len(dry)}


def rooms():
    p = verified()
    manifest = h.read(STUDY/'download/manifest.json')
    assert manifest['protocol_sha256'] == h.sha(STUDY/'protocol.json')
    (STUDY/'decoded').mkdir(exist_ok=False)
    downloads = {d['id']: d for d in manifest['files']}
    jobs = [(e, downloads[e['id']], p['decoder']['path']) for e in p['sources'] if downloads[e['id']]['status'] == 'verified']
    rows = []
    with ProcessPoolExecutor(WORKERS) as pool:
        for job in as_completed([pool.submit(room_task, j) for j in jobs]):
            r = job.result()
            rows.append(r)
            print(json.dumps({'source': r['source_id'], 'status': r['status'], 'rooms_with_tones': sum(c['menu_tones'] > 0 for c in r['cases'])}), flush=True)
    rows.sort(key=lambda r: r['source_id'])
    rows += [{'source_id': d['id'], 'title': d['title'], 'status': 'excluded', 'reason': d.get('reason', 'download failed'), 'cases': []}
             for d in manifest['files'] if d['status'] != 'verified']
    cases = [c for r in rows for c in r['cases'] if c['menu_tones'] > 0]
    h.write_new(STUDY/'rooms.json', {'created_utc': td.now(), 'protocol_sha256': h.sha(STUDY/'protocol.json'),
                                     'sources': rows, 'eligible_cases': cases,
                                     'eligible_sources': len({c['source_id'] for c in cases})})
    print(json.dumps({'eligible_rooms': len(cases), 'eligible_sources': len({c['source_id'] for c in cases}),
                      'tones': sum(c['menu_tones'] for c in cases)}), flush=True)


# ---------------- scoring ----------------
def tuned_run(scene, reference, sigma, k, seed, arm):
    search, sequential = TUNERS[arm]
    settings, summaries = td.tune(scene, seed, sigma, search, sequential)
    metrics, _ = scoring.evaluate(scene, settings, LEAD, 'v2', reference)
    tones = ab.tone_rows(scene, summaries, ab.tone_bases(scene), [NO_ORACLE]*len(scene['tones']))
    return {'sigma': sigma, 'seed_index': k, 'seed': seed, 'arm': arm,
            'settings': [asdict(s) for s in settings], 'room': metrics, 'tones': tones}


def score_case(c, entry, download, decoder, reference):
    with threadpool_limits(limits=1), cached_dpss(True):
        dry, _, _ = dry_signal(entry, download, decoder)
        _, scene = build_room(dry, c['seed'])
        assert [t['frequency'] for t in scene['tones']] == c['tone_hz'], c['case_id']
        smooth = es.engine_scene(scene, ALPHA)
        runs = [tuned_run(scene if arm == 'O' else smooth, reference, sigma, k, seed, arm)
                for sigma in SIGMAS for k, seed in enumerate(c['seeds']) for arm in ARMS]
    return {'case_id': c['case_id'], 'source_id': c['source_id'], 'runs': runs}


def run_all():
    p = verified()
    built = h.read(STUDY/'rooms.json')
    assert built['protocol_sha256'] == h.sha(STUDY/'protocol.json')
    h.write_new(STUDY/'scoring-seal.json', {'rooms_sha256': h.sha(STUDY/'rooms.json'), 'protocol_sha256': h.sha(STUDY/'protocol.json')})
    dest = STUDY/'cases'
    dest.mkdir(exist_ok=False)
    entries = {e['id']: e for e in p['sources']}
    downloads = {d['id']: d for d in h.read(STUDY/'download/manifest.json')['files']}
    references = {r['source_id']: r.get('reference_tones_hz', []) for r in built['sources']}
    h.write_new(STUDY/'run-start.json', {'started_utc': td.now(), 'workers': WORKERS})
    done = 0
    with ProcessPoolExecutor(WORKERS) as pool:
        jobs = [pool.submit(score_case, c, entries[c['source_id']], downloads[c['source_id']], p['decoder']['path'], references[c['source_id']])
                for c in built['eligible_cases']]
        for job in as_completed(jobs):
            result = job.result()
            h.write_new(dest/(result['case_id']+'.json'), result)
            done += 1
            print(json.dumps({'case': result['case_id'], 'complete': done, 'of': len(jobs)}), flush=True)
    h.write_new(STUDY/'run-complete.json', {'completed_utc': td.now(), 'cases': done})


# ---------------- summary ----------------
def decide(tone_ci_lower, band_mean, counts, base_counts, sources, rooms_n):
    criteria = {'enough_sources': sources >= MIN_SOURCES, 'enough_rooms': rooms_n >= MIN_ROOMS,
                'tone_level_ci_lower_above_0': bool(tone_ci_lower > 0),
                'harmful_keeps_no_more': counts['harmful_keeps_prefix'] <= base_counts['harmful_keeps_prefix'],
                'harmed_rooms_no_more': counts['room_harms'] <= base_counts['room_harms'],
                'whole_room_at_least_minus_0_05': bool(band_mean >= -.05)}
    adequate = criteria['enough_sources'] and criteria['enough_rooms']
    verdict = 'inconclusive_too_few_rooms' if not adequate else 'pass' if all(criteria.values()) else 'fail'
    return criteria, verdict


def summarize():
    p = verified()
    assert (STUDY/'run-complete.json').exists()
    built = h.read(STUDY/'rooms.json')
    cases = [h.read(STUDY/'cases'/(c['case_id']+'.json')) for c in built['eligible_cases']]
    out, table = {'by_sigma': {}}, []
    band = lambda r: r['room']['band_db']
    boost = lambda r: r['room']['max_third_octave_amplification_db']
    for sigma in SIGMAS:
        runs = {(c['case_id'], r['seed_index'], r['arm']): (c['source_id'], r) for c in cases for r in c['runs'] if r['sigma'] == sigma}
        stats = {}
        for i, arm in enumerate(ARMS):
            rng = lambda j: np.random.default_rng([td.BOOTSTRAP_SEED, int(sigma*10), i, j, 7])
            counts, level = Counter(), {}
            for (case, k, a), (source, r) in runs.items():
                if a != arm:
                    continue
                counts['room_runs'] += 1
                counts['room_harms'] += ab.room_harm(r['room'])
                level.setdefault(source, {}).setdefault(case, []).append(td.tone_level(r))
                for t in r['tones']:
                    counts['tones'] += 1
                    counts['kept'] += t['kept']
                    counts['harmful_keeps_prefix'] += t['kept'] and t['final_effect']['prefix_erb_db'] < -1e-9
                    counts['harmful_keeps_suffix'] += t['kept'] and t['final_effect']['suffix_erb_db'] < -1e-9
                    counts['useful_keeps'] += t['kept'] and t['final_effect']['prefix_erb_db'] >= td.USEFUL_DB
                    table.append({'sigma': sigma, 'arm': arm, 'case_id': case, 'source_id': source, 'seed_index': k,
                                  'tone_index': t['tone_index'], 'frequency_hz': t['frequency'], 'kept': t['kept'],
                                  'final_prefix_erb_db': t['final_effect']['prefix_erb_db'],
                                  'final_suffix_erb_db': t['final_effect']['suffix_erb_db'], 'check_pairs': t['check_pairs'],
                                  'listening_seconds': t['listening_seconds'], 'room_band_db': r['room']['band_db'],
                                  'room_max_third_octave_db': r['room']['max_third_octave_amplification_db']})
            stats[arm] = {'tone_level_db': ab.bootstrap(ab.source_means(level), rng(0)),
                          'tone_level_minus_O': ab.bootstrap(es.paired(runs, arm, 'O', td.tone_level), rng(1)),
                          'band_db_minus_O': ab.bootstrap(es.paired(runs, arm, 'O', band), rng(2)),
                          'max_third_octave_minus_O': ab.bootstrap(es.paired(runs, arm, 'O', boost), rng(3)),
                          'counts': dict(counts)}
        s = stats['SD-s30']
        s['criteria'], s['verdict'] = decide(s['tone_level_minus_O']['ci95'][0], s['band_db_minus_O']['mean'], s['counts'],
                                             stats['O']['counts'], len({c['source_id'] for c in cases}), len(cases))
        out['by_sigma'][f'{sigma:g}'] = stats
    out['verdict'] = out['by_sigma']['1']['SD-s30']['verdict']
    h.write_new(STUDY/'summary.json', out)
    with (STUDY/'tone-runs.csv').open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    print(json.dumps({'verdict': out['verdict'], 'sigma1': {a: {k: out['by_sigma']['1'][a][k] for k in ('tone_level_minus_O', 'band_db_minus_O', 'counts')} for a in ARMS},
                      'criteria': out['by_sigma']['1']['SD-s30']['criteria']}, indent=1), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['rooms', 'run', 'summarize'])
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        {'rooms': rooms, 'run': run_all, 'summarize': summarize}[args.stage]()
