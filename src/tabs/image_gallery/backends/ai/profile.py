"""The AI analysis backend — the vision judge's judgment domain.

ADR 009 wave A2: the judge's axis set is made, owned and read HERE. As with the
Algorithms adapter nothing is re-implemented; each call delegates to the entry
point that already owns the behaviour:

* ``make_profile`` → ``use_cases.profile_ai.choose_profile_sync`` (one pinned
  call per folder generation: probe members, free-form axis naming, the 5..8
  rule, the pin). Its ``None`` — AI not configured, no probe, transport failure,
  an unusable reply — is this backend having NO profile, so it surfaces as
  ``NoProfileYet``; it is never repaired with the local axis set (owner rule
  2026-10-26, ``ANALYSIS_BACKENDS.md`` §5);
* ``measure`` → ``analysis.read.read_axes(domain="ai")``, i.e. the scorecard's
  per-axis records;
* ``rank`` → ``services.jev_client.rank_series_jev`` (the AI-domain ranker over
  the measured vector). ``None`` from a degraded Jev answer (Noul / low
  confidence / transport error / malformed) is an EMPTY ``RankResult``: the
  contract's "a path absent from ``ranks`` is unmeasured — never rank 0, never a
  borrowed number". The Algorithms order is NOT substituted here; that decision
  belongs to the A3 rank wiring, not to the owner of the profile.

Two capabilities are declared beyond the four the Algorithms backend has —
``pairwise`` and ``ask`` — because both are AI-domain-only features the rules
already gate (``pairwise_rank`` runs in the AI domain only, ``ask_router`` is
advisory). Their wire is ADR 009 wave A3 (``use_cases.pairwise_rank`` /
``use_cases.ai_analysis`` rank block are explicitly not rewired by this wave).
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
    AI_PROFILE_SLOT,
    DOMAIN_AI,
    ForeignProfileError,
    domain_of,
)

#: What this backend promises: the four shared operations plus the two features
#: only the judge's domain has (pairwise near-tie passes, advisory questions).
CAPABILITIES: frozenset[str] = frozenset(
    {"measure", "rank", "profile", "pairwise", "ask", "reset"}
)


class AIBackend:
    """The vision judge's backend: named axes, scorecard read, Jev rank.

    One instance per process (``BACKEND`` below) is the registry's adapter. An
    EMPTY profile is a first-class state: ``make_profile`` refuses to invent one
    (``NoProfileYet``), ``measure``/``rank`` refuse to run without one, and the
    UI's existing "not ready / no profile" surfaces paint instead of showing
    local detector numbers (``use_cases.action_context.REFUSAL_NO_PROFILE``).
    """

    descriptor = BackendDescriptor(
        backend_id=DOMAIN_AI,
        schema_version=PROFILE_SCHEMA_VERSION,
        capabilities=CAPABILITIES,
        cache_namespace="ai",
    )

    #: The ``GalleryState`` field this backend owns.
    slot = AI_PROFILE_SLOT

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
        """Ask the judge for this series' axes through the existing selector.

        The selector's answer is pinned in ``services.profile_cache`` exactly as
        today (one paid call per unchanged folder generation). No answer — the
        backend is not configured, no probe could be prepared, the transport
        failed, the reply broke the 5..8/evidence rule — is ``NoProfileYet``: the
        AI backend has no profile, and the local mode mapping is not a profile of
        THIS backend.
        """
        from tabs.image_gallery.use_cases import profile_ai

        context = context if context is not None else SeriesContext()
        members = select_members(request.member_keys, context.members)
        profile = profile_ai.choose_profile_sync(
            members,
            mode=request.mode,
            settings=context.settings,
            folder_key=context.folder_key,
            salience=context.salience,
            reference_path=context.reference_path,
            cache=context.cache,
            client_call=context.client_call,
            refresh=bool(context.refresh),
        )
        if profile is None:
            raise NoProfileYet(
                backend_id=self.descriptor.backend_id, operation="make_profile"
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

        The AI slot accepts the judge's own answer only: a series/heuristic
        (Algorithms) profile here would let the local derivation fuel the AI
        prompt, so it is ``ForeignProfileError`` — the adapter decides, not the
        core.
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
            # ``measure``/``rank`` against its OwnedProfile resolves.
            self._own(profile)
        setattr(state, self.slot, profile)
        return profile

    def load_profile(self, state):
        """This backend's slot: ``None`` when the judge has not answered yet."""
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
        """The judge's per-axis records, read through ``analysis.read``.

        No request is issued here: the scorecard numbers are already on the
        items (``item.analysis``), and an item the model has not scored is a
        ``gap`` record — never a detector number.
        """
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
                    read_axes(member, domain=DOMAIN_AI, axes=axes, profile=profile)
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
        """The AI-domain order through the existing Jev rank entry point."""
        from tabs.image_gallery.services import jev_client

        profile = self._require_profile(request.profile, operation="rank")
        members = select_members(
            request.item_keys, (context.members if context is not None else ())
        )
        context = context if context is not None else SeriesContext()
        base_url = str(getattr(context.settings, "base_url", "") or "")
        api_key = str(getattr(context.settings, "api_key", "") or "")
        client = context.client or jev_client.make_client(base_url, api_key)
        ranks = jev_client.rank_series_jev(
            members,
            mode=getattr(profile, "mode", None),
            client=client,
            cache=context.cache,
            domain=DOMAIN_AI,
            profile=profile,
            base_url=base_url,
        )
        return RankResult(ranks=ranks or {})

    # -- lifecycle ---------------------------------------------------------

    def reset(self) -> None:
        """Drop the in-memory profile generations.

        The pinned selector answers and the pairwise verdict cache are disk /
        in-memory caches of their own seams (``profile_cache`` /
        ``pairwise_rank.clear_default_cache``); clearing them is ADR 009 wave A4
        (``use_cases.cache_reset``) and is NOT duplicated here.
        """
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
        """The owned profile's ``MetricProfile``, or a loud refusal (see A2 rules)."""
        self.descriptor.assert_owns(owned)
        profile = self._metric(getattr(owned, "profile_id", ""))
        if profile is None:
            raise NoProfileYet(
                backend_id=self.descriptor.backend_id, operation=operation
            )
        return profile

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"AIBackend(profiles={len(self._profiles)}, slot={self.slot!r})"


__all__ = ["CAPABILITIES", "AIBackend"]
