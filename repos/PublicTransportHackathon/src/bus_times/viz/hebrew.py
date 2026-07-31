"""Making Hebrew labels readable in matplotlib.

There is exactly one thing to do and one thing **not** to do.

**Do** pick a font that carries Hebrew. Matplotlib's default, DejaVu Sans, has no Hebrew coverage, so
every letter comes out as an empty box.

**Do not** reorder the text. Matplotlib >= 3.11 lays text out through HarfBuzz and applies the full
Unicode Bidirectional Algorithm itself: Hebrew runs are placed right-to-left, embedded digits stay
left-to-right (``15`` does not become ``51``), and mirrored punctuation such as brackets is flipped to
face the right way. Passing it a string that has already been reordered — by ``python-bidi``'s
``get_display`` or anything else — reverses it a second time, and every label renders backwards, the
Hebrew equivalent of ``eman`` for ``name``.

Labels are therefore built in plain **logical** order, exactly as a person types them, and handed to
matplotlib untouched. Because it runs the real bidi algorithm rather than a reversal, brackets, commas
and arrows can all be used freely.

If this package is ever run against matplotlib < 3.11, which had no bidi support, Hebrew will render
reversed and the reordering would need reinstating — hence the floor in ``pyproject.toml``.
"""

import functools
import unicodedata
import warnings

from matplotlib import font_manager

# Fonts that ship Hebrew coverage, best-looking first. Noto/Arial/Segoe cover Linux, macOS and
# Windows respectively, so at least one is normally present.
HEBREW_FONT_CANDIDATES = (
    'Noto Sans Hebrew',
    'Arial',
    'Segoe UI',
    'Tahoma',
    'David',
    'FreeSans',
    'DejaVu Sans',  # no Hebrew coverage; last resort so a chart still renders
)


@functools.cache
def resolve_hebrew_font(candidates: tuple[str, ...] = HEBREW_FONT_CANDIDATES) -> str:
    """Name of the first installed font that can render Hebrew.

    Warns and falls back to matplotlib's default if none of the candidates is installed — a chart
    with boxes for labels is more useful than a traceback, as long as the reason is stated.

    Cached: enumerating installed fonts is slow enough to notice when every chart re-does it, and it
    keeps the missing-font warning to one occurrence rather than one per figure.
    """
    installed = set(font_manager.get_font_names())
    for name in candidates:
        if name in installed:
            if name == 'DejaVu Sans':
                warnings.warn(
                    'No Hebrew-capable font found (tried: '
                    f'{", ".join(candidates[:-1])}). Hebrew labels will render as empty boxes. '
                    'Install "Noto Sans Hebrew" to fix.',
                    RuntimeWarning, stacklevel=2)
            return name

    warnings.warn('None of the candidate fonts are installed; using the matplotlib default.',
                  RuntimeWarning, stacklevel=2)
    return font_manager.FontProperties().get_name()


def has_hebrew(text: str) -> bool:
    """True if any character belongs to the Hebrew script."""
    return any(unicodedata.name(ch, '').startswith('HEBREW') for ch in text)


def shorten(name: str, max_chars: int = 22) -> str:
    """Trim a stop name, preferring to cut at a separator.

    Israeli stop names are often ``street/cross-street`` or ``landmark/street`` pairs and run past 40
    characters; two of them in one segment label overflow any sensible margin. The ellipsis is
    appended in logical order — matplotlib's bidi pass puts it on the correct visual side.
    """
    if len(name) <= max_chars:
        return name
    head = name[:max_chars]
    cut = max(head.rfind('/'), head.rfind(' '), head.rfind('\\'))
    if cut >= max_chars // 2:
        head = head[:cut]
    return head.rstrip() + '…'


def segment_label(from_name: str, to_name: str, arrow: str = ' ← ',
                  max_chars: int = 22) -> str:
    """Label for a stop-to-stop segment, in logical order.

    Written the way it is read: origin, arrow, destination. Rendered right-to-left, the origin lands on
    the right and the arrow points leftward towards the destination, following the reading direction.
    """
    return f'{shorten(from_name, max_chars)}{arrow}{shorten(to_name, max_chars)}'
