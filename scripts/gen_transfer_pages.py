#!/usr/bin/env python3
"""Regenerate the /transfer/ articulation pages from ASSIST agreement data.

Each page under transfer/<college>/<uc>/<major>.html keeps its URL, head,
header, footer, and GoatCounter loader; only the articulation table, the
"How to read this table" bullets, and the agreement published date are
rewritten, from the ASSIST JSON API (the public source the project already
pulls; see transfer-os scrapers/ASSIST_NOTES.md).

Rendering (agent-hq #147): one row per UC requirement; CC courses that must
all be taken joined by "+", alternatives by "or", parentheses where groups
nest; ASSIST notes kept word for word; no-articulation requirements say so
with the ASSIST reason quoted.

Usage: python3 scripts/gen_transfer_pages.py [--cache-dir DIR] [--delay S]
Agreement JSON is cached (default /tmp/ucplan-assist-cache); requests are
spaced by --delay seconds (default 2) with an identifying User-Agent. The
script fails loudly on any page it cannot match or render.
"""
import argparse
import html
import http.cookiejar
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://www.assist.org"
YEARS = {"2026-2027": 77, "2025-2026": 76}
UC_NAMES = ["UC Berkeley", "UC Davis", "UC Irvine", "UC San Diego", "UC Santa Cruz", "UCLA"]
UC_VARIANTS = {
    "UC Berkeley": ["university of california berkeley"],
    "UC Davis": ["university of california davis"],
    "UC Irvine": ["university of california irvine"],
    "UC San Diego": ["university of california san diego"],
    "UC Santa Cruz": ["university of california santa cruz"],
    "UCLA": ["university of california los angeles", "ucla"],
}


def esc(s):
    return html.escape(str(s), quote=True)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def course_code(course):
    return f"{(course.get('prefix') or '').strip()} {(course.get('courseNumber') or '').strip()}".strip()


def course_units(course):
    u = course.get("maxUnits")
    if u in (None, ""):
        return ""
    return str(u)


# --------------------------------------------------------------------------
# Grouping / notes rendering (unit-tested in test_gen_transfer_pages.py)
# --------------------------------------------------------------------------

def _group_ops(groups, conjunctions):
    """Operator between consecutive groups, from ASSIST group conjunctions."""
    ops = []
    by_pair = {}
    for c in conjunctions or []:
        by_pair[(c.get("sendingCourseGroupBeginPosition"), c.get("sendingCourseGroupEndPosition"))] = c.get("groupConjunction")
    for prev, cur in zip(groups, groups[1:]):
        op = by_pair.get((prev.get("position"), cur.get("position")), "Or")
        if op not in ("And", "Or"):
            raise ValueError(f"invalid group conjunction between positions {prev.get('position')} and {cur.get('position')}")
        ops.append(op)
    return ops


def advisement_text(advisement):
    """ASSIST advisement (e.g. NFollowing/Complete/1/Course) as plain text."""
    amount = advisement.get("amount")
    unit = (advisement.get("amountUnitType") or "Course").lower()
    if amount is not None and float(amount) != 1 and not unit.endswith("s"):
        unit += "s"
    amount_text = ("%g" % float(amount)) if amount is not None else ""
    selection = advisement.get("selectionType") or "Complete"
    return f"{selection} {amount_text} {unit} from the following".strip()


def render_sending(sa):
    """Render the sending side: course groups plus any advisements, in
    ASSIST position order. Groups join by their group conjunctions; an
    advisement (e.g. "Complete 1 course from the following") prefixes the
    group that follows it."""
    items = sorted(sa.get("items") or [], key=lambda i: i.get("position", 0))
    groups = [i for i in items if i.get("type") != "Advisement"]
    if not groups:
        return ""
    ops = {}
    for c in sa.get("courseGroupConjunctions") or []:
        ops[(c.get("sendingCourseGroupBeginPosition"), c.get("sendingCourseGroupEndPosition"))] = c.get("groupConjunction")
    group_positions = [g.get("position", 0) for g in groups]
    for prev, cur in zip(group_positions, group_positions[1:]):
        # ASSIST lists sending groups as alternatives unless a group
        # conjunction says otherwise; a missing entry means Or.
        if ops.get((prev, cur), "Or") not in ("And", "Or"):
            raise ValueError(f"invalid group conjunction between positions {prev} and {cur}")
    multi = len(groups) > 1
    out = ""
    prev_group_pos = None
    pending_advisement = ""
    for item in items:
        if item.get("type") == "Advisement":
            pending_advisement = advisement_text(item.get("advisement") or {})
            continue
        codes = [course_code(c) for c in sorted(item.get("items") or [], key=lambda c: c.get("position", 0))]
        if not codes:
            raise ValueError("empty sending course group")
        joiner = " + " if item.get("courseConjunction", "And") == "And" else " or "
        text = joiner.join(codes)
        if multi and len(codes) > 1:
            text = f"({text})"
        if pending_advisement:
            text = f"{pending_advisement}: {text}"
            pending_advisement = ""
        if prev_group_pos is None:
            out = text
        else:
            op = ops.get((prev_group_pos, item.get("position", 0)), "Or")
            out += (" + " if op == "And" else " or ") + text
        prev_group_pos = item.get("position", 0)
    if pending_advisement:
        out += f" + {pending_advisement}"
    return out


def render_expression(groups, conjunctions):
    """Render sending groups as e.g. "(MATH 1B + MATH 1A) or (MATH 1AH + MATH 1BH)".

    Groups are joined by their ASSIST group conjunctions; courses inside a
    group by the group's courseConjunction. A multi-course group is
    parenthesized whenever more than one group is combined, so the grouping
    stays unambiguous.
    """
    groups = sorted(groups, key=lambda g: g.get("position", 0))
    if not groups:
        return ""
    ops = _group_ops(groups, conjunctions)
    parts = []
    for g in groups:
        items = sorted(g.get("items") or [], key=lambda c: c.get("position", 0))
        codes = [course_code(c) for c in items]
        if not codes:
            raise ValueError("empty sending course group")
        joiner = " + " if g.get("courseConjunction", "And") == "And" else " or "
        text = joiner.join(codes)
        if len(groups) > 1 and len(codes) > 1:
            text = f"({text})"
        parts.append(text)
    out = parts[0]
    for op, part in zip(ops, parts[1:]):
        out += (" + " if op == "And" else " or ") + part
    return out


def collect_notes(block):
    """ASSIST notes for one requirement, verbatim.

    Returns a list of (text, codes) where codes is the list of sending
    course codes the note is attached to (empty = applies to the whole row).
    Identical texts are merged, keeping every course they were attached to.
    """
    art = block.get("articulation", {}) or {}
    sa = art.get("sendingArticulation", {}) or {}
    merged = {}

    def add(text, code=None):
        text = (text or "").strip()
        if not text:
            return
        codes = merged.setdefault(text, [])
        if code and code not in codes:
            codes.append(code)

    for g in sa.get("items") or []:
        for a in g.get("attributes") or []:
            add(a.get("content"))
        for c in g.get("items") or []:
            for a in c.get("attributes") or []:
                add(a.get("content"), course_code(c))
    for a in sa.get("attributes") or []:
        add(a.get("content") if isinstance(a, dict) else None)
    for key in ("attributes", "seriesAttributes", "courseAttributes", "requirementAttributes"):
        for a in art.get(key) or []:
            add(a.get("content") if isinstance(a, dict) else None)
    ra = block.get("receivingAttributes") or {}
    for key in ("attributes", "courseAttributes", "seriesAttributes", "seriesCourseAttributes"):
        for a in ra.get(key) or []:
            if isinstance(a, dict):
                add(a.get("content"))
    return [(text, codes) for text, codes in merged.items()]


def render_notes(block, all_codes):
    lines = []
    for text, codes in collect_notes(block):
        if codes and set(codes) != set(all_codes):
            lines.append(f"{esc(', '.join(codes))}: {esc(text)}")
        else:
            lines.append(esc(text))
    return "<br>".join(lines)


def uc_label(block):
    """(code label, title detail) for a Course or Series receiving side."""
    art = block.get("articulation", {}) or {}
    rc = art.get("course") or {}
    code = course_code(rc)
    if code:
        return code, (rc.get("courseTitle") or "").strip()
    series = art.get("series") or {}
    courses = sorted(series.get("courses") or [], key=lambda c: c.get("position", 0))
    if courses:
        joiner = " + " if series.get("conjunction", "And") == "And" else " or "
        label = joiner.join(course_code(c) for c in courses)
        detail = "; ".join((c.get("courseTitle") or "").strip() for c in courses)
        return label, detail
    requirement = art.get("requirement") or {}
    if requirement.get("name"):
        return requirement["name"].strip(), ""
    raise ValueError(f"receiving side without course, series, or requirement: {json.dumps(art)[:200]}")


def requirement_row(block):
    """One table row's cells: (uc_html, cc_html, notes_html, articulated)."""
    art = block.get("articulation", {}) or {}
    sa = art.get("sendingArticulation", {}) or {}
    uc_code, uc_title = uc_label(block)
    uc_html = f"<strong>{esc(uc_code)}</strong>"
    if uc_title:
        uc_html += f"<br>{esc(uc_title)}"
    groups = [i for i in (sa.get("items") or []) if i.get("type") != "Advisement"]
    denied = sa.get("deniedCourses") or []
    noart = sa.get("noArticulationReason")
    if not groups:
        parts = []
        if noart and noart.strip().lower() != "no course articulated":
            parts.append(esc(noart))
        attr_notes = render_notes(block, [])
        if attr_notes:
            parts.append(attr_notes)
        if denied:
            codes = ", ".join(course_code(d) for d in denied if isinstance(d, dict))
            parts.append(f"Course(s) denied: {esc(codes)}")
        return uc_html, "No course articulated", "<br>".join(parts), False
    expr = render_sending(sa)
    seen = []
    for g in sorted(groups, key=lambda g: g.get("position", 0)):
        for c in sorted(g.get("items") or [], key=lambda c: c.get("position", 0)):
            code = course_code(c)
            if code not in [s[0] for s in seen]:
                seen.append((code, (c.get("courseTitle") or "").strip(), course_units(c)))
    detail = "<br>".join(
        f"<strong>{esc(code)}</strong> {esc(title)}" + (f" ({esc(units)} units)" if units else "")
        for code, title, units in seen
    )
    cc_html = f"<strong>{esc(expr)}</strong>"
    if detail:
        cc_html += f"<br>{detail}"
    notes = render_notes(block, [s[0] for s in seen])
    if denied:
        codes = ", ".join(course_code(d) for d in denied if isinstance(d, dict))
        notes = (notes + "<br>" if notes else "") + f"Course(s) denied: {esc(codes)}"
    return uc_html, cc_html, notes, True


# --------------------------------------------------------------------------
# ASSIST fetching (cached, polite)
# --------------------------------------------------------------------------

class Assist:
    def __init__(self, cache_dir, delay):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        cj = http.cookiejar.CookieJar()
        ctx = ssl._create_unverified_context()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx),
            urllib.request.HTTPCookieProcessor(cj),
        )
        self.op.addheaders = [
            ("User-Agent", "ucplan/1.0 (+https://ucplan.org; transfer planning reference)"),
            ("Accept", "application/json"),
            ("Referer", BASE + "/"),
        ]
        self.op.open(BASE + "/", timeout=30).read()
        token = next((c.value for c in cj if c.name == "X-XSRF-TOKEN"), None)
        if not token:
            raise RuntimeError("X-XSRF-TOKEN cookie not set by ASSIST homepage")
        self.op.addheaders.append(("X-XSRF-TOKEN", token))
        self._lists = {}

    def get_json(self, url, cache_name):
        f = self.cache / cache_name
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        time.sleep(self.delay)
        with self.op.open(url, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        f.write_text(json.dumps(data), encoding="utf-8")
        return data

    def institution_id(self, name):
        data = self.get_json(BASE + "/api/institutions", "institutions.json")
        by_name = {}
        for i in data:
            for n in i.get("names") or []:
                if n.get("name"):
                    by_name[norm(n["name"])] = i["id"]
        if norm(name) in by_name:
            return by_name[norm(name)]
        for v in UC_VARIANTS.get(name, []):
            if v in by_name:
                return by_name[v]
        raise RuntimeError(f"institution not found: {name}")

    def agreement(self, cc, uc, major, year, cache_name=None):
        cc_id, uc_id, yid = self.institution_id(cc), self.institution_id(uc), YEARS[year]
        lkey = (cc_id, uc_id, yid)
        if lkey not in self._lists:
            self._lists[lkey] = self.get_json(
                f"{BASE}/api/agreements?receivingInstitutionId={uc_id}&sendingInstitutionId={cc_id}&academicYearId={yid}&categoryCode=major",
                f"agreements_{cc_id}_{uc_id}_{yid}.json",
            )
        reports = self._lists[lkey].get("reports") or []
        match = next((r for r in reports if norm(r.get("label") or r.get("name", "")) == norm(major)), None)
        if not match:
            raise RuntimeError(f"no ASSIST agreement for {cc} -> {uc} {major} {year}")
        if not cache_name:
            cache_name = "agreement_" + re.sub(r"[^A-Za-z0-9]+", "_", f"{cc}_{uc}_{major}_{year}") + ".json"
        data = self.get_json(
            f"{BASE}/api/articulation/Agreements?Key={urllib.parse.quote(match['key'], safe='')}",
            cache_name,
        )
        if not data.get("isSuccessful"):
            raise RuntimeError(f"ASSIST agreement fetch failed for {cc} -> {uc} {major}")
        return data


# --------------------------------------------------------------------------
# Page rewriting
# --------------------------------------------------------------------------

def page_meta(path):
    t = path.read_text(encoding="utf-8")
    m = re.search(r"Course articulations from (.+?) to (.+?), ASSIST agreement (\d{4}-\d{4}), published (\d{4}-\d{2}-\d{2})", t)
    if not m:
        raise RuntimeError(f"cannot parse page meta: {path}")
    cc, uc_major, year, _published = m.groups()
    uc = next(u for u in UC_NAMES if uc_major.startswith(u + " "))
    return {"cc": cc, "uc": uc, "major": uc_major[len(uc) + 1:], "year": year}


def render_page(path, data):
    meta = page_meta(path)
    result = data.get("result", {}) or {}
    published = (result.get("publishDate") or "")[:10]
    if not published:
        raise RuntimeError(f"no publishDate for {path}")
    arts = result.get("articulations", [])
    if isinstance(arts, str):
        arts = json.loads(arts)
    rows = []
    noart_codes = []
    for block in arts:
        uc_html, cc_html, notes_html, articulated = requirement_row(block)
        rows.append((uc_html, cc_html, notes_html))
        if not articulated:
            noart_codes.append(uc_label(block)[0])
    n_art = len(rows) - len(noart_codes)
    counts = f"<p>{n_art} of {len(rows)} {esc(meta['uc'])} course requirements in this agreement have articulated {esc(meta['cc'])} courses.</p>"
    if noart_codes:
        counts += f"\n    <p>{len(noart_codes)} {esc(meta['uc'])} course requirement(s) have no articulated {esc(meta['cc'])} course ({esc(', '.join(noart_codes))}).</p>"
    trs = "\n".join(f"    <tr><td>{uc}</td><td>{cc}</td><td>{notes}</td></tr>" for uc, cc, notes in rows)
    table = (
        counts + "\n"
        '    <table class="data">\n'
        f"      <thead><tr><th>{esc(meta['uc'])} course</th><th>{esc(meta['cc'])} courses</th><th>ASSIST notes</th></tr></thead>\n"
        "      <tbody>\n" + trs + "\n      </tbody>\n    </table>"
    )
    bullets = (
        "    <ul>\n"
        f"      <li>Each row is one {esc(meta['uc'])} course requirement. {esc(meta['cc'])} courses joined by + must all be taken; courses joined by or are alternatives. Parentheses group courses that belong together.</li>\n"
        "      <li>Notes are quoted from the ASSIST agreement. A note can change what a course satisfies — read it before you plan around the row.</li>\n"
        "      <li>This page is a planning reference, not an admission decision.</li>\n"
        "    </ul>"
    )
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"published \d{4}-\d{2}-\d{2}", f"published {published}", text)
    text, n1 = re.subn(
        r"(<h2>Course articulations</h2>).*?(</section>)",
        lambda m: m.group(1) + "\n    " + table + "\n  " + m.group(2),
        text, count=1, flags=re.S,
    )
    text, n2 = re.subn(
        r"(<h2>How to read this table</h2>)\s*<ul>.*?</ul>",
        lambda m: m.group(1) + "\n" + bullets,
        text, count=1, flags=re.S,
    )
    if n1 != 1 or n2 != 1:
        raise RuntimeError(f"section rewrite failed for {path} ({n1}, {n2})")
    if "taking it once " + "covers" in text:
        raise RuntimeError(f"misleading phrase remains in {path}")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", default="/tmp/ucplan-assist-cache")
    ap.add_argument("--delay", type=float, default=2.0)
    a = ap.parse_args()
    assist = Assist(a.cache_dir, a.delay)
    pages = sorted(ROOT.glob("transfer/*/*/*.html"))
    changed = 0
    for p in pages:
        meta = page_meta(p)
        cache_name = str(p.relative_to(ROOT)).replace("/", "__") + ".json"
        data = assist.agreement(meta["cc"], meta["uc"], meta["major"], meta["year"], cache_name)
        new = render_page(p, data)
        if new != p.read_text(encoding="utf-8"):
            p.write_text(new, encoding="utf-8")
            changed += 1
        print(f"ok {p.relative_to(ROOT)}", file=sys.stderr)
    print(f"{len(pages)} pages regenerated, {changed} changed")


if __name__ == "__main__":
    main()
