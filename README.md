# App toolkit research agent

Researches 100 apps for agent-toolkit buildability (auth, self-serve vs gated, API surface, MCP, verdict, evidence), verifies its own answers, and renders a one-page case study.

**Case study (live):** https://dhruthik0.github.io/toolkit-readiness-research/
**Machine-readable results:** [`data.json`](data.json) (100 final records with evidence URLs and per-claim verifier status)

Result: 49 apps ready today, 45 buildable with a caveat, 6 blocked. Field accuracy on a 20-app sample, scored against an answer key frozen before scoring: 88% (pass 1) → 93% (verifier) → 96% (recheck + rule verdict).

## Pipeline

1. **Research** (`agent.py research`): one headless Claude Code session per app, WebSearch + WebFetch only, output forced into `schema.json`.
2. **Verify** (`agent.py verify`): a fresh session re-fetches every cited URL, marks each claim supported / contradicted / unsupported, returns a corrected record.
3. **Recheck** (`agent.py recheck`): only for apps where the verifier could confirm neither access nor API; finds the vendor's own docs via llms.txt, .md pages, GitHub, help center.
4. **Rules** (`score.py: finalize`): verdict computed from the verified fields (the prompt's own definition), because the model hedged 88/100 verdicts as "caveats".
5. **Score** (`score.py`): field accuracy per stage against `truth/labels.json` (frozen, hash in `truth/FROZEN.txt`) and with the documented corrections in `truth/adjudications.json`.
6. **Publish** (`build_page.py`): renders `index.html` and `data.json`; every number on the page comes from the outputs.

## Run it

Needs Python 3.10+ and [Claude Code](https://claude.com/claude-code) logged in (`claude` on PATH). No API keys and no pip installs: the agent is headless Claude Code (`claude -p`) with only WebSearch and WebFetch enabled, so it runs on your Claude plan.

```bash
python3 agent.py research          # pass 1: one research session per app   -> out/pass1/<id>.json
python3 agent.py verify            # pass 2: independent fact-check + fix   -> out/final/<id>.json
python3 agent.py recheck           # pass 3: flagged apps only              -> out/recheck/<id>.json
python3 score.py                   # accuracy vs hand-built answer key      -> out/scores.json
python3 build_page.py              # renders index.html + data.json
```

Pass app ids to run a subset (`python3 agent.py research 2 41 81`). Finished apps are skipped, so a rerun resumes after failures. 6 apps run in parallel (`WORKERS` in `agent.py`).

## Files

| File | What it is |
|---|---|
| `apps.csv` | The 100 apps from the brief |
| `schema.json` | Output contract every research session must fill (enforced with `--json-schema`) |
| `prompts/research.md` | Pass 1 instructions, including the definitions of each access tier and verdict |
| `prompts/verify.md` | Pass 2 instructions: re-fetch every cited URL, mark each claim supported / contradicted / unsupported, return a corrected record |
| `prompts/recheck.md` | Pass 3 instructions: reach the vendor's own docs by alternate routes |
| `out/pass1`, `out/final`, `out/recheck` | Raw agent output per app (pass 1, pass 2 checks + corrected record, pass 3) |
| `page_template.html` | Page layout; `build_page.py` fills it |
| `composio.json` | Which apps already have a Composio toolkit, matched by hand against the catalog at composio.dev/toolkits |
| `sample.py`, `truth/sample_ids.json` | Seeded, stratified 20-app sample (2 per category), drawn before any agent output existed |
| `truth/labels.json` | Answer key for the sample, built before scoring from vendor quotes and browser checks; ambiguous fields list every acceptable answer |
| `truth/adjudications.json` | Two post-hoc corrections to the key, with reasons (the key was wrong on fanbasis and inconsistent on Lark) |
| `score.py` | Field-level accuracy of pass 1 and final against the answer key |
| `build_page.py` | Builds `index.html` (the case study) and `data.json` (all 100 records, machine-readable) |

## Cost and runtime

About $14 of API-equivalent usage on a Claude plan for all three passes (shown per app in each output's `meta`). Each pass takes about 2–3 minutes per app, with 6 apps running in parallel.
