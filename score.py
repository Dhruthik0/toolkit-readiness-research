#!/usr/bin/env python3
"""Score agent output against the hand-built answer key (truth/labels.json) on the 20-app sample.

Per app, 5 fields. Truth lists every acceptable value where docs are genuinely ambiguous.
Every truth field is a list of acceptable answers.
  auth    : [offers OAuth2?, offers a static credential?] pair. Vendors call the same thing "API key",
            "token" or Basic auth, so the name is not scored, only the build-relevant split.
  access, mcp, verdict : enum value
  api     : the {REST, GraphQL} subset the agent found
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
FIELDS = ["auth", "access", "api", "mcp", "verdict"]
STATIC = {"API key", "Bearer token", "Basic", "JWT / service account", "HMAC signature"}


def auth_key(methods):
    return ("OAuth2" in methods, bool(STATIC & set(methods)))


def rule_verdict(rec):
    """The verdict definition from prompts/research.md, applied mechanically to the verified fields.
    Added after pass 1 hedged 85/100 apps as 'ready_with_caveats'."""
    if rec["access"] in ("partner_gated", "no_public_api"):
        return "blocked"
    if not {"REST", "GraphQL"} & set(rec["api_types"]):  # CLI/library-only: wrap as a sandboxed skill
        return "ready_with_caveats" if "CLI / library only" in rec["api_types"] else "blocked"
    return "ready" if rec["access"] == "self_serve_free" else "ready_with_caveats"


def finalize(rec, recheck=None):
    """Final record: the verifier's corrected record, overridden by the pass-3 recheck where one ran,
    with the verdict computed by rule_verdict.
    (An earlier version blocked every app whose access+API the verifier marked 'unsupported'. It fired on 7
    apps and 6 were false positives, because 'unsupported' mostly meant the docs page did not render.)"""
    rec = dict(rec)
    if recheck:
        rec.update(access=recheck["access"], api_types=recheck["api_types"], rechecked=True)
    rec["verdict"] = rule_verdict(rec)
    return rec


def judge(rec, t):
    return {
        "auth": list(auth_key(rec["auth_methods"])) in t["auth"],
        "access": rec["access"] in t["access"],
        "api": sorted({"REST", "GraphQL"} & set(rec["api_types"])) in [sorted(a) for a in t["api"]],
        "mcp": rec["mcp"] in t["mcp"],
        "verdict": rec["verdict"] in t["verdict"],
    }


def load(stage, i):
    """stage: pass1 | verified (LLM verdict) | final (verified + rule verdict)"""
    p = ROOT / "out" / ("pass1" if stage == "pass1" else "final") / f"{i}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    if stage == "pass1":
        return d["record"]
    rc = ROOT / "out" / "recheck" / f"{i}.json"
    rc = json.loads(rc.read_text())["recheck"] if rc.exists() else None
    return finalize(d["corrected"], rc) if stage == "final" else d["corrected"]


def answer_key(adjudicated=True):
    """Frozen key (truth/labels.json, hash in truth/FROZEN.txt) plus, optionally, the documented
    post-hoc corrections in truth/adjudications.json."""
    truth = json.loads((ROOT / "truth" / "labels.json").read_text())
    if adjudicated:
        for i, adj in json.loads((ROOT / "truth" / "adjudications.json").read_text()).items():
            truth[i] = dict(truth[i], **adj["set"], notes=truth[i]["notes"] + " [Adjudicated: " + adj["why"] + "]")
    return truth


def score(adjudicated=True):
    truth = answer_key(adjudicated)
    res = {}
    for stage in ("pass1", "verified", "final"):
        rows, hits = [], 0
        for i, t in truth.items():
            rec = load(stage, i)
            j = judge(rec, t) if rec else {f: False for f in FIELDS}
            hits += sum(j.values())
            rows.append({"id": i, "app": t["app"], "fields": j,
                         "got": rec and {"auth": rec["auth_methods"], "access": rec["access"],
                                         "api": rec["api_types"], "mcp": rec["mcp"], "verdict": rec["verdict"]}})
        total = len(truth) * len(FIELDS)
        per_field = {f: sum(r["fields"][f] for r in rows) for f in FIELDS}
        res[stage] = {"hits": hits, "total": total, "pct": round(100 * hits / total, 1),
                      "per_field": per_field, "rows": rows}
    return res


def _selfcheck():
    t = {"auth": [[True, True]], "access": ["self_serve_free"], "api": [["REST"]],
         "mcp": ["official"], "verdict": ["ready"]}
    rec = {"auth_methods": ["OAuth2", "Bearer token"], "access": "self_serve_free",
           "api_types": ["REST", "CLI / library only"], "mcp": "official", "verdict": "ready"}
    assert all(judge(rec, t).values())
    rec2 = dict(rec, auth_methods=["API key"], access="paid_plan")
    j = judge(rec2, t)
    assert not j["auth"] and not j["access"] and j["mcp"]
    assert rule_verdict(rec) == "ready" and rule_verdict(rec2) == "ready_with_caveats"
    assert rule_verdict(dict(rec, access="partner_gated")) == "blocked"
    assert rule_verdict(dict(rec, api_types=["CLI / library only"])) == "ready_with_caveats"
    assert rule_verdict(dict(rec, api_types=[])) == "blocked"
    assert finalize(rec, {"access": "partner_gated", "api_types": ["REST"]})["verdict"] == "blocked"
    assert finalize(rec)["verdict"] == "ready"


if __name__ == "__main__":
    _selfcheck()
    frozen = score(adjudicated=False)
    print("vs frozen key:", {k: v["pct"] for k, v in frozen.items()})
    r = score()
    (ROOT / "out" / "scores.json").write_text(json.dumps({"adjudicated": r, "frozen": frozen}, indent=2))
    print("vs adjudicated key:")
    for stage, s in r.items():
        print(f"  {stage:8} {s['hits']}/{s['total']} = {s['pct']}%  {s['per_field']}")
    for row in r["final"]["rows"]:
        bad = [f for f, ok in row["fields"].items() if not ok]
        if bad:
            print("  final miss:", row["app"], bad, row["got"])
