# ApexSys Cryptographic & Security Specification

This document provides the formal security architecture, cryptographic payload signing specification, replay-attack prevention protocol, and DoD 5220.22-M sanitization standards for ApexSys.

---

## 1. Threat Modeling & Safeguards

Because ApexSys allows low-level remediation on Windows endpoints, security controls are implemented at every layer:

| Threat Vector | Mitigation Mechanism |
| :--- | :--- |
| **Command Injection / Spoofing** | Every execution payload is cryptographically signed with HMAC-SHA256 using a shared or vault-stored secret key (`APEX_SECRET_KEY`). Client agents verify signatures before parsing commands. |
| **Replay Attacks** | Every payload incorporates a cryptographically unique 128-bit hex nonce (`secrets.token_hex(16)`). The receiving agent caches nonces in memory and rejects duplicates. |
| **Clock Drift / Old Payloads** | Strict timestamp validation enforces a 300-second freshness window. Payloads with timestamps outside this range are rejected immediately. |
| **Forensic Trace on Endpoint** | The Zero-Footprint Self-Destruct protocol performs a multi-pass DoD 5220.22-M wipe of all temporary files, followed by out-of-process unlinking. |
| **Session Hijacking** | Agent authorization tokens (`apex_<client_id>_<hash>`) are negotiated upon initial handshake. |

---

## 2. Cryptographic Payload Specification

### 2.1 Payload Structure
When the Commander issues a directive, it wraps the command in a standardized metadata envelope:

```json
{
  "type": "EXECUTE_COMMAND",
  "action": "FIX_ALL",
  "target_client": "PC-HOST-01",
  "params": {},
  "_meta": {
    "timestamp": 1793098932,
    "nonce": "c4b8e21a0f679d38e9a244c01d1678b2",
    "version": "1.0-apex"
  },
  "_signature": "8a74e5f03a67d589e3a0937a4d34f0e972e6bbf4e963dc56f6ba70a5682857bb"
}
```

### 2.2 Canonicalization & Signature Generation
1. Extract all payload fields excluding `_signature`.
2. Format into a deterministic JSON string where keys are alphabetically sorted and whitespace is stripped:
   $$\text{CanonicalString} = \text{JSON.stringify}(\text{payload}, \text{sort\_keys}=\text{True}, \text{separators}=(\text{","}, \text{":"}))$$
3. Compute the HMAC-SHA256 digest:
   $$\text{Signature} = \text{HMAC-SHA256}(K_{\text{secret}}, \text{CanonicalString})$$

### 2.3 Verification Algorithm (Agent Side)
Upon receiving a command, the agent executes:
```python
def verify_payload(payload):
    # 1. Check existence of signature and metadata
    if "_signature" not in payload or "_meta" not in payload:
        return False, "Missing signature"
    
    # 2. Check timestamp skew (|now - ts| <= 300)
    now = time.time()
    ts = payload["_meta"]["timestamp"]
    if abs(now - ts) > 300:
        return False, "Timestamp expired"
        
    # 3. Check replay nonce
    nonce = payload["_meta"]["nonce"]
    if nonce in seen_nonces:
        return False, "Replay attack detected"
        
    # 4. Canonicalize & compare HMAC using constant-time comparison
    expected = compute_hmac(payload_without_signature)
    if not hmac.compare_digest(payload["_signature"], expected):
        return False, "Signature mismatch"
        
    seen_nonces[nonce] = now
    return True, "Valid"
```

---

## 3. Zero-Footprint Sanitization (DoD 5220.22-M)

When the administrator triggers `SELF_DESTRUCT`, or when a scheduled remediation workflow concludes in ephemeral mode, the agent executes `agent/self_destruct.py`:

1. **Pass 1 (Zero-fill)**: The entire file byte range is overwritten with binary zeros (`0x00`), followed by `os.fsync()`.
2. **Pass 2 (One-fill)**: The byte range is overwritten with binary ones (`0xFF`), followed by `os.fsync()`.
3. **Pass 3 (Cryptographic Random)**: The byte range is overwritten with cryptographically strong pseudorandom bytes (`secrets.token_bytes(length)`).
4. **Truncation**: The file size is truncated to 0 bytes via `f.truncate(0)`.
5. **Unlink**: The directory entry is unlinked via `os.remove()`.
6. **Out-of-Process Self-Erase**: A detached transient command (`cmd.exe /c ping 127.0.0.1 -n 2 > nul & del /f /q ... & del %0`) cleans the parent directory after process termination.
