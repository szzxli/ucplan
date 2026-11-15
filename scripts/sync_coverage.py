"""Sync the coverage data into this site and regenerate the static lists on /coverage.

Inputs (never typed by hand):
  - Transfer-OS coverage.json   (generated from the shipped ASSIST data by transfer-os/mobile/scripts/build-coverage.py)
  - UC Course Planner majors/index.json  (the list the tool itself loads)

Outputs:
  - coverage.json       copy of the Transfer-OS file (the homepage lookup reads it)
  - ucc-majors.json     UC Course Planner campuses and majors (homepage + /uc-course read it)
  - index.html, coverage.html, uc-course.html, transfer-os.html:
      blocks between <!-- GEN:NAME --> ... <!-- /GEN:NAME --> are rewritten (YEARS, COLLEGES, MAJORS, UCC),
      and English text with {tokens} is re-rendered from lang/en.json so the static page shows the real numbers

Usage (defaults fetch the main branches from GitHub):
  python3 scripts/sync_coverage.py
  python3 scripts/sync_coverage.py --transfer-os ../transfer-os/mobile/www/coverage.json \
         --uc-course ../UC-Course/web/data/majors/index.json
Then bump CACHE in sw.js and the "Updated" date in index.html, and open a PR.
"""
import argparse
import datetime
import html
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/szzxli/"
DEFAULT_TOS = RAW + "transfer-os/main/mobile/www/coverage.json"
DEFAULT_UCC = RAW + "UC-Course/main/web/data/majors/index.json"
UCC_NAMES = {"UCI": "UC Irvine", "UCSD": "UC San Diego", "UCSB": "UC Santa Barbara"}


def read(src):
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=30) as r:
            return r.read().decode("utf-8")
    return Path(src).read_text(encoding="utf-8")


def esc(s):
    return html.escape(s, quote=True)


def fmt_year(y):
    return y.replace("-", "\u2013")


def build_ucc_data(index):
    out = []
    for cid in ("UCI", "UCSD", "UCSB"):
        majors = [{"name": m["major"], "degree": m["degree"]} for m in index if m["campus"] == cid]
        out.append({"id": cid, "name": UCC_NAMES[cid], "majors": majors})
    return {"count": sum(len(c["majors"]) for c in out), "campuses": out}


def years_cell(u, total):
    return "<br>".join("%s: %d / %d" % (fmt_year(y), n, total) for y, n in u["colleges_by_year"].items())


def build_years(cov):
    total = len(cov["colleges"])
    rows = ["<tr><td>%s</td><td>%s</td><td>%d</td></tr>" % (esc(u["name"]), years_cell(u, total), len(u["majors"])) for u in cov["ucs"]]
    return "\n".join(rows)


def build_colleges(cov):
    return "<ul class=\"cols\">\n" + "\n".join("<li>%s</li>" % esc(c) for c in cov["colleges"]) + "\n</ul>"


def build_majors(cov):
    total = len(cov["colleges"])
    parts = []
    for u in cov["ucs"]:
        parts.append("<h4>%s (%d)</h4>\n<p class=\"hint\">%s</p>\n<ul class=\"majs\">" % (esc(u["name"]), len(u["majors"]), esc(" \u00b7 ".join("%s: %d / %d" % (fmt_year(y), n, total) for y, n in u["colleges_by_year"].items()))))
        for m in u["majors"]:
            ys = ", ".join("%s (%d)" % (fmt_year(y), len(idx)) for y, idx in m["years"].items())
            parts.append("<li>%s <span class=\"hint\">%s</span></li>" % (esc(m["name"]), esc(ys)))
        parts.append("</ul>")
    return "\n".join(parts)


def build_ucc(ucc):
    parts = []
    for c in ucc["campuses"]:
        parts.append("<h4>%s (%d)</h4>\n<ul class=\"majs\">" % (esc(c["name"]), len(c["majors"])))
        parts += ["<li>%s <span class=\"hint\">%s</span></li>" % (esc(m["name"]), esc(m["degree"])) for m in c["majors"]]
        parts.append("</ul>")
    return "\n".join(parts)


def fill_blocks(text, blocks):
    for name, body in blocks.items():
        pat = re.compile(r"(<!-- GEN:%s -->).*?(<!-- /GEN:%s -->)" % (name, name), re.S)
        text = pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text)
    return text


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s %d, %d" % (d.strftime("%B"), d.day, d.year)


def render_tokens(text, en, vals):
    """Static English text for every data-i18n element whose English string has {tokens}, so the page is
    correct without JavaScript. i18n.js fills the same tokens from the same JSON for other languages."""
    def sub(m):
        key = m.group(3)
        v = en.get(key)
        if not isinstance(v, str) or not re.search(r"\{[a-z]+\}", v):
            return m.group(0)
        for k, val in vals.items():
            v = v.replace("{%s}" % k, str(val))
        if re.search(r"\{(colleges|ucs|majors|ucmajors|uccampuses|assistdate)\}", v):
            return m.group(0)
        return m.group(1) + html.escape(v, quote=False) + m.group(5)
    return re.sub(r'(<(\w+)\b[^>]*data-i18n="([^"]+)"[^>]*>)([^<]*)(</\2>)', sub, text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transfer-os", default=DEFAULT_TOS)
    ap.add_argument("--uc-course", default=DEFAULT_UCC)
    a = ap.parse_args()
    cov = json.loads(read(a.transfer_os))
    ucc = build_ucc_data(json.loads(read(a.uc_course)))
    (ROOT / "coverage.json").write_text(json.dumps(cov, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (ROOT / "ucc-majors.json").write_text(json.dumps(ucc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    en = json.loads((ROOT / "lang" / "en.json").read_text(encoding="utf-8"))
    vals = {"colleges": cov["counts"]["colleges"], "ucs": cov["counts"]["ucs"], "majors": cov["counts"]["uc_majors"],
            "ucmajors": ucc["count"], "uccampuses": len(ucc["campuses"]), "assistdate": nice_date(cov["assist_pulled"])}
    blocks = {"YEARS": build_years(cov), "COLLEGES": build_colleges(cov), "MAJORS": build_majors(cov), "UCC": build_ucc(ucc)}
    for name in ("index.html", "coverage.html", "uc-course.html", "transfer-os.html"):
        page = ROOT / name
        t = page.read_text(encoding="utf-8")
        t = fill_blocks(t, blocks)
        t = render_tokens(t, en, vals)
        if name == "index.html":
            today = datetime.date.today().isoformat()
            t = re.sub(r'<time datetime="[^"]*">[^<]*</time>', '<time datetime="%s">%s</time>' % (today, today), t)
        page.write_text(t, encoding="utf-8")
    print("colleges %d, UC majors %d, UC Course Planner majors %d" % (cov["counts"]["colleges"], cov["counts"]["uc_majors"], ucc["count"]))


if __name__ == "__main__":
    main()
