"""Tests for the Hebrew rendering helpers.

The central guarantee here is a *negative* one: label text must reach matplotlib in logical order,
never pre-reordered. Matplotlib >= 3.11 runs the Unicode Bidirectional Algorithm itself, so reversing
a string first makes it render backwards — the Hebrew equivalent of ``eman`` for ``name``.

An earlier version of this suite asserted the reversal, which is precisely how that bug shipped: the
tests described the implementation instead of the outcome. These assert the outcome.
"""

import matplotlib
import pytest
from packaging.version import Version

from bus_times.viz.hebrew import has_hebrew, resolve_hebrew_font, segment_label, shorten

STOP_A = 'ביטוח לאומי'
STOP_B = 'האומן/ברעם'


def test_matplotlib_is_new_enough_to_do_its_own_bidi():
    """The floor that makes passing logical order correct. Below it, Hebrew renders reversed."""
    assert Version(matplotlib.__version__) >= Version('3.11')


def test_segment_label_is_left_in_logical_order():
    label = segment_label(STOP_A, STOP_B)

    # Character-for-character as typed: origin, arrow, destination. No reversal anywhere.
    assert label == f'{STOP_A} ← {STOP_B}'
    assert label.startswith(STOP_A)
    assert label.endswith(STOP_B)


def test_no_helper_reverses_hebrew():
    """A regression guard: any reintroduced reordering step fails here."""
    assert shorten(STOP_A) == STOP_A
    assert STOP_A[::-1] not in segment_label(STOP_A, STOP_B)


def test_shorten_trims_long_names_at_a_separator():
    long_name = 'שדרות שז״ר/בנייני האומה והכנסת'

    short = shorten(long_name, max_chars=18)

    assert short.endswith('…')
    assert len(short) <= 19
    # Keeps as much as fits, cutting at the last separator inside the budget rather than mid-word.
    assert short == 'שדרות שז״ר/בנייני…'
    assert not short.startswith('…')  # the ellipsis goes on the end, in logical order


def test_shorten_leaves_short_names_alone():
    assert shorten(STOP_B, max_chars=40) == STOP_B
    assert '…' not in shorten(STOP_B, max_chars=40)


def test_segment_label_shortens_both_ends():
    long_a = 'תחנה ראשונה עם שם ארוך מאוד מאוד'
    long_b = 'תחנה שנייה עם שם ארוך מאוד מאוד'

    label = segment_label(long_a, long_b, max_chars=12)

    assert label.count('…') == 2


def test_has_hebrew_discriminates():
    assert has_hebrew(STOP_A)
    assert has_hebrew(f'Line 15 {STOP_A}')
    assert not has_hebrew('Line 15')


def test_resolved_font_is_actually_installed():
    name = resolve_hebrew_font()

    assert name in set(matplotlib.font_manager.get_font_names())


def test_resolve_hebrew_font_warns_when_nothing_matches():
    with pytest.warns(RuntimeWarning):
        resolve_hebrew_font(candidates=('No Such Font At All',))
