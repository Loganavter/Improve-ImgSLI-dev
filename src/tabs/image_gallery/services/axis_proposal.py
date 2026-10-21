"""Model-NAMED axes: the judge's own entries and the pool a scorecard may extend.

The judged axis set is the fixed registry (``metric_scores.SPECS``) plus the
axes the model NAMES. Two producers reach this module, both with the same rule —
a name is nothing without a definition:

- the **selector** (``use_cases/profile_ai``) asks the model for 3..8 axes that
  most differentiate a series, in free form (plan-gallery-ai-judgement §OWNER
  REVISION 2026-10-22). A name that matches a registry id is that id (a local
  detector can score it too); any other name is a first-class entry with a
  definition, a scale and a direction. This is the NORMAL case — the filter that
  intersected the answer with a mode's axis set is gone.
- the **scorecard** (``services/axis_proposal`` below) lets a per-image reply add
  at most two dimensions the asked set is missing, each with this image's score.

Both paths refuse only a proposal that is NOT MEASURABLE, with a recorded reason:

- no NAME (a phrase or an empty string is not an axis);
- no DEFINITION (or a definition that only describes the scene — content is
  identical across variants of one picture and cannot separate them);
- a DUPLICATE of a registry axis (a renamed axis is not a new dimension);
- no SCALE / no SCORE where a number is required.

Pure: no Qt, no HTTP, no registry mutation. A free axis lives on the profile
(selector) or on the result of the image that proposed it (scorecard); the pool
itself is never written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tabs.image_gallery.models import (
    AXIS_DIRECTION_DEFAULT,
    AXIS_DIRECTIONS,
    AiAxisProposal,
)

#: The only scale a scorecard answer may use (the pool's own 0-100 quality
#: scale). A proposal on another scale cannot be compared with a measured axis.
AXIS_PROPOSAL_SCALE = "0-100"

#: Accepted spellings of that scale (normalized to :data:`AXIS_PROPOSAL_SCALE`).
_SCALE_SPELLINGS = frozenset(
    {
        "0-100",
        "0..100",
        "0 to 100",
        "0–100",
        "0—100",
        "0-100%",
    }
)

#: Upper bound per image: a proposal is a *gap* in the pool, not a second
#: scorecard. Beyond this the reply is over-limit and the extra ones are refused.
AXIS_PROPOSAL_LIMIT = 2

#: How many axes the SELECTOR may keep (owner rule: "from 3 to 8"). The floor is
#: the instruction, not a parser refusal — a two-axis answer is kept as given (a
#: parser never fabricates a third) and the trace says so.
AXIS_CHOICE_MIN = 3
AXIS_CHOICE_MAX = 8

#: Refusal codes (the recorded reason). Codes, never prose: a surface localizes
#: them and the trace stays stable across a language switch.
REJECT_NAME = "unusable-name"
REJECT_DEFINITION = "no-definition"
REJECT_CONTENT = "describes-content"
REJECT_SCALE = "unsupported-scale"
REJECT_SCORE = "no-score"
REJECT_DUPLICATE = "duplicate-pool-axis"
REJECT_LIMIT = "over-limit"
#: A name repeated inside ONE reply (the first occurrence is kept).
REJECT_REPEAT = "repeated-axis"
PROPOSAL_REJECT_CODES: tuple[str, ...] = (
    REJECT_NAME,
    REJECT_DEFINITION,
    REJECT_CONTENT,
    REJECT_SCALE,
    REJECT_SCORE,
    REJECT_DUPLICATE,
    REJECT_LIMIT,
    REJECT_REPEAT,
)

#: A name is an axis id, not a phrase: 2–40 characters, starts with a letter,
#: then letters/digits/underscore/space/hyphen (Unicode letters allowed — the
#: judge answers in the UI language, "чистота" is a valid axis name).
_NAME_RE = re.compile(r"^[^\W\d_][\w \-]{1,39}$", re.UNICODE)


#: Vocabulary that makes a definition MEASURABLE: it names a technical
#: dimension of the image (what a detector or a careful eye could score). A
#: definition built only out of scene nouns has no such dimension.
_MEASURABLE_WORDS = frozenset(
    {
        "alias",
        "artifact",
        "banding",
        "bleed",
        "blotch",
        "blur",
        "brightness",
        "blockiness",
        "chroma",
        "chromatic",
        "clarity",
        "clipping",
        "colour",
        "color",
        "compression",
        "contrast",
        "crispness",
        "detail",
        "distortion",
        "dust",
        "edge",
        "exposure",
        "fidelity",
        "fringing",
        "glow",
        "grain",
        "halation",
        "halo",
        "highlight",
        "hue",
        "jpeg",
        "moire",
        "noise",
        "overshoot",
        "posterization",
        "resolution",
        "ringing",
        "saturation",
        "scratch",
        "sepia",
        "shadow",
        "sharpen",
        "sharpness",
        "smear",
        "smoothing",
        "softness",
        "speckle",
        "structure",
        "texture",
        "tone",
        "vignette",
        "white_balance",
    }
)

#: Scene/content vocabulary: a definition that is only about WHAT is depicted
#: cannot separate two variants of the same picture (the prompt's rule).
_CONTENT_WORDS = frozenset(
    {
        "animal",
        "background",
        "beauty",
        "beautiful",
        "building",
        "car",
        "character",
        "composition_subject",
        "dog",
        "face",
        "flower",
        "landscape",
        "person",
        "portrait",
        "scene",
        "sky",
        "subject",
        "tree",
    }
)

_WORD_RE = re.compile(r"[a-z_]+")


def normalize_name(raw) -> str:
    """Canonical axis id for a proposed name (``""`` when unusable).

    Lowercase, spaces/hyphens → ``_``, collapsed. A name must look like an axis
    id (for example "halation" or "sepia_drift"), never a phrase.
    """
    try:
        text = str(raw or "").strip().lower()
    except Exception:
        return ""
    text = re.sub(r"[\s-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text or not _NAME_RE.match(text.replace("_", " ")):
        return ""
    return text


def _words(text: str) -> set[str]:
    return set(_WORD_RE.findall(str(text or "").lower()))


def _definition_problem(definition: str) -> str:
    """``""`` when *definition* names a measurable dimension, else a code."""
    words = _words(definition)
    if len(definition.strip()) < 10 or len(words) < 2:
        return REJECT_DEFINITION
    if not (words & _MEASURABLE_WORDS):
        # A definition about the scene ("how pretty the sky looks") has no
        # dimension to score: identical across variants of one picture.
        return REJECT_CONTENT if (words & _CONTENT_WORDS) else REJECT_DEFINITION
    return ""


def _definition_missing(definition: str) -> bool:
    """True when *definition* says nothing at all (the SELECTOR-level rule).

    The selector's rule is the owner's: a free name WITH a definition is the
    normal case, and the model's own vocabulary is the point — so this checks
    only that a definition EXISTS (a sentence, not a word or a placeholder).
    Judging whether the vocabulary is "technical enough" is the SCORECARD
    proposal rule (``_definition_problem``), where an invented per-image axis
    would otherwise become a weight in the order.
    """
    text = str(definition or "").strip()
    return len(text) < 10 or len(_words(text)) < 2


def _pool_axis_for(name: str) -> str:
    """The existing pool axis *name* duplicates (``""`` when it is new)."""
    try:
        from tabs.image_gallery.services.axis_policy import known_axis
        from tabs.image_gallery.services.metric_scores import SCORECARD_AXIS_IDS

        if name in SCORECARD_AXIS_IDS:
            return name
        resolved = known_axis(name.replace("_", " "))
        if resolved:
            return str(resolved)
        # A pooled id written with a different separator still duplicates it.
        for axis_id in SCORECARD_AXIS_IDS:
            if axis_id.replace("_", "") == name.replace("_", ""):
                return axis_id
    except Exception:
        return ""
    return ""


def _score_of(value) -> int:
    try:
        score = int(float(str(value).strip().rstrip("%")))
    except Exception:
        return -1
    return score if 0 <= score <= 100 else -1


def normalize_direction(value) -> str:
    """Canonical direction token for *value* (``""`` when it says nothing).

    Accepts the canonical tokens plus the spellings a model actually writes
    ("higher", "higher_is_better", "more is better", "lower", "less-is-better",
    "max"/"min"). An unknown value returns ``""`` so the caller applies the
    definition/default rule instead of storing a guess.
    """
    try:
        text = re.sub(r"[\s_]+", "-", str(value or "").strip().lower())
    except Exception:
        return ""
    text = text.strip("-")
    if not text:
        return ""
    if text in AXIS_DIRECTIONS:
        return text
    if text in {"higher", "more", "more-is-better", "higher-better", "max", "up", "asc"}:
        return AXIS_DIRECTIONS[0]
    if text in {"lower", "less", "less-is-better", "lower-better", "min", "down", "desc"}:
        return AXIS_DIRECTIONS[1]
    return ""


#: Definition phrases that flip the DEFAULT direction: the owner rule is
#: "higher is better unless the definition says otherwise", so a definition that
#: names 0 as the good end ("0 = no ringing") is a lower-is-better axis.
_LOWER_IS_BETTER_CUES: tuple[str, ...] = (
    "lower is better",
    "lower-is-better",
    "less is better",
    "smaller is better",
    "fewer is better",
    "0 = no",
    "0=no",
    "0 = none",
    "0=none",
    "0 = clean",
    "0=clean",
    "0 is clean",
    "0 = absent",
)


def direction_of(entry, definition=None) -> str:
    """The direction of an axis entry: explicit field, else its definition.

    ``entry`` may be the raw reply dict (``{"direction": "lower-is-better"}``) or
    any object carrying ``.direction``. An explicit but unrecognized value is
    ignored in favour of the definition; the fallback is
    ``AXIS_DIRECTION_DEFAULT`` ("higher is better").
    """
    if isinstance(entry, dict):
        explicit = entry.get("direction")
    else:
        explicit = getattr(entry, "direction", "")
    token = normalize_direction(explicit)
    if token:
        return token
    if definition is None:
        if isinstance(entry, dict):
            definition = entry.get("definition")
        else:
            definition = getattr(entry, "definition", "")
    text = str(definition or "").strip().lower()
    for cue in _LOWER_IS_BETTER_CUES:
        if cue in text:
            return AXIS_DIRECTIONS[1]
    return AXIS_DIRECTION_DEFAULT


def _scale_of(value) -> str:
    try:
        text = str(value or "").strip().lower()
    except Exception:
        return ""
    return AXIS_PROPOSAL_SCALE if text in _SCALE_SPELLINGS else ""


def refusal_reason(entry) -> str:
    """Why *entry* is not a usable axis proposal (``""`` when it is)."""
    if not isinstance(entry, dict):
        return REJECT_NAME
    name = normalize_name(entry.get("name"))
    if not name:
        return REJECT_NAME
    duplicate = _pool_axis_for(name)
    if duplicate:
        return f"{REJECT_DUPLICATE}:{duplicate}"
    problem = _definition_problem(str(entry.get("definition", "") or ""))
    if problem:
        return problem
    if not _scale_of(entry.get("scale")):
        return REJECT_SCALE
    if _score_of(entry.get("score")) < 0:
        return REJECT_SCORE
    return ""


def parse_proposals(value, *, limit: int = AXIS_PROPOSAL_LIMIT):
    """``(accepted, refusals)`` for one reply's ``axis_proposals`` field.

    ``accepted`` is a tuple of :class:`AiAxisProposal` (``producer="vlm"``,
    ``kind="candidate"``); ``refusals`` is a tuple of ``(name, reason)`` for
    every entry that was NOT stored — an unusable entry still has a name (or
    ``"#"`` + position when it has none) so the loss is traceable. Unknown
    duplicates inside one reply keep the first occurrence. Never raises.
    """
    accepted: list[AiAxisProposal] = []
    refusals: list[tuple[str, str]] = []
    try:
        entries = list(value or ())
    except Exception:
        return (), ()
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        name = normalize_name((entry or {}).get("name")) if isinstance(entry, dict) else ""
        row_name = name or f"#{index + 1}"
        reason = refusal_reason(entry)
        if not reason and name in seen:
            reason = REJECT_DUPLICATE + ":repeat"
        if not reason and len(accepted) >= int(limit):
            reason = REJECT_LIMIT
        if reason:
            refusals.append((row_name, reason))
            continue
        seen.add(name)
        definition = str(entry.get("definition", "") or "").strip()[:240]
        accepted.append(
            AiAxisProposal(
                name=name,
                definition=definition,
                scale=AXIS_PROPOSAL_SCALE,
                score=_score_of(entry.get("score")),
                direction=direction_of(entry, definition),
            )
        )
    return tuple(accepted), tuple(refusals)


@dataclass(frozen=True)
class AxisChoiceSet:
    """The selector reply split into what it can become (plan P7-A).

    ``registry_ids`` are the axes of the fixed pool the judge named (a local
    detector can produce them; the profile keeps them in ``axis_ids``).
    ``entries`` are the axes the judge NAMED that the pool does not have — each a
    first-class :class:`~tabs.image_gallery.models.AiAxisProposal` with a
    definition, a scale and a direction. ``refusals`` is ``(name, reason)`` for
    every pick that was NOT stored, so the loss is traceable and never silent.

    A registry id and an entry are different PROVENANCE, not different quality:
    the first reads "measured locally", the second "measured by the judge".
    """

    registry_ids: tuple[str, ...] = ()
    entries: tuple[AiAxisProposal, ...] = ()
    refusals: tuple[tuple[str, str], ...] = ()


def parse_axis_choices(value, *, limit: int = AXIS_CHOICE_MAX) -> AxisChoiceSet:
    """Classify a selector reply's ``axes`` list (never raises).

    Every element may be:

    - a string: a registry axis id (the reply of a terse/older answer) — kept
      when it IS a pool id, refused as ``no-definition`` otherwise (a bare name
      with no meaning cannot be measured, and the app will not invent one);
    - an object: ``{name, definition, scale, direction}``. A name equal to a
      registry id is that registry axis (the model asked for a measurable
      dimension that already exists — the local detector should score it too);
      any other name becomes a first-class entry, which is the normal answer of
      the free-form selector.

    The pool filter that used to drop every non-registry name is GONE (owner
    revision 2026-10-22): a free name WITH a definition is kept. What stays
    refused is what is not measurable — an unusable/empty name, an entry without
    a definition (or one that only describes the scene), and a name repeated
    inside one reply.
    """
    try:
        items = list(value or ())
    except Exception:
        return AxisChoiceSet()
    try:
        from tabs.image_gallery.services.metric_profile import MEASURED_POOL

        pool = frozenset(MEASURED_POOL)
    except Exception:
        pool = frozenset()

    registry: list[str] = []
    entries: list[AiAxisProposal] = []
    refusals: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _refuse(row_name: str, reason: str) -> None:
        refusals.append((row_name, reason))

    for index, item in enumerate(items):
        if isinstance(item, str):
            raw_name = item
            name = normalize_name(item)
            if not name:
                _refuse(item.strip() or f"#{index + 1}", REJECT_NAME)
                continue
            if name not in pool:
                _refuse(name, REJECT_DEFINITION)
                continue
            definition = ""
            direction = AXIS_DIRECTION_DEFAULT
        elif isinstance(item, dict):
            raw_name = item.get("name")
            name = normalize_name(raw_name)
            if not name:
                _refuse(str(raw_name or f"#{index + 1}")[:40], REJECT_NAME)
                continue
            definition = str(item.get("definition", "") or "").strip()[:240]
            direction = direction_of(item, definition)
            if name in pool:
                # A named registry axis: it is the pool axis, measured locally.
                pass
            else:
                if _definition_missing(definition):
                    _refuse(name, REJECT_DEFINITION)
                    continue
                if not _scale_of(item.get("scale")):
                    _refuse(name, REJECT_SCALE)
                    continue
        else:
            _refuse(f"#{index + 1}", REJECT_NAME)
            continue

        if name in seen:
            _refuse(name, REJECT_REPEAT)
            continue
        if name in pool:
            seen.add(name)
            if name not in registry:
                registry.append(name)
            continue
        if len(entries) >= int(limit):
            _refuse(name, REJECT_LIMIT)
            continue
        seen.add(name)
        entries.append(
            AiAxisProposal(
                name=name,
                definition=definition,
                scale=AXIS_PROPOSAL_SCALE,
                score=-1,  # chosen, not yet read: the scorecard fills the numbers
                direction=direction,
            )
        )
    return AxisChoiceSet(
        registry_ids=tuple(registry),
        entries=tuple(entries),
        refusals=tuple(refusals),
    )


__all__ = [
    "AXIS_CHOICE_MAX",
    "AXIS_CHOICE_MIN",
    "AXIS_PROPOSAL_LIMIT",
    "AXIS_PROPOSAL_SCALE",
    "AxisChoiceSet",
    "PROPOSAL_REJECT_CODES",
    "REJECT_CONTENT",
    "REJECT_DEFINITION",
    "REJECT_DUPLICATE",
    "REJECT_LIMIT",
    "REJECT_NAME",
    "REJECT_REPEAT",
    "REJECT_SCALE",
    "REJECT_SCORE",
    "direction_of",
    "normalize_direction",
    "normalize_name",
    "parse_axis_choices",
    "parse_proposals",
    "refusal_reason",
]
