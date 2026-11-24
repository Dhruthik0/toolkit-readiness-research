#!/usr/bin/env python3
"""Build index.html (the case study) and data.json (all 100 final records) from out/ + truth/.

  python3 build_page.py          # writes index.html, data.json
  python3 build_page.py --stats  # prints the aggregate numbers the headline text is written from
"""
import csv, html, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

from score import ROOT, STATIC, FIELDS, answer_key, finalize, score

ACCESS = ["self_serve_free", "self_serve_trial", "paid_plan", "approval_required", "partner_gated", "no_public_api"]
ACCESS_LABEL = {"self_serve_free": "Free self-serve", "self_serve_trial": "Trial only", "paid_plan": "Paid plan",
                "approval_required": "Vendor approval", "partner_gated": "Partner / sales", "no_public_api": "No public API"}
VERDICT_LABEL = {"ready": "Ready", "ready_with_caveats": "Caveats", "blocked": "Blocked"}
GATED = {"approval_required", "partner_gated", "no_public_api"}


def records():
    apps = list(csv.DictReader(open(ROOT / "apps.csv")))
    comp = json.loads((ROOT / "composio.json").read_text())["apps"]
    out = []
    for a in apps:
        p1 = json.loads((ROOT / "out/pass1" / f"{a['id']}.json").read_text())["record"]
        fin = json.loads((ROOT / "out/final" / f"{a['id']}.json").read_text())
        rc = ROOT / "out/recheck" / f"{a['id']}.json"
        rc = json.loads(rc.read_text())["recheck"] if rc.exists() else None
        r = finalize(fin["corrected"], rc)
        r.update(id=int(a["id"]), app=a["app"], group=a["category"], hint=a["hint"],
                 llm_verdict=fin["corrected"]["verdict"], composio=comp[a["id"]],
                 checks=fin["checks"], recheck=rc,
                 changed=[k for k in ("auth_methods", "access", "api_types", "mcp", "verdict")
                          if p1[k] != fin["corrected"][k]],
                 no_evidence=[k for k, v in r["evidence"].items() if not v])
        out.append(r)
    return out


def stats(R):
    n = len(R)
    oauth = sum("OAuth2" in r["auth_methods"] for r in R)
    static = sum(bool(STATIC & set(r["auth_methods"])) for r in R)
    both = sum("OAuth2" in r["auth_methods"] and bool(STATIC & set(r["auth_methods"])) for r in R)
    by_group = defaultdict(Counter)
    for r in R:
        by_group[r["group"]][r["access"]] += 1
    checks = Counter(c["status"] for r in R for c in r["checks"])
    return {
        "n": n, "oauth": oauth, "static": static, "both": both,
        "oauth_only": oauth - both, "static_only": static - both,
        "access": Counter(r["access"] for r in R), "verdict": Counter(r["verdict"] for r in R),
        "llm_verdict": Counter(r["llm_verdict"] for r in R),
        "mcp": Counter(r["mcp"] for r in R),
        "composio": sum(bool(r["composio"]["slug"]) for r in R),
        "by_group": {g: dict(c) for g, c in by_group.items()},
        "checks": checks, "changed_apps": sum(bool(r["changed"]) for r in R),
        "changed_fields": Counter(k for r in R for k in r["changed"]),
        "blockers": [(r["app"], r["access"], r["blocker"]) for r in R if r["verdict"] == "blocked"],
        "ready_no_composio": [r["app"] for r in R if r["verdict"] != "blocked" and not r["composio"]["slug"]],
        "gated_in_composio": [r["app"] for r in R if r["access"] in GATED and r["composio"]["slug"]],
    }


e = html.escape
REPO = "https://github.com/Dhruthik0/toolkit-readiness-research"


def clip(t, n=140):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def wilson(k, n, z=1.96):
    """95% Wilson score interval, in percent."""
    from math import sqrt
    p, d = k / n, 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h)), round(100 * (c + h))


def link(u, text):
    return f'<a href="{e(u)}" target="_blank" rel="noopener">{e(text)}</a>' if u and u.startswith("http") else e(text)


def page(R, S, SC):
    T = answer_key()
    n = S["n"]
    FR = score(adjudicated=False)  # headline numbers use the untouched frozen key
    p1, ver, fin = FR["pass1"], FR["verified"], FR["final"]
    groups = list(dict.fromkeys(r["group"] for r in R))

    # --- category x access matrix
    mx = max(c for g in S["by_group"].values() for c in g.values())
    head = "".join(f"<th>{ACCESS_LABEL[a]}</th>" for a in ACCESS)
    rows = ""
    for g in groups:
        cells = ""
        for a in ACCESS:
            c = S["by_group"][g].get(a, 0)
            lvl = 0 if not c else 1 + round(4 * c / mx)
            apps = ", ".join(r["app"] for r in R if r["group"] == g and r["access"] == a)
            cells += f'<td class="h{lvl}" title="{e(g)} / {ACCESS_LABEL[a]}: {e(apps) or "none"}">{c or ""}</td>'
        rows += f"<tr><th>{e(g)}</th>{cells}</tr>"
    matrix = f'<table class="matrix"><thead><tr><th></th>{head}</tr></thead><tbody>{rows}</tbody></table>'

    # --- verdict by category stacked bars
    vbars = ""
    for g in groups:
        c = Counter(r["verdict"] for r in R if r["group"] == g)
        segs = "".join(
            f'<span class="seg {v}" style="flex:{c[v]}" title="{VERDICT_LABEL[v]}: '
            f'{e(", ".join(r["app"] for r in R if r["group"] == g and r["verdict"] == v))}">{c[v]}</span>'
            for v in VERDICT_LABEL if c[v])
        vbars += f'<div class="vrow"><span class="vlab">{e(g)}</span><span class="vbar">{segs}</span></div>'

    # --- auth bars (share of apps offering each)
    auth_counts = Counter(m for r in R for m in r["auth_methods"])
    abars = "".join(
        f'<div class="arow"><span class="vlab">{e(m)}</span><span class="atrack"><span class="afill" style="width:{100 * c / n}%"></span></span><span class="aval">{c}</span></div>'
        for m, c in auth_counts.most_common() if m != "None")

    # --- accuracy table
    def acc_row(name, s, note):
        cells = "".join(f"<td>{s['per_field'][f]}/{len(T)}</td>" for f in FIELDS)
        return f"<tr><th>{name}</th>{cells}<td><b>{s['pct']}%</b></td><td class='muted'>{note}</td></tr>"
    acc = (f'<table class="acc"><thead><tr><th>Stage</th>{"".join(f"<th>{f}</th>" for f in FIELDS)}<th>Overall</th><th></th></tr></thead><tbody>'
           + acc_row("1. Research agent", p1, "single pass, as generated")
           + acc_row("2. + Verifier agent", ver, "independent re-fetch of every cited page, corrections applied")
           + acc_row("3. + Recheck + rule verdict", fin, "recheck agent on flagged apps; verdict computed from verified fields")
           + "</tbody></table>")

    # --- per-app sample results (final stage), misses first
    srows = ""
    p1rows = {r["id"]: r for r in p1["rows"]}
    for row in sorted(fin["rows"], key=lambda r: sum(r["fields"].values())):
        t = T[row["id"]]
        marks = "".join(
            f'<td class="{"ok" if row["fields"][f] else "bad"}">'
            f'{"✓" if row["fields"][f] else "✗"}{"" if p1rows[row["id"]]["fields"][f] == row["fields"][f] else (" ↑" if row["fields"][f] else " ↓")}</td>'
            for f in FIELDS)
        srows += f'<tr><th>{e(row["app"])}</th>{marks}<td class="note">{e(t["notes"])}</td></tr>'
    sample = (f'<table class="sample"><thead><tr><th>App</th>{"".join(f"<th>{f}</th>" for f in FIELDS)}'
              f'<th>Answer key note</th></tr></thead><tbody>{srows}</tbody></table>')

    # --- main table
    trs = ""
    for r in R:
        comp = r["composio"]
        comp_cell = (f'<span class="pill yes" title="{e(comp["note"] or "")}">{e(comp["slug"])}{"*" if comp["note"] else ""}</span>'
                     if comp["slug"] else '<span class="pill no">none</span>')
        ev = " · ".join(link(u, k) for k, u in r["evidence"].items() if u)
        chk = Counter(c["status"] for c in r["checks"])
        flags = []
        if r["changed"]:
            flags.append(f'<span class="pill fix" title="Fields the verifier changed">fixed: {", ".join(r["changed"])}</span>')
        if chk["unsupported"]:
            flags.append(f'<span class="pill warn">{chk["unsupported"]} unsupported</span>')
        if r["confidence"] == "low":
            flags.append('<span class="pill warn">low confidence</span>')
        detail = (f'<p><b>Auth:</b> {e(r["auth_notes"])}</p><p><b>Access:</b> {e(r["access_notes"])}</p>'
                  f'<p><b>Blocker / caveat:</b> {e(r["blocker"])}</p>'
                  + (f'<p><b>MCP:</b> {link(r["mcp_url"], r["mcp_url"])}</p>' if r["mcp_url"] else "")
                  + "<p><b>Verifier:</b> " + "; ".join(f'{e(c["field"])} = {e(c["status"])}' + (f' ({e(c["note"])})' if c["status"] != "supported" else "") for c in r["checks"]) + "</p>"
                  + f'<p><b>Evidence:</b> {ev or "none"}</p>')
        trs += (f'<tr class="main" data-group="{e(r["group"])}" data-access="{r["access"]}" data-verdict="{r["verdict"]}" '
                f'data-text="{e((r["app"] + " " + r["one_liner"]).lower())}">'
                f'<td>{r["id"]}</td><td><b>{e(r["app"])}</b><div class="muted small">{e(r["one_liner"])}</div></td>'
                f'<td>{e(", ".join(r["auth_methods"]))}</td><td><span class="acc-{r["access"]}">{ACCESS_LABEL[r["access"]]}</span></td>'
                f'<td>{e(", ".join(r["api_types"]) or "none")} <span class="muted small">{r["api_breadth"]}</span></td>'
                f'<td>{e(r["mcp"].replace("_", " "))}</td><td>{comp_cell}</td>'
                f'<td><span class="v {r["verdict"]}">{VERDICT_LABEL[r["verdict"]]}</span></td>'
                f'<td class="small">{e(clip(r["blocker"]))}<div>{"".join(flags)}</div></td></tr>'
                f'<tr class="detail" hidden><td></td><td colspan="8">{detail}</td></tr>')
    opts = lambda vals, lab: "".join(f'<option value="{e(v)}">{e(lab(v))}</option>' for v in vals)

    data_json = json.dumps(R).replace("</", "<\\/")
    A, V = S["access"], S["verdict"]
    lo, hi = wilson(fin["hits"], fin["total"])
    ul = lambda items: "".join(f"<li>{x}</li>" for x in items)
    short = lambda t: e(t.split(". ")[0].rstrip(".")) + "."
    adj = json.loads((ROOT / "truth/adjudications.json").read_text())
    vals = dict(
        n=n, matrix=matrix, vbars=vbars, abars=abars, acc=acc, sample=sample, rows=trs,
        group_opts=opts(groups, str), access_opts=opts(ACCESS, ACCESS_LABEL.get),
        verdict_opts=opts(VERDICT_LABEL, VERDICT_LABEL.get), data_json=data_json,
        free=A["self_serve_free"], trial=A["self_serve_trial"], paid=A["paid_plan"],
        approval=A["approval_required"], partner=A["partner_gated"], noapi=A["no_public_api"],
        ready=V["ready"], caveats=V["ready_with_caveats"], blocked=V["blocked"],
        oauth=S["oauth"], static=S["static"], both=S["both"], oauth_only=S["oauth_only"], static_only=S["static_only"],
        mcp_official=S["mcp"]["official"], composio=S["composio"], llm_caveats=S["llm_verdict"]["ready_with_caveats"],
        changed_apps=S["changed_apps"], supported=S["checks"]["supported"], unsupported=S["checks"]["unsupported"],
        contradicted=S["checks"]["contradicted"], nchecks=sum(S["checks"].values()),
        p1=p1["pct"], ver=ver["pct"], fin=fin["pct"], ap1=SC["pass1"]["pct"], aver=SC["verified"]["pct"], afin=SC["final"]["pct"],
        ci_lo=lo, ci_hi=hi, repo=REPO,
        rest=sum(bool({"REST", "GraphQL"} & set(r["api_types"])) for r in R),
        missing=sum(not r["composio"]["slug"] for r in R),
        missing_buildable=sum(r["verdict"] != "blocked" and not r["composio"]["slug"] for r in R),
        partner_list=", ".join(e(r["app"]) for r in R if r["access"] == "partner_gated"),
        nsample=len(T), nfield=len(T) * len(FIELDS),
        easy_wins=ul(f'<b>{e(r["app"])}</b> <span class="muted">({ACCESS_LABEL[r["access"]]})</span>' for r in R if r["verdict"] != "blocked" and not r["composio"]["slug"]),
        outreach=ul(f'<b>{e(r["app"])}</b>: {short(r["blocker"])}' for r in R if r["verdict"] == "blocked"),
        approval_list=", ".join(e(r["app"]) for r in R if r["access"] == "approval_required"),
        oauth_only_list=", ".join(e(r["app"]) for r in R if "OAuth2" in r["auth_methods"] and not STATIC & set(r["auth_methods"])),
        adjudications=ul(f'<b>{e(T[i]["app"])}</b>: {e(a["why"])}' for i, a in adj.items()),
        recheck_list=", ".join(e(r["app"]) for r in R if r.get("recheck")),
        support_paid=S["by_group"]["Support and Helpdesk"].get("paid_plan", 0) + S["by_group"]["Support and Helpdesk"].get("self_serve_trial", 0),
        prod_free=S["by_group"]["Productivity and Project Management"].get("self_serve_free", 0),
        dev_free=S["by_group"]["Developer, Infra and Data platforms"].get("self_serve_free", 0),
        mkt_approval=S["by_group"]["Marketing, Ads, Email and Social"].get("approval_required", 0),
    )
    out = (ROOT / "page_template.html").read_text()
    for k, v in vals.items():
        out = out.replace("%%" + k + "%%", str(v))
    left = re.findall(r"%%\w+%%", out)
    assert not left, f"unfilled placeholders: {left}"
    return out


if __name__ == "__main__":
    R = records()
    S = stats(R)
    if "--stats" in sys.argv:
        print(json.dumps(S, indent=1, default=dict))
        sys.exit()
    SC = score()
    (ROOT / "out/scores.json").write_text(json.dumps({"adjudicated": SC, "frozen": score(adjudicated=False)}, indent=2))
    (ROOT / "data.json").write_text(json.dumps(R, indent=1))
    (ROOT / "index.html").write_text(page(R, S, SC))
    print("wrote index.html, data.json")
