"""Evidence integrity: SHA-256 hash chain + Merkle tree.

This is TRINETRA's blockchain-equivalent. Append-only, tamper-evident,
independently verifiable - without running a distributed ledger.
"""
import hashlib
from typing import Sequence

GENESIS = "0" * 64


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chain_hash(prev_chain_hash: str | None, file_sha256: str, sequence_number: int) -> str:
    """Link this evidence record to the one before it.

    Changing any past record breaks every hash after it.
    """
    prev = prev_chain_hash or GENESIS
    return sha256_text(f"{prev}|{file_sha256}|{sequence_number}")


def merkle_root(leaf_hashes: Sequence[str]) -> str:
    """Build a Merkle root so a single record can be proven without
    re-verifying the entire chain."""
    if not leaf_hashes:
        return GENESIS
    level = list(leaf_hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])  # duplicate last node for odd counts
        level = [
            sha256_text(level[i] + level[i + 1]) for i in range(0, len(level), 2)
        ]
    return level[0]


def merkle_proof(leaf_hashes: Sequence[str], index: int) -> list[dict]:
    """Sibling path proving leaf_hashes[index] belongs to the root."""
    proof: list[dict] = []
    level = list(leaf_hashes)
    idx = index
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        sibling = idx + 1 if idx % 2 == 0 else idx - 1
        proof.append({"hash": level[sibling], "position": "right" if idx % 2 == 0 else "left"})
        level = [sha256_text(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        idx //= 2
    return proof


def verify_merkle_proof(leaf: str, proof: list[dict], root: str) -> bool:
    computed = leaf
    for step in proof:
        if step["position"] == "right":
            computed = sha256_text(computed + step["hash"])
        else:
            computed = sha256_text(step["hash"] + computed)
    return computed == root
