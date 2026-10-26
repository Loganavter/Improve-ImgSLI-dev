"""Analysis-backend adapter contract, typed errors and registry (ADR 009 A1).

The public surface later waves consume::

    BackendDescriptor(backend_id, schema_version, capabilities, cache_namespace)
    AnalysisBackend.descriptor
    AnalysisBackend.make_profile(ProfileRequest) -> OwnedProfile
    AnalysisBackend.measure(MeasureRequest) -> MeasurementEnvelope
    AnalysisBackend.rank(RankRequest) -> RankResult
    AnalysisBackend.reset() -> None ; AnalysisBackend.release() -> None
    OwnedProfile(backend_id, profile_id, schema_version, axes, entries)
    MeasurementEnvelope(backend_id, schema_version, profile_id, records)
    registry[backend_id]      # KeyError when unknown
    iter_backends()
    require_capability(descriptor, name)          # CapabilityNotDeclared
    assert_envelope_owned(descriptor, envelope)   # BackendMismatch
    errors: BackendMismatch, NoProfileYet, CapabilityNotDeclared, SchemaMismatch,
            CacheNamespaceCollision

Re-exports are the only content: no behaviour is wired into the app in this
wave (A2–A4 rewire the profile producers, the measurement/rank paths and the
controller).
"""

from __future__ import annotations

from .contract import (
    AnalysisBackend,
    BackendDescriptor,
    MeasurementEnvelope,
    MeasureRequest,
    OwnedProfile,
    ProfileRequest,
    RankRequest,
    RankResult,
    assert_envelope_owned,
    require_capability,
)
from .errors import (
    BackendContractError,
    BackendMismatch,
    CacheNamespaceCollision,
    CapabilityNotDeclared,
    NoProfileYet,
    SchemaMismatch,
)
from .registry import AnalysisBackendRegistry, iter_backends, register, registry

__all__ = [
    "AnalysisBackend",
    "AnalysisBackendRegistry",
    "BackendContractError",
    "BackendDescriptor",
    "BackendMismatch",
    "CacheNamespaceCollision",
    "CapabilityNotDeclared",
    "MeasureRequest",
    "MeasurementEnvelope",
    "NoProfileYet",
    "OwnedProfile",
    "ProfileRequest",
    "RankRequest",
    "RankResult",
    "SchemaMismatch",
    "assert_envelope_owned",
    "iter_backends",
    "register",
    "registry",
    "require_capability",
]
