"""Cryptographic envelope for the simulated onion-routed network.

This module is the single implementation of the wire format defined in
``AgentsDocs/RELAY_PROTOCOL.md`` sections 2, 5.2 and 7.  The client seals layers
with it and the relays open layers with it, so the two can never disagree about
the format (SD-008).

Every primitive comes from the ``cryptography`` package.  Nothing here
implements a cipher, a hash or a key exchange by hand -- see
``AgentsDocs/MASTER_CONTEXT.md`` section 5 rule 2.

Primitives, per RELAY_PROTOCOL.md section 2:

    per-hop key delivery     RSA-OAEP, 2048-bit, SHA-256
    layer payload encryption AES-GCM, 256-bit key, 96-bit nonce
    serialization            JSON -> UTF-8 bytes -> base64 on the wire
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# RELAY_PROTOCOL.md section 2.
RSA_KEY_BITS = 2048
RSA_PUBLIC_EXPONENT = 65537
AES_KEY_BYTES = 32  # 256-bit
NONCE_BYTES = 12  # 96-bit

# The sentinel that tells a relay it is the exit hop (RELAY_PROTOCOL.md 5.1).
DESTINATION = "DESTINATION"


class EnvelopeError(Exception):
    """A layer or response envelope could not be opened.

    Raised for malformed structure, a bad base64 field, a failed RSA unwrap and
    a failed AES-GCM tag check alike.  Callers must not distinguish between
    those cases when reporting outwards: RELAY_PROTOCOL.md section 9 says a
    decryption failure is logged and dropped, not diagnosed to the sender.
    """


# --------------------------------------------------------------------------
# Key handling (RELAY_PROTOCOL.md section 3)
# --------------------------------------------------------------------------


def generate_relay_keypair() -> tuple[rsa.RSAPrivateKey, str]:
    """Generate a relay's in-memory RSA-2048 keypair.

    Returns the private key object and the PEM encoding of the *public* half.
    The private key is never serialised by this module: section 3 requires that
    it stay in memory, off disk, out of git and out of every payload.
    """
    private_key = rsa.generate_private_key(
        public_exponent=RSA_PUBLIC_EXPONENT, key_size=RSA_KEY_BITS
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return private_key, public_pem


def load_public_key(public_pem: str) -> rsa.RSAPublicKey:
    """Parse a PEM public key, rejecting anything that is not one.

    A PEM block carrying a private key is refused outright rather than parsed.
    DIRECTORY_SPEC.md section 2 requires the directory to reject such a
    registration and treat it as a bug in the relay.
    """
    if "PRIVATE KEY" in public_pem:
        raise EnvelopeError("refusing to load a PEM block containing a private key")
    try:
        key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any parse failure is the same answer
        raise EnvelopeError("not a valid PEM public key") from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise EnvelopeError("public key is not RSA")
    return key


def _oaep_padding() -> padding.OAEP:
    """RSA-OAEP with SHA-256, as section 2 specifies for both MGF1 and the digest."""
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    )


# --------------------------------------------------------------------------
# Session material
# --------------------------------------------------------------------------


def new_session_key() -> bytes:
    """A fresh 256-bit AES key -- ``K`` in RELAY_PROTOCOL.md section 5.2."""
    return os.urandom(AES_KEY_BYTES)


def new_nonce() -> bytes:
    """A fresh 96-bit nonce.

    Section 7: "Never reuse a nonce with the same key. Generate a fresh nonce
    for every encryption operation, forward and return."  Every call site in
    this repository calls this function rather than reusing a value.
    """
    return os.urandom(NONCE_BYTES)


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: Any, field: str) -> bytes:
    if not isinstance(text, str):
        raise EnvelopeError(f"field {field!r} is missing or not a string")
    try:
        return base64.b64decode(text, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise EnvelopeError(f"field {field!r} is not valid base64") from exc


# --------------------------------------------------------------------------
# Forward direction: layers (RELAY_PROTOCOL.md sections 5.1 and 5.2)
# --------------------------------------------------------------------------


def build_layer(next_hop: str, next_host: str, next_port: int, payload: bytes) -> dict:
    """Build one plaintext layer.

    Section 5.1 fixes this object at exactly four fields.  ``payload`` is the
    next encrypted layer, or the raw request bytes when this is the exit hop;
    either way it is base64-encoded here and opaque to the relay that is not
    meant to read it.

    Note there is deliberately no ``request_id`` field -- see SD-003.
    """
    return {
        "next_hop": next_hop,
        "next_host": next_host,
        "next_port": int(next_port),
        "payload": _b64e(payload),
    }


def seal_layer(layer: dict, relay_public_key: rsa.RSAPublicKey) -> dict:
    """Encrypt one layer for one relay.

    Implements section 5.2 exactly::

        K      = random 256-bit AES key
        nonce  = random 96-bit nonce
        ct     = AES-GCM-encrypt(K, nonce, json_bytes(layer))
        enc_K  = RSA-OAEP-encrypt(relay_public_key, K)

    Returns ``(wire_layer, K)``.  The caller keeps ``K`` to open the response
    that comes back through this hop (section 7).

    The hybrid construction is required, not stylistic: section 2 notes that
    RSA-OAEP at 2048 bits can carry only ~190 bytes, which is smaller than a
    layer.
    """
    session_key = new_session_key()
    nonce = new_nonce()
    plaintext = json.dumps(layer, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ciphertext = AESGCM(session_key).encrypt(nonce, plaintext, None)
    enc_key = relay_public_key.encrypt(session_key, _oaep_padding())
    wire = {
        "enc_key": _b64e(enc_key),
        "nonce": _b64e(nonce),
        "ciphertext": _b64e(ciphertext),
    }
    return wire, session_key


def open_layer(wire: Any, private_key: rsa.RSAPrivateKey) -> tuple[dict, bytes]:
    """Decrypt exactly one layer.

    Returns ``(layer, K)``.  This is the whole of a relay's cryptographic
    capability: it unwraps its own layer and gets an opaque ``payload`` it
    cannot read further.  Section 6.
    """
    if not isinstance(wire, dict):
        raise EnvelopeError("wire layer is not a JSON object")

    enc_key = _b64d(wire.get("enc_key"), "enc_key")
    nonce = _b64d(wire.get("nonce"), "nonce")
    ciphertext = _b64d(wire.get("ciphertext"), "ciphertext")

    if len(nonce) != NONCE_BYTES:
        raise EnvelopeError("nonce is not 96 bits")

    try:
        session_key = private_key.decrypt(enc_key, _oaep_padding())
    except Exception as exc:  # noqa: BLE001
        raise EnvelopeError("could not unwrap the session key") from exc

    if len(session_key) != AES_KEY_BYTES:
        raise EnvelopeError("unwrapped session key is not 256 bits")

    try:
        plaintext = AESGCM(session_key).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise EnvelopeError("layer failed authentication") from exc

    try:
        layer = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise EnvelopeError("layer is not valid JSON") from exc

    if not isinstance(layer, dict):
        raise EnvelopeError("layer is not a JSON object")
    for field in ("next_hop", "next_host", "next_port", "payload"):
        if field not in layer:
            raise EnvelopeError(f"layer is missing required field {field!r}")

    return layer, session_key


def layer_payload(layer: dict) -> bytes:
    """Decode a layer's ``payload`` field to bytes."""
    return _b64d(layer.get("payload"), "payload")


# --------------------------------------------------------------------------
# Return direction: response envelopes (SD-002, RELAY_PROTOCOL.md section 7)
# --------------------------------------------------------------------------


def seal_response(inner: bytes, session_key: bytes) -> dict:
    """Wrap one response layer with a relay's retained ``K`` and a fresh nonce.

    ``inner`` is the site's raw response at the exit hop, and the JSON bytes of
    the envelope received from downstream at every other hop.  A relay never
    inspects what it is sealing.

    The envelope carries no ``enc_key``: both ends already hold ``K`` from the
    forward pass, so the RSA step does not repeat (SD-002).
    """
    nonce = new_nonce()
    ciphertext = AESGCM(session_key).encrypt(nonce, inner, None)
    return {"nonce": _b64e(nonce), "ciphertext": _b64e(ciphertext)}


def open_response(wire: Any, session_key: bytes) -> bytes:
    """Unwrap one response layer with the key this hop was sealed under."""
    if not isinstance(wire, dict):
        raise EnvelopeError("response envelope is not a JSON object")

    nonce = _b64d(wire.get("nonce"), "nonce")
    ciphertext = _b64d(wire.get("ciphertext"), "ciphertext")

    if len(nonce) != NONCE_BYTES:
        raise EnvelopeError("nonce is not 96 bits")

    try:
        return AESGCM(session_key).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise EnvelopeError("response layer failed authentication") from exc
