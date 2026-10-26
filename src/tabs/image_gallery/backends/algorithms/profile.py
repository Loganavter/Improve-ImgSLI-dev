"""The Algorithms analysis backend — the local detectors' judgment domain.

ADR 009 wave A2: the profile of the local/fusion domain is made, owned and read
HERE instead of in the tab's core. The backend does not re-implement anything —
every call delegates to the entry point that already owned that behaviour:

* ``make_profile`` → ``use_cases.profile_select.derive_profile`` (the series
  offer: ``metric_profile.profile_for_series`` over the measured spreads,
  falling back to the mode mapping only while the series has no discriminating
  measurement — the LAST local fallback, named as such by the source label);
* ``measure`` → ``analysis.read.read_axes(domain="algorithms")``, the one read
  path whose records are the engine's ``AxisValue`` values;
* ``rank`` → ``rank_fusion.rank_series`` (the deterministic fusion).

What is NEW is the ownership, not the computation:

* a profile this backend did not make from the Algorithms builders is refused
  at the boundary (``BackendMismatch``) — the judge's ``source="vlm"`` answer
  can never enter this backend, and a profile this backend cannot find among the
  ones it made is ``NoProfileYet``, never a mode-mapping substitute;
* the state slot write and read go through the adapter (``install`` /
  ``load_profile``), so the core no longer decides which profile belongs here.

The disk caches (metrics/proxy pins) are untouched: their reset is ADR 009 wave
A4 (``use_cases.cache_reset``). ``reset`` here drops the in-memory profile
generations, which is what the folder-generation reset needs.
"""

from __future__ import annotations

from tabs.image_gallery.backends.context import (
    PROFILE_SCHEMA_VERSION,
    MeasuredItem,
    SeriesContext,
    item_key_of,
    owned_profile,
    profile_axes,
    profile_identity,
    select_members,
)
from tabs.image_gallery.backends.contract import (
    BackendDescriptor,
    MeasurementEnvelope,
    MeasureRequest,
    OwnedProfile,
    ProfileRequest,
    RankRequest,
    RankResult,
)
from tabs.image_gallery.backends.errors import BackendMismatch, NoProfileYet
from tabs.image_gallery.services.metric_profile import (
    ALGORITHMS_PROFILE_SLOT,
    DOMAIN_ALGORITHMS,
    ForeignProfileError,
    domain_of,
)

#: What this backend promises. ``profile``/``measure``/``rank``/``reset`` are the
#: four things the Algorithms domain actually does; there is deliberately no
#: ``pairwise``/``ask`` — a paid judge call belongs to the AI backend.
CAPABILITIES: frozenset[str] = frozenset({"measure", "rank", "profile", "reset"})


class AlgorithmsBackend:
    """The local detectors' backend: series offer, local read, fusion rank.

    One instance per process (``BACKEND`` below) is the registry's adapter; the
    in-memory profile generations are keyed by ``profile_id``, so a caller that
    holds an owned profile from an earlier generation can still be answered
    correctly and a caller from another (or a reset) generation is refused with
    ``NoProfileYet`` instead of being measured against the wrong axis set.
    """

    descriptor = BackendDescriptor(
        backend_id=DOMAIN_ALGORITHMS,
        schema_version=PROFILE_SCHEMA_VERSION,
        capabilities=CAPABILITIES,
        cache_namespace="algorithms",
    )

    #: The ``GalleryState`` field this backend owns — written by :meth:`install`
    #: and read by :meth:`load_profile`, never by the core.
    slot = ALGORITHMS_PROFILE_SLOT

    def __init__(self) -> None:
        self._profiles: dict[str, object] = {}
        self._current: OwnedProfile | None = None

    # -- profile -----------------------------------------------------------

    def make_profile(
        self,
        request: ProfileRequest,
        *,
        context: SeriesContext | None = None,
    ) -> OwnedProfile:
        """Derive the series offer through the existing builder and own it.

        ``context.members`` is the live folder; without one the builder sees an
        empty series and answers exactly as it does today (the mode mapping).
        A profile the local builder cannot legitimately produce — anything
        tagged as the judge's (``source="vlm"``) — is refused: this backend owns
        local axes only.
        """
        from tabs.image_gallery.use_cases.profile_select import derive_profile

        members = select_members(
            request.member_keys, (context.members if context is not None else ())
        )
        profile = derive_profile(
            members,
            mode=request.mode,
            has_reference=request.has_reference,
        )
        tag = domain_of(profile)
        if tag != self.descriptor.backend_id:
            raise BackendMismatch(
                what="profile",
                expected_backend_id=self.descriptor.backend_id,
                actual_backend_id=tag,
            )
        return self._own(profile)

    def install(self, state, profile=None):
        """Store this backend's profile in ITS state slot and return it.

        The Algorithms slot accepts the local derivation only: a foreign-tagged
        profile is ``ForeignProfileError`` (the same loud seam the slot reader
        raised), so a caller cannot park the judge's axis set here.
        """
        if profile is None:
            profile = self._current_metric()
        if profile is None:
            raise NoProfileYet(
                backend_id=self.descriptor.backend_id, operation="install"
            )
        tag = domain_of(profile)
        if tag != self.descriptor.backend_id:
            raise ForeignProfileError(
                f"state.{self.slot} would hold a {tag}-tagged profile "
                f"(source={getattr(profile, 'source', '?')!r}); the "
                f"{self.descriptor.backend_id} backend must not own it"
            )
        if profile_identity(self.descriptor, profile) not in self._profiles:
            # An answer that arrived through another seam (the controller's
            # landing path) becomes an owned generation here, so a later
            # ``measure``/``rank`` against its OwnedProfile resolves instead of
            # claiming the backend has no such profile while its slot holds it.
            self._own(profile)
        setattr(state, self.slot, profile)
        return profile

    def load_profile(self, state):
        """Read this backend's slot, or ``None`` when it has not answered yet.

        An EMPTY slot is ``None`` ("nothing derived yet"); a slot holding the
        other backend's profile is loud (``ForeignProfileError``) — the same two
        answers the core reader gave, now decided by the owner.
        """
        if state is None:
            return None
        try:
            profile = getattr(state, self.slot, None)
        except Exception:
            profile = None
        if profile is None:
            return None
        tag = domain_of(profile)
        if tag != self.descriptor.backend_id:
            raise ForeignProfileError(
                f"state.{self.slot} holds a {tag}-tagged profile (source="
                f"{getattr(profile, 'source', '?')!r}); the "
                f"{self.descriptor.backend_id} backend must not read it"
            )
        return profile

    # -- measurement / rank ------------------------------------------------

    def measure(
        self,
        request: MeasureRequest,
        *,
        context: SeriesContext | None = None,
    ) -> MeasurementEnvelope:
        """Per-member ``AxisValue`` records, read through ``analysis.read``."""
        from tabs.image_gallery.analysis.read import read_axes

        profile = self._require_profile(request.profile, operation="measure")
        members = select_members(
            request.item_keys, (context.members if context is not None else ())
        )
        axes = profile_axes(profile)
        records = tuple(
            MeasuredItem(
                item_key=item_key_of(member),
                records=tuple(
                    read_axes(
                        member,
                        domain=DOMAIN_ALGORITHMS,
                        axes=axes,
                        profile=profile,
                    )
                ),
            )
            for member in members
        )
        return MeasurementEnvelope(
            backend_id=self.descriptor.backend_id,
            schema_version=self.descriptor.schema_version,
            profile_id=request.profile.profile_id,
            records=records,
        )

    def rank(
        self,
        request: RankRequest,
        *,
        context: SeriesContext | None = None,
    ) -> RankResult:
        """The deterministic fusion order over this backend's own profile."""
        from tabs.image_gallery.services.rank_fusion import rank_series

        profile = self._require_profile(request.profile, operation="rank")
        members = select_members(
            request.item_keys, (context.members if context is not None else ())
        )
        ranks = rank_series(
            members,
            mode=getattr(profile, "mode", None),
            profile=profile,
            pairwise_order=request.pairwise_order or None,
        )
        return RankResult(ranks=ranks or {})

    # -- lifecycle ---------------------------------------------------------

    def reset(self) -> None:
        """Drop the in-memory profile generations (a new folder generation)."""
        self._profiles.clear()
        self._current = None

    def release(self) -> None:
        """Drop everything this backend holds; ``reset`` is the same operation."""
        self.reset()

    # -- internals ---------------------------------------------------------

    @property
    def profile(self):
        """The ``MetricProfile`` currently owned (``None`` before one is made)."""
        return self._current_metric()

    def _own(self, profile) -> OwnedProfile:
        owned = owned_profile(self.descriptor, profile)
        self._profiles[owned.profile_id] = profile
        self._current = owned
        return owned

    def _current_metric(self):
        return self._metric(self._current.profile_id) if self._current else None

    def _metric(self, profile_id: str):
        return self._profiles.get(profile_id)

    def _require_profile(self, owned: OwnedProfile, *, operation: str):
        """The owned profile's ``MetricProfile``, or a loud refusal.

        Both halves are checked: the artifact must belong to this backend
        (``BackendMismatch`` — the judge's profile is not measurable here) and it
        must be one of the generations this adapter built (``NoProfileYet`` —
        an empty slot, a reset, or a profile from another folder generation).
        """
        self.descriptor.assert_owns(owned)
        profile = self._metric(getattr(owned, "profile_id", ""))
        if profile is None:
            raise NoProfileYet(
                backend_id=self.descriptor.backend_id, operation=operation
            )
        return profile

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return (
            f"AlgorithmsBackend(profiles={len(self._profiles)}, "
            f"slot={self.slot!r})"
        )


__all__ = ["CAPABILITIES", "AlgorithmsBackend"]
