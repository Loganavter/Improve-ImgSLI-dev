"""ADR 009 wave A1 — the analysis-backend adapter contract, errors and registry.

ADR 009 replaces "two judgment domains decided by a controller field" with two
BACKENDS behind one adapter contract. This wave ships only the contract: nothing
in the app is rewired yet (``metric_profile``, ``profile_for_domain``,
``rank_fusion``, ``pairwise_rank``, ``cache_reset`` and the controller keep
their current shape until A2–A4).

The contract is modelled on two older idioms in this tree, deliberately:

* ``ui/canvas_infra/scene/stacking_policy.py`` — a semantic declaration is
  resolved by one central policy and an unresolvable declaration raises
  ``KeyError`` instead of taking a silent default;
* ``.../keyframing/adapters/static.py`` — values are reachable only through the
  owning adapter's own bindings; an unknown descriptor is a lookup failure.

So every boundary here FAILS LOUDLY and names the offending ids/versions, and
there is no ``fallback()`` / ``default()`` / ``or_other_backend()`` anywhere in
the core — ADR 009 forbids a fallback branch.

Red-before: ``src/tabs/image_gallery/backends/`` did not exist, so this module
failed at import (collection error) before A1 landed.
"""

from __future__ import annotations

import pytest

from tabs.image_gallery import backends
from tabs.image_gallery.backends import (
    AnalysisBackend,
    AnalysisBackendRegistry,
    BackendDescriptor,
    BackendMismatch,
    CapabilityNotDeclared,
    CacheNamespaceCollision,
    MeasurementEnvelope,
    NoProfileYet,
    OwnedProfile,
    ProfileRequest,
    RankRequest,
    RankResult,
    SchemaMismatch,
    assert_envelope_owned,
    require_capability,
)

SCHEMA = 1


def _descriptor(
    backend_id: str = "algorithms",
    *,
    schema_version: int = SCHEMA,
    capabilities: frozenset[str] = frozenset({"local-scores"}),
    cache_namespace: str | None = None,
) -> BackendDescriptor:
    return BackendDescriptor(
        backend_id=backend_id,
        schema_version=schema_version,
        capabilities=capabilities,
        cache_namespace=cache_namespace or f"gallery.{backend_id}",
    )


def _profile(
    backend_id: str = "algorithms",
    *,
    schema_version: int = SCHEMA,
    profile_id: str = "profile-1",
) -> OwnedProfile:
    return OwnedProfile(
        backend_id=backend_id,
        profile_id=profile_id,
        schema_version=schema_version,
        axes=("sharpness", "contrast"),
        entries=(),
    )


def _envelope(
    backend_id: str = "algorithms",
    *,
    schema_version: int = SCHEMA,
    profile_id: str = "profile-1",
) -> MeasurementEnvelope:
    return MeasurementEnvelope(
        backend_id=backend_id,
        schema_version=schema_version,
        profile_id=profile_id,
        records=(),
    )


class _Adapter:
    """Smallest object the registry may accept: a descriptor + the protocol calls."""

    def __init__(self, descriptor: BackendDescriptor) -> None:
        self.descriptor = descriptor
        self._profile: OwnedProfile | None = None

    def make_profile(self, request: ProfileRequest) -> OwnedProfile:
        self._profile = _profile(self.descriptor.backend_id)
        return self._profile

    def measure(self, request) -> MeasurementEnvelope:
        if self._profile is None:
            raise NoProfileYet(
                backend_id=self.descriptor.backend_id, operation="measure"
            )
        return _envelope(self.descriptor.backend_id)

    def rank(self, request) -> RankResult:
        if self._profile is None:
            raise NoProfileYet(
                backend_id=self.descriptor.backend_id, operation="rank"
            )
        return RankResult(ranks={})

    def reset(self) -> None:
        self._profile = None

    def release(self) -> None:
        self._profile = None


# ---------------------------------------------------------------------------
# 1. registry: duplicates refused, unknown id is a KeyError, order is stable
# ---------------------------------------------------------------------------


def test_duplicate_backend_id_is_refused() -> None:
    registry = AnalysisBackendRegistry()
    registry.register(_Adapter(_descriptor("algorithms")))

    with pytest.raises(ValueError) as excinfo:
        registry.register(
            _Adapter(_descriptor("algorithms", cache_namespace="gallery.algorithms.2"))
        )
    assert "algorithms" in str(excinfo.value)


def test_duplicate_cache_namespace_raises_collision() -> None:
    registry = AnalysisBackendRegistry()
    registry.register(_Adapter(_descriptor("algorithms", cache_namespace="gallery.shared")))

    with pytest.raises(CacheNamespaceCollision) as excinfo:
        registry.register(
            _Adapter(_descriptor("ai", cache_namespace="gallery.shared"))
        )
    message = str(excinfo.value)
    assert "gallery.shared" in message
    # Both claimants are named: the collision is between two backends.
    assert "algorithms" in message and "ai" in message


def test_unknown_backend_id_raises_key_error() -> None:
    registry = AnalysisBackendRegistry()
    registry.register(_Adapter(_descriptor("algorithms")))

    with pytest.raises(KeyError) as excinfo:
        registry["ai"]
    # Never a default object, never None — a KeyError whose message names the id.
    assert "ai" in str(excinfo.value)


def test_iter_backends_is_deterministic() -> None:
    def build(order: tuple[str, ...]) -> AnalysisBackendRegistry:
        registry = AnalysisBackendRegistry()
        for backend_id in order:
            registry.register(_Adapter(_descriptor(backend_id)))
        return registry

    first = build(("ai", "algorithms", "mid"))
    second = build(("mid", "ai", "algorithms"))

    ids = [adapter.descriptor.backend_id for adapter in first.iter_backends()]
    assert ids == ["ai", "algorithms", "mid"]
    assert ids == [adapter.descriptor.backend_id for adapter in first.iter_backends()]
    assert ids == [adapter.descriptor.backend_id for adapter in second.iter_backends()]


def test_module_registry_is_subscriptable() -> None:
    # The interface later waves consume is ``registry[backend_id]`` on the
    # exported singleton, plus the module-level ``register``/``iter_backends``
    # helpers — never a hand-maintained list beside it.
    assert isinstance(backends.registry, AnalysisBackendRegistry)
    assert callable(backends.register)
    assert callable(backends.iter_backends)
    # No mutation here: the singleton is process-wide and a probe left in it
    # would leak into every later contract that enumerates the real backends.


# ---------------------------------------------------------------------------
# 2. boundary: an artifact of another backend / another schema is refused
# ---------------------------------------------------------------------------


def test_envelope_from_another_backend_is_refused() -> None:
    descriptor = _descriptor("algorithms")

    with pytest.raises(BackendMismatch) as excinfo:
        assert_envelope_owned(descriptor, _envelope("ai"))

    message = str(excinfo.value)
    assert "ai" in message and "algorithms" in message


def test_descriptor_owns_only_its_own_profile() -> None:
    descriptor = _descriptor("algorithms")

    descriptor.assert_owns(_profile("algorithms"))  # its own: no raise

    with pytest.raises(BackendMismatch) as excinfo:
        descriptor.assert_owns(_profile("ai"))
    assert "ai" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 3. an adapter with no profile yet is loud, never empty-handed
# ---------------------------------------------------------------------------


def test_measure_and_rank_without_a_profile_raise_no_profile_yet() -> None:
    adapter = _Adapter(_descriptor("algorithms"))

    with pytest.raises(NoProfileYet) as excinfo:
        adapter.measure(object())
    assert "algorithms" in str(excinfo.value)
    with pytest.raises(NoProfileYet):
        adapter.rank(object())

    adapter.make_profile(ProfileRequest(mode="camera"))
    adapter.measure(object())
    adapter.rank(object())

    adapter.reset()
    with pytest.raises(NoProfileYet):
        adapter.measure(object())


# ---------------------------------------------------------------------------
# 4. requesting a capability the backend never declared
# ---------------------------------------------------------------------------


def test_undeclared_capability_is_refused() -> None:
    descriptor = _descriptor("algorithms", capabilities=frozenset({"local-scores"}))

    require_capability(descriptor, "local-scores")  # declared: no raise

    with pytest.raises(CapabilityNotDeclared) as excinfo:
        require_capability(descriptor, "pairwise")

    message = str(excinfo.value)
    assert "pairwise" in message and "algorithms" in message


# ---------------------------------------------------------------------------
# 5. a profile / envelope carrying another schema version
# ---------------------------------------------------------------------------


def test_profile_with_foreign_schema_version_is_refused() -> None:
    descriptor = _descriptor("algorithms", schema_version=SCHEMA)

    with pytest.raises(SchemaMismatch) as excinfo:
        descriptor.assert_owns(_profile("algorithms", schema_version=SCHEMA + 1))

    message = str(excinfo.value)
    assert str(SCHEMA) in message and str(SCHEMA + 1) in message


def test_envelope_with_foreign_schema_version_is_refused() -> None:
    descriptor = _descriptor("algorithms", schema_version=SCHEMA)

    with pytest.raises(SchemaMismatch) as excinfo:
        assert_envelope_owned(
            descriptor, _envelope("algorithms", schema_version=SCHEMA + 1)
        )
    assert str(SCHEMA) in str(excinfo.value)


# ---------------------------------------------------------------------------
# 6. non-vacuity: the real package, the declared surface, no fallback seam
# ---------------------------------------------------------------------------


def test_public_surface_exists_on_the_real_package() -> None:
    from pathlib import Path

    package_file = Path(backends.__file__).resolve()
    assert package_file.parent.name == "backends"
    assert package_file.parent.parent.name == "image_gallery"

    for name in (
        "AnalysisBackend",
        "AnalysisBackendRegistry",
        "BackendDescriptor",
        "OwnedProfile",
        "MeasurementEnvelope",
        "ProfileRequest",
        "MeasureRequest",
        "RankRequest",
        "RankResult",
        "registry",
        "register",
        "iter_backends",
        "require_capability",
        "assert_envelope_owned",
        "BackendMismatch",
        "NoProfileYet",
        "CapabilityNotDeclared",
        "SchemaMismatch",
        "CacheNamespaceCollision",
    ):
        assert hasattr(backends, name), f"missing public name: {name}"
        assert name in backends.__all__, f"{name} is public but not in __all__"


def test_protocol_declares_the_whole_adapter_surface() -> None:
    for method in ("make_profile", "measure", "rank", "reset", "release"):
        assert callable(getattr(AnalysisBackend, method, None)), method
    assert "descriptor" in getattr(AnalysisBackend, "__annotations__", {})


def test_rank_result_cannot_be_mutated_after_delivery() -> None:
    result = RankResult(ranks={"b": 2, "a": 1})
    assert dict(result.ranks) == {"a": 1, "b": 2}
    with pytest.raises(TypeError):
        result.ranks["a"] = 99  # type: ignore[index]


def test_no_fallback_helper_is_exported() -> None:
    # ADR 009: no fallback branch anywhere in the core — a second backend is
    # chosen by the caller, never silently substituted here.
    forbidden = {"fallback", "default", "default_backend", "or_other_backend"}
    assert forbidden.isdisjoint(set(backends.__all__))
    for adapter in backends.iter_backends():
        assert not hasattr(adapter, "fallback")
