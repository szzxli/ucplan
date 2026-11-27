#!/usr/bin/env python3
"""Unit tests for the ASSIST grouping/notes rendering in gen_transfer_pages.py.

Run: python3 scripts/test_gen_transfer_pages.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_transfer_pages as g


def course(prefix, number, notes=()):
    return {
        "prefix": prefix,
        "courseNumber": number,
        "courseTitle": f"{prefix} {number} title",
        "maxUnits": 4.0,
        "attributes": [{"position": i, "content": n} for i, n in enumerate(notes)],
    }


def group(position, conjunction, courses, notes=()):
    return {
        "position": position,
        "courseConjunction": conjunction,
        "items": courses,
        "attributes": [{"position": i, "content": n} for i, n in enumerate(notes)],
    }


def conj(begin, end, op):
    return {
        "sendingCourseGroupBeginPosition": begin,
        "sendingCourseGroupEndPosition": end,
        "groupConjunction": op,
    }


class ExpressionTest(unittest.TestCase):
    def test_single_course(self):
        self.assertEqual(g.render_expression([group(0, "And", [course("CIS", "22C")])], []), "CIS 22C")

    def test_and_group(self):
        groups = [group(0, "And", [course("MATH", "1B"), course("MATH", "1A")])]
        self.assertEqual(g.render_expression(groups, []), "MATH 1B + MATH 1A")

    def test_or_alternatives(self):
        groups = [
            group(0, "And", [course("CIS", "22CH")]),
            group(1, "And", [course("CIS", "26B")]),
            group(2, "And", [course("CIS", "22C")]),
        ]
        conjs = [conj(0, 1, "Or"), conj(1, 2, "Or")]
        self.assertEqual(g.render_expression(groups, conjs), "CIS 22CH or CIS 26B or CIS 22C")

    def test_nested_and_groups_joined_by_or(self):
        groups = [
            group(0, "And", [course("MATH", "1B"), course("MATH", "1A")]),
            group(1, "And", [course("MATH", "1AH"), course("MATH", "1BH")]),
        ]
        self.assertEqual(
            g.render_expression(groups, [conj(0, 1, "Or")]),
            "(MATH 1B + MATH 1A) or (MATH 1AH + MATH 1BH)",
        )

    def test_nested_or_groups_joined_by_and(self):
        groups = [
            group(0, "Or", [course("MATH", "1A"), course("MATH", "1AH")]),
            group(1, "Or", [course("MATH", "1B"), course("MATH", "1BH")]),
        ]
        self.assertEqual(
            g.render_expression(groups, [conj(0, 1, "And")]),
            "(MATH 1A or MATH 1AH) + (MATH 1B or MATH 1BH)",
        )

    def test_missing_conjunction_defaults_to_or(self):
        sa = {
            "items": [group(0, "And", [course("A", "1")]), group(1, "And", [course("B", "2")])],
            "courseGroupConjunctions": [],
        }
        self.assertEqual(g.render_sending(sa), "A 1 or B 2")


class SendingTest(unittest.TestCase):
    def test_advisement_prefixes_following_group(self):
        sa = {
            "items": [
                group(0, "Or", [course("MATH", "1A"), course("MATH", "1AH")]),
                {"type": "Advisement", "position": 1, "advisement": {"type": "NFollowing", "amount": 1.0, "amountUnitType": "Course", "selectionType": "Complete"}},
                group(2, "Or", [course("MATH", "1C"), course("MATH", "1CH")]),
            ],
            "courseGroupConjunctions": [conj(0, 2, "And")],
        }
        self.assertEqual(
            g.render_sending(sa),
            "(MATH 1A or MATH 1AH) + Complete 1 course from the following: (MATH 1C or MATH 1CH)",
        )

    def test_requirement_label(self):
        b = {"articulation": {"type": "Requirement", "requirement": {"name": "Mathematics Requirement"}, "sendingArticulation": {}}}
        self.assertEqual(g.uc_label(b), ("Mathematics Requirement", ""))

    def test_series_label(self):
        b = {"articulation": {"type": "Series", "series": {"conjunction": "And", "courses": [course("MCELLBI", "32"), course("MCELLBI", "32L")]}, "sendingArticulation": {}}}
        label, _detail = g.uc_label(b)
        self.assertEqual(label, "MCELLBI 32 + MCELLBI 32L")


class NotesTest(unittest.TestCase):
    def block(self, groups, receiving=()):
        return {
            "articulation": {
                "course": course("COMPSCI", "61B"),
                "sendingArticulation": {"items": groups, "courseGroupConjunctions": []},
            },
            "receivingAttributes": {"attributes": [{"content": n} for n in receiving], "courseAttributes": []},
        }

    def test_identical_notes_merge(self):
        note = "Must complete an additional university course after transfer to satisfy this requirement"
        b = self.block([group(0, "And", [course("CIS", "26B", [note])]), group(1, "And", [course("CIS", "22C", [note])])])
        self.assertEqual(g.collect_notes(b), [(note, ["CIS 26B", "CIS 22C"])])
        self.assertEqual(g.render_notes(b, ["CIS 26B", "CIS 22C"]), note)

    def test_partial_note_keeps_course_prefix(self):
        note = "Regular and honors courses may be combined to complete this series"
        b = self.block([group(0, "And", [course("MATH", "1B", [note]), course("MATH", "1A")])])
        self.assertEqual(g.render_notes(b, ["MATH 1B", "MATH 1A"]), f"MATH 1B: {note}")

    def test_group_and_receiving_notes(self):
        b = self.block([group(0, "And", [course("A", "1")], notes=["Group note"])], receiving=["Receiving note"])
        self.assertEqual(g.collect_notes(b), [("Group note", []), ("Receiving note", [])])


class RowTest(unittest.TestCase):
    def test_no_articulation_row(self):
        b = {
            "articulation": {
                "course": course("COMPSCI", "70"),
                "sendingArticulation": {
                    "items": [],
                    "deniedCourses": [],
                    "noArticulationReason": "This course must be taken at the university after transfer",
                },
            },
            "receivingAttributes": {},
        }
        uc, cc, notes, articulated = g.requirement_row(b)
        self.assertFalse(articulated)
        self.assertEqual(cc, "No course articulated")
        self.assertEqual(notes, "This course must be taken at the university after transfer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
