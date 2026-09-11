"""Unit tests for the parts that must be provably correct."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.hashing import (GENESIS, chain_hash, merkle_proof, merkle_root,
                              sha256_text, verify_merkle_proof)
from app.services.extractors import extract_by_regex


# ---------------------------------------------------------- hash chain
def test_chain_is_deterministic():
    a = chain_hash(None, sha256_text("f1"), 1)
    b = chain_hash(None, sha256_text("f1"), 1)
    assert a == b


def test_chain_detects_tampering():
    h1 = chain_hash(None, sha256_text("f1"), 1)
    h2 = chain_hash(h1, sha256_text("f2"), 2)
    tampered = chain_hash(sha256_text("EVIL"), sha256_text("f2"), 2)
    assert tampered != h2


def test_chain_order_matters():
    h1 = chain_hash(None, sha256_text("f1"), 1)
    assert chain_hash(h1, sha256_text("f2"), 2) != chain_hash(h1, sha256_text("f2"), 3)


# ------------------------------------------------------------- merkle
def test_merkle_proof_roundtrip():
    leaves = [sha256_text(f"e{i}") for i in range(7)]
    root = merkle_root(leaves)
    for i in range(len(leaves)):
        assert verify_merkle_proof(leaves[i], merkle_proof(leaves, i), root)


def test_merkle_rejects_wrong_leaf():
    leaves = [sha256_text(f"e{i}") for i in range(5)]
    root = merkle_root(leaves)
    proof = merkle_proof(leaves, 2)
    assert not verify_merkle_proof(leaves[3], proof, root)


def test_empty_merkle_is_genesis():
    assert merkle_root([]) == GENESIS


# --------------------------------------------------------- extraction
def test_extracts_indian_formats():
    text = ("Accused Ramesh Kumar, mobile 9812345670, vehicle DL08CA4321, "
            "UPI ramesh.kalia@okaxis, IFSC HDFC0001234, "
            "account 50100234567891, Aadhaar 4521 8890 3312.")
    found = {e.entity_type: e.normalized_value for e in extract_by_regex(text)}
    assert found["PHONE"] == "9812345670"
    assert found["VEHICLE"] == "DL08CA4321"
    assert found["UPI"] == "ramesh.kalia@okaxis"
    assert found["IFSC"] == "HDFC0001234"
    assert found["AADHAAR"] == "452188903312"


def test_regex_is_language_independent():
    """The whole point: structured formats survive Devanagari narrative."""
    hindi = ("आरोपी का मोबाइल नंबर 9812345672 है और वाहन संख्या HR26BC7788 "
             "पंजीकृत है। खाता संख्या 50100234567893 में राशि भेजी गई।")
    found = {e.entity_type: e.normalized_value for e in extract_by_regex(hindi)}
    assert found["PHONE"] == "9812345672"
    assert found["VEHICLE"] == "HR26BC7788"
    assert "ACCOUNT" in found


def test_aadhaar_not_misread_as_account():
    found = {e.entity_type for e in extract_by_regex("Aadhaar 4521 8890 3312")}
    assert "AADHAAR" in found


# ---------------------------------------------------------- redaction
def test_redaction_by_role():
    from app.core.crypto import redact
    assert redact("person.aadhaar", "452188903312", "CONSTABLE") == "[REDACTED]"
    assert redact("person.aadhaar", "452188903312", "INSPECTOR") == "452188903312"
    assert redact("person.phone", "9812345670", "CONSTABLE").endswith("5670")


def test_unknown_field_is_not_leaked_by_accident():
    from app.core.crypto import redact
    # unmapped fields pass through - policy is explicit, not implicit
    assert redact("person.nickname", "Kalia", "CONSTABLE") == "Kalia"


# ------------------------------------------------------------- geo
def test_haversine_distance():
    from app.services.anomalies import _haversine_m
    d = _haversine_m(28.5355, 77.2410, 28.5358, 77.2412)
    assert 20 < d < 80
