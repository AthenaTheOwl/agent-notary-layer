"""notary — reference verifier for the agent-receipt v0.1 schema."""

from notary.canonical import canonicalize, signed_bytes
from notary.verifier import (
    REJECT_CODES,
    ChainBreak,
    ChainNoRoot,
    ChainNotLinear,
    CycleDetected,
    FileKeyResolver,
    KeyMalformed,
    SchemaInvalid,
    SchemaLoadError,
    SignatureInvalid,
    UnknownSigner,
    VerifyError,
    load_schema,
    order_and_check,
    validate,
    verify_receipt,
    verify_signature,
)

__version__ = "0.1.0"

__all__ = [
    "REJECT_CODES",
    "ChainBreak",
    "ChainNoRoot",
    "ChainNotLinear",
    "CycleDetected",
    "FileKeyResolver",
    "KeyMalformed",
    "SchemaInvalid",
    "SchemaLoadError",
    "SignatureInvalid",
    "UnknownSigner",
    "VerifyError",
    "canonicalize",
    "load_schema",
    "order_and_check",
    "signed_bytes",
    "validate",
    "verify_receipt",
    "verify_signature",
]
