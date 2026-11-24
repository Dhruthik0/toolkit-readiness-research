#!/usr/bin/env python3
"""Research agent: runs one headless Claude Code session per app.

  python3 agent.py research [ids...]   # pass 1  -> out/pass1/<id>.json
  python3 agent.py verify   [ids...]   # pass 2  -> out/final/<id>.json (checks + corrected record)
  python3 agent.py recheck  [ids...]   # pass 3  -> out/recheck/<id>.json, only apps where pass 2 could
                                       #            confirm neither access nor API

No ids = all 100. Existing outputs are skipped, so reruns resume. Needs `claude` logged in.
"""
import csv, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent
SCHEMA = json.loads((ROOT / "schema.json").read_text())
FIELDS = ["auth", "access", "api", "mcp", "verdict"]
VERIFY_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["checks", "corrected"],
    "properties": {
        "checks": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["field", "status", "note", "url"],
            "properties": {"field": {"enum": FIELDS},
                           "status": {"enum": ["supported", "contradicted", "unsupported"]},
                           "note": {"type": "string"}, "url": {"type": ["string", "null"]}}}},
        "corrected": SCHEMA,
    },
}
RECHECK_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["vendor_docs_url", "access", "api_types", "evidence_quote", "notes"],
    "properties": {"vendor_docs_url": {"type": ["string", "null"]},
                   "access": SCHEMA["properties"]["access"], "api_types": SCHEMA["properties"]["api_types"],
                   "evidence_quote": {"type": "string"}, "notes": {"type": "string"}},
}
MODEL, WORKERS, TIMEOUT = "sonnet", 6, 900


def apps():
    return {r["id"]: r for r in csv.DictReader(open(ROOT / "apps.csv"))}


def claude(prompt, schema):
    cmd = ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json",
           "--json-schema", json.dumps(schema), "--tools", "WebSearch,WebFetch",
           "--allowedTools", "WebSearch,WebFetch",
           "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"]
    for attempt in range(4):  # Claude Code's auto-updater briefly removes the binary mid-run
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd="/tmp")
            break
        except FileNotFoundError:
            if attempt == 3:
                raise
            time.sleep(30)
    res = json.loads(out.stdout)
    if res.get("is_error") or not res.get("structured_output"):
        raise RuntimeError(res.get("result") or out.stderr[-500:])
    meta = {"cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns")}
    return res["structured_output"], meta


def fill(template, **kw):
    s = (ROOT / "prompts" / template).read_text()
    for k, v in kw.items():
        s = s.replace("{{" + k + "}}", v)
    return s


def needs_recheck(i):
    """Verifier could confirm neither access nor API for this app."""
    p = ROOT / "out" / "final" / f"{i}.json"
    if not p.exists():
        return False
    st = {c["field"]: c["status"] for c in json.loads(p.read_text())["checks"]}
    return st.get("access") == "unsupported" and st.get("api") == "unsupported"


def run(mode, app):
    src = ROOT / "out" / ("final" if mode == "recheck" else "pass1") / f"{app['id']}.json"
    dst = ROOT / "out" / {"research": "pass1", "verify": "final", "recheck": "recheck"}[mode] / f"{app['id']}.json"
    if dst.exists():
        return f"skip {app['app']}"
    if mode == "research":
        prompt, schema = fill("research.md", app=app["app"], hint=app["hint"]), SCHEMA
    elif mode == "verify":
        rec = json.loads(src.read_text())["record"]
        prompt, schema = fill("verify.md", app=app["app"], hint=app["hint"],
                              record=json.dumps(rec, indent=2)), VERIFY_SCHEMA
    else:
        rec = json.loads(src.read_text())["corrected"]
        prompt, schema = fill("recheck.md", app=app["app"], hint=app["hint"],
                              record=json.dumps(rec, indent=2)), RECHECK_SCHEMA
    try:
        data, meta = claude(prompt, schema)
    except Exception as e:  # one bad app must not kill the batch; rerun picks it up
        return f"FAIL {app['app']}: {str(e)[:200]}"
    body = {"id": app["id"], "input": app, "meta": meta}
    body.update({"record": data} if mode == "research" else data if mode == "verify" else {"recheck": data})
    dst.write_text(json.dumps(body, indent=2))
    return f"ok   {app['app']} ({meta['turns']} turns)"


if __name__ == "__main__":
    mode, ids = sys.argv[1], sys.argv[2:]
    assert mode in ("research", "verify", "recheck"), __doc__
    todo = [a for i, a in apps().items() if (not ids or i in ids) and (mode != "recheck" or needs_recheck(i))]
    with ThreadPoolExecutor(WORKERS) as ex:
        for line in ex.map(lambda a: run(mode, a), todo):
            print(line, flush=True)
