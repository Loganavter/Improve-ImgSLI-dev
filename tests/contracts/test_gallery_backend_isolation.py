"""I1: the Algorithms rank fusion consumes LOCAL measurements only.

The two gallery judgment backends own different inputs: the local detectors
answer Algorithms (engine records with a non-``vlm`` producer / ``item.metrics``)
and the VLM scorecard answers AI (``item.analysis``). ``plan-gallery-ai-*`` made
the AI domain read the scorecard; the reverse must never happen — a paid model
answer is not a measurement of the Algorithms backend, and letting it order the
grid makes "Algorithms" silently depend on whether a VLM ran.

The measured defect this ratchet kills (``int/backend-isolation``, W1): the
fusion carried ``_judge_scores``, which read ``item.analysis`` (via
``ai_scored_axes`` and ``analysis.axis_proposals``) for every axis the profile's
judge half named. Two byte-identical ``metrics`` therefore stopped tying once one
card carried a scorecard.

Scope, deliberately narrow: the rank-fusion module itself (``services/
rank_fusion.py``, or a ``services/rank_fusion/`` package if it is ever split).
Fixing the LAYER is not this gate's business — it only proves that the Algorithms
order's own module cannot reach the other backend's output. ``item.analysis_records``
is NOT a violation: records are the engine channel and ``_record_scores`` filters
the ``vlm`` producer (``analysis.read.AI_PRODUCER``) at the source.

Shrink-only allowlist (same mechanism as ``test_analysis_no_raw_metric_reads``):
an entry means "known read, with the wave that removes it", never a rubber stamp.
"""

from __future__ import annotations

import ast

import pytest

from ._framework import SRC, read, rel
from .analysis_gates_allowlist import (
    assert_ratchet,
    add_hit,
    make_key,
    source_line,
)

PLAN = "int/backend-isolation (backend isolation, W1)"

GALLERY = SRC / "tabs" / "image_gallery"
SERVICES = GALLERY / "services"
#: The Algorithms rank module. The contract is about this PATH, not one file:
#: a split into ``services/rank_fusion/`` stays covered.
RANK_FUSION = SERVICES / "rank_fusion.py"
RANK_FUSION_PACKAGE = SERVICES / "rank_fusion"

#: The AI backend's transport/client package (single module or package split).
AI_CLIENT = "ai_client"

#: The scorecard reader the deleted ``_judge_scores`` used. Named separately from
#: the ``.analysis`` attribute because it turns a scorecard object into per-axis
#: numbers — the exact conversion the Algorithms rank must not perform.
AI_SCORECARD_READERS = frozenset({"ai_scored_axes"})

#: ``path|offending source line`` -> why it is still allowed. EMPTY on purpose:
#: the Algorithms fusion has zero legitimate AI reads today, so any entry here is
#: a regression that must name the wave deleting it.
AI_INPUT_READ_ALLOWLIST: dict[str, str] = {}


def _getattr_string(node: ast.Call) -> str | None:
    """The name in ``getattr(obj, "<name>"[, default])``, else ``None``."""
    if not (isinstance(node.func, ast.Name) and node.func.id == "getattr"):
        return None
    if len(node.args) < 2:
        return None
    name = node.args[1]
    if isinstance(name, ast.Constant) and isinstance(name.value, str):
        return name.value
    return None


def _imports_ai_client(node: ast.AST) -> bool:
    """True for ``import ...ai_client`` / ``from ...ai_client import ...``.

    Relative spellings are matched by their last component (``from .ai_client
    import call_sync``), absolute ones by the full dotted module.
    """
    if isinstance(node, ast.Import):
        return any(
            alias.name == AI_CLIENT or alias.name.startswith(AI_CLIENT + ".")
            or alias.name.endswith("." + AI_CLIENT)
            for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module == AI_CLIENT or module.startswith(AI_CLIENT + "."):
            return True
        if module.endswith("." + AI_CLIENT):
            return True
        # ``from tabs.image_gallery.services import ai_client``
        return any(alias.name == AI_CLIENT for alias in node.names)
    return False


def find_ai_input_reads(sources: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """``path|line`` -> occurrences for every AI-input read in *sources*.

    Three spellings: the scorecard attribute (``item.analysis`` and its
    ``getattr`` string form), a call to the scorecard reader
    (``ai_scored_axes``) and any import of the AI client. Comments/docstrings are
    not AST nodes, so prose about the other backend stays allowed; the local
    engine channel (``item.analysis_records``) is a different attribute and is
    not flagged.
    """
    hits: dict[str, tuple[str, ...]] = {}
    for path in sorted(sources):
        source = sources[path]
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            note = ""
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "analysis"
                and isinstance(node.ctx, ast.Load)
            ):
                note = "reads .analysis (the VLM scorecard)"
            elif isinstance(node, ast.Call) and _getattr_string(node) == "analysis":
                note = 'getattr string read "analysis" (the VLM scorecard)'
            elif isinstance(node, ast.Name) and node.id in AI_SCORECARD_READERS:
                note = "calls the AI scorecard reader"
            elif isinstance(node, ast.Attribute) and node.attr in AI_SCORECARD_READERS:
                note = "calls the AI scorecard reader"
            elif _imports_ai_client(node):
                note = "imports the AI client"
            if note:
                add_hit(
                    hits,
                    path=path,
                    lineno=node.lineno,
                    line=source_line(source, node.lineno),
                    note=note,
                )
    return hits


def rank_fusion_sources() -> dict[str, str]:
    """The Algorithms fusion module's sources (``{}`` when the path is gone)."""
    paths = [RANK_FUSION] if RANK_FUSION.is_file() else []
    if RANK_FUSION_PACKAGE.is_dir():
        paths.extend(
            p
            for p in sorted(RANK_FUSION_PACKAGE.rglob("*.py"))
            if "__pycache__" not in p.parts
        )
    return {rel(p): read(p) for p in paths}


# ---------------------------------------------------------------------------
# real tree
# ---------------------------------------------------------------------------


def test_algorithms_rank_fusion_reads_no_ai_output():
    sources = rank_fusion_sources()
    assert sources, (
        f"no rank-fusion module under {rel(SERVICES)} — the Algorithms order moved "
        f"and this gate now scans nothing ({PLAN})"
    )
    assert_ratchet(
        f"I1 Algorithms rank is local-only ({PLAN})",
        AI_INPUT_READ_ALLOWLIST,
        find_ai_input_reads(sources),
    )


# ---------------------------------------------------------------------------
# falsifiability: every claimed spelling is flagged, the local channel is not
# ---------------------------------------------------------------------------


def test_guard_flags_the_scorecard_attribute_and_getattr():
    src = (
        "def scores(item):\n"
        "    first = item.analysis\n"
        '    second = getattr(item, "analysis", None)\n'
        "    return first, second\n"
    )
    path = rel(RANK_FUSION)
    hits = find_ai_input_reads({path: src})
    assert len(hits) == 2
    assert make_key(path, "first = item.analysis") in hits
    assert make_key(path, 'second = getattr(item, "analysis", None)') in hits


def test_guard_flags_the_scorecard_reader_and_the_ai_client():
    src = (
        "from tabs.image_gallery.services.ai_client import call_sync\n"
        "from tabs.image_gallery.models import ai_scored_axes\n"
        "\n"
        "def scores(analysis):\n"
        "    return ai_scored_axes(analysis), call_sync({})\n"
    )
    hits = find_ai_input_reads({rel(RANK_FUSION): src})
    assert len(hits) == 2, hits
    assert make_key(
        rel(RANK_FUSION),
        "from tabs.image_gallery.services.ai_client import call_sync",
    ) in hits
    # The import line alone is harmless (the client could be unused); the CALL
    # is the conversion of a scorecard into numbers, so that is what is flagged.
    assert make_key(
        rel(RANK_FUSION),
        "return ai_scored_axes(analysis), call_sync({})",
    ) in hits


def test_guard_flags_a_relative_ai_client_import():
    src = "from .ai_client import call_sync\n"
    hits = find_ai_input_reads({rel(RANK_FUSION): src})
    assert len(hits) == 1
    assert make_key(rel(RANK_FUSION), "from .ai_client import call_sync") in hits


def test_guard_ignores_the_local_instrument():
    """The engine channel and the raw metrics are Algorithms' own inputs."""
    src = (
        "from tabs.image_gallery.analysis.read import AI_PRODUCER\n"
        "from tabs.image_gallery.services.metric_scores import raw_for\n"
        "\n"
        "def local(item):\n"
        "    records = tuple(getattr(item, 'analysis_records', ()) or ())\n"
        "    metrics = getattr(item, 'metrics', None)\n"
        "    return records, metrics\n"
    )
    assert find_ai_input_reads({rel(RANK_FUSION): src}) == {}


def test_allowlist_is_shrink_only():
    """A stale entry (code fixed, list not updated) must fail the gate."""
    probe = {
        "src/tabs/image_gallery/services/rank_fusion.py|x = item.analysis": (
            "probe: a regression that was fixed but left in the ledger"
        )
    }
    with pytest.raises(AssertionError, match="STALE"):
        assert_ratchet("I1 probe (empty scan)", probe, {})
