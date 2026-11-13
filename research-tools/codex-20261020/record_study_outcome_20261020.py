"""Update human-facing research notes from an audited saved result."""
import argparse
import json
from pathlib import Path

ROOT=Path(r'C:\Users\talk2.000\Desktop\Claude\predictive-anc')
PROGRESS=Path(r'C:\Users\talk2.000\Documents\Obsidian Vault\Predictive ANC\Progress log.md')


def main(n):
    folder=ROOT/f'results-tone-forecaster-{n}'
    review=json.loads((folder/'CODEX_REVIEW.json').read_text(encoding='utf-8'))
    candidate=review['candidate'];a=review['metrics'][candidate]
    joint=review['metrics']['joint_gated'];base=review['metrics']['v2_gated']
    outcome='passed all frozen questions' if review['all_frozen_questions_pass'] else 'did not pass all frozen questions'
    f=lambda v:'not available' if v is None else f'{v:.2f}'
    summary=(f"Study {n} {outcome} on {len(review['fresh_files'])} fresh recordings and "
             f"{review['synthetic_scenes']} fresh synthetic scenes. At 20 ms, median tone-bin prediction gain "
             f"was {f(a['tone_median_20ms_db'])} dB for the candidate, {f(joint['tone_median_20ms_db'])} dB "
             f"for joint + gate, and {f(base['tone_median_20ms_db'])} dB for v2 + gate. "
             f"Recording band-boost cases: {a['recording_band_boost_cases']}, "
             f"{joint['recording_band_boost_cases']} and {base['recording_band_boost_cases']}, respectively.")
    section=['## Test result, 20 Oct 2026','',summary,'',
             'The unchanged protocol was executed once after Sid granted full autonomy and authorized necessary '
             'downloads. Current Commons sizes and SHA-1s were checked against the frozen list; the downloaded '
             'bytes were then verified. No substitutes were used.','',
             f"Missing recordings: {', '.join(review['fresh_missing']) if review['fresh_missing'] else 'none'}. "
             'Any missing entries remain in the protocol and are disclosed rather than replaced.','']
    section.extend(f"- {k.replace('_',' ')}: **{'yes' if v else 'no'}**." for k,v in review['primary_questions'].items())
    section += ['',f"Full frozen report: [REPORT.md](../results-tone-forecaster-{n}/REPORT.md). "
                f"Independent recount of the saved scores and paired uncertainty: "
                f"[CODEX_REVIEW.md](../results-tone-forecaster-{n}/CODEX_REVIEW.md). "
                'This audit did not rerun or retune the models.', '',
                'These are reference-signal prediction results only. The test clips are now seen data and must not '
                'be reused as fresh evidence for a later chosen improvement. The live engine remains v2; '
                'multiprocessing timings are not quiet-machine qualification.','']
    document=ROOT/'docs'/('TONE_GATE_FADE.md' if n=='04' else 'TONE_REACT.md')
    text=document.read_text(encoding='utf-8')
    if '## Test result, 20 Oct 2026' in text:raise RuntimeError('Outcome already recorded.')
    intro=next(line for line in text.splitlines() if line.startswith('Claude, 19 Oct 2026'))
    text=text.replace(intro, f"Claude's 19 Oct development work was tested by Codex on 20 Oct 2026. "
                      f"Status: **{outcome}; the frozen test is complete.** "
                      f"Study folder: [results-tone-forecaster-{n}](../results-tone-forecaster-{n}/). "
                      'The development history below is retained; the fresh test result is recorded separately.',1)
    if n=='05':
        old="## Test\n\nNot run yet. It needs the eight files downloaded into a new folder, `external-audio/wikimedia-commons-fresh-05/`, and Sid hasn't approved that yet.\n\n"
        if old not in text:raise RuntimeError('Expected study-05 pending-test section.')
        text=text.replace(old,'\n'.join(section)+'\n',1)
    else:
        text=text.replace('## Timing\n','\n'.join(section)+'\n## Timing\n',1)
        text=text.replace('Downloads remain paused at Sid\'s request.',
                          'This was the preparation state. Sid subsequently authorized necessary downloads; see the completed test below.',1)
    # Replace the old forward-looking interpretation, while keeping the development evidence.
    start=text.index('## What it means so far\n');end=text.index('\n## Checks',start)
    interpretation=("## What it means so far\n\nThe frozen result above supersedes the development-only expectation. "
                    +("The frozen bar was met on this small sample; this does not establish universal benefit or physical ANC. "
                      if review['all_frozen_questions_pass'] else
                      "The development result did not satisfy every frozen fresh-test requirement, so this candidate is not promoted. ")
                    +"The engine still uses v2. The two studies address different transitions; their combination has not "
                    "been validated and needs its own development and fresh test. Quiet-machine timing and near-ear "
                    "validation remain separate from reference-prediction accuracy.\n")
    text=text[:start]+interpretation+text[end:]
    document.write_text(text,encoding='utf-8')

    status=ROOT/'docs/CONTINUATION_STATUS.md';text=status.read_text(encoding='utf-8')
    marker=f'### 20 Oct: completed frozen study {n}'
    if marker in text:raise RuntimeError('Status result already recorded.')
    text+='\n\n'+marker+'\n\n'+summary+'\n\n'
    text+=f"Missing: {', '.join(review['fresh_missing']) if review['fresh_missing'] else 'none'}. "
    text+='No replacement, retuning, playback or microphone capture. All figures are reference-prediction metrics. '
    text+=f"See [study {n}](../results-tone-forecaster-{n}/CODEX_REVIEW.md).\n"
    status.write_text(text,encoding='utf-8')
    progress=PROGRESS.read_text(encoding='utf-8')
    marker=f'## 2026-10-20 — frozen forecaster study {n} tested once'
    if marker in progress:raise RuntimeError('Progress result already recorded.')
    progress+='\n\n'+marker+'\n'
    progress+='- Sid authorized full autonomy and necessary downloads, superseding the earlier preparation-only direction.\n'
    progress+='- '+summary+'\n'
    progress+=f"- Missing inputs: {', '.join(review['fresh_missing']) if review['fresh_missing'] else 'none'}. "
    progress+='The frozen missing-file rule was followed; none was replaced. Source metadata, authorization and hashes are saved.\n'
    progress+='- The frozen runner executed once. A review recomputed its medians and boost counts from saved scores; no model rerun or retuning.\n'
    progress+='- No physical ANC claim or engine change; v2 remains in use. Reports: '
    progress+=f'`results-tone-forecaster-{n}/REPORT.md` and `CODEX_REVIEW.md`.\n'
    PROGRESS.write_text(progress,encoding='utf-8')
    print(summary)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',choices=['04','05']);main(p.parse_args().study)
