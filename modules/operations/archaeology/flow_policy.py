"""Versioned, conservative Python source/sink policy for mapper M04.

Rules identify source-code surfaces that *may* read untrusted/sensitive values or cause effects.
They never grant a capability, prove execution, or by themselves prove a vulnerability.
"""

from __future__ import annotations

from typing import Any, Mapping

from .evidence import canonical_bytes, sha256_bytes


FLOW_POLICY_VERSION = "giga.archaeologist.python-flow-policy.v1"

SOURCE_CALLS: Mapping[str, str] = {
    "getpass.getpass": "SECRET_INPUT",
    "input": "UNTRUSTED_STDIN",
    "os.environ.get": "ENVIRONMENT_INPUT",
    "os.getenv": "ENVIRONMENT_INPUT",
    "sys.stdin.read": "UNTRUSTED_STDIN",
    "sys.stdin.readline": "UNTRUSTED_STDIN",
}

SINK_CALLS: Mapping[str, str] = {
    "eval": "DYNAMIC_CODE_EXECUTION",
    "exec": "DYNAMIC_CODE_EXECUTION",
    "httpx.delete": "NETWORK_EGRESS",
    "httpx.get": "NETWORK_EGRESS",
    "httpx.patch": "NETWORK_EGRESS",
    "httpx.post": "NETWORK_EGRESS",
    "httpx.put": "NETWORK_EGRESS",
    "httpx.request": "NETWORK_EGRESS",
    "logging.critical": "OUTPUT_DISCLOSURE",
    "logging.debug": "OUTPUT_DISCLOSURE",
    "logging.error": "OUTPUT_DISCLOSURE",
    "logging.exception": "OUTPUT_DISCLOSURE",
    "logging.info": "OUTPUT_DISCLOSURE",
    "logging.warning": "OUTPUT_DISCLOSURE",
    "os.system": "PROCESS_EXECUTION",
    "print": "OUTPUT_DISCLOSURE",
    "requests.delete": "NETWORK_EGRESS",
    "requests.get": "NETWORK_EGRESS",
    "requests.patch": "NETWORK_EGRESS",
    "requests.post": "NETWORK_EGRESS",
    "requests.put": "NETWORK_EGRESS",
    "requests.request": "NETWORK_EGRESS",
    "subprocess.Popen": "PROCESS_EXECUTION",
    "subprocess.call": "PROCESS_EXECUTION",
    "subprocess.check_call": "PROCESS_EXECUTION",
    "subprocess.check_output": "PROCESS_EXECUTION",
    "subprocess.run": "PROCESS_EXECUTION",
    "urllib.request.urlopen": "NETWORK_EGRESS",
}

POLICY_SHA256 = sha256_bytes(
    canonical_bytes(
        {
            "schema": FLOW_POLICY_VERSION,
            "sources": dict(sorted(SOURCE_CALLS.items())),
            "sinks": dict(sorted(SINK_CALLS.items())),
            "claim": "SOURCE_STATIC_POSSIBLE_FLOW_NOT_EXECUTION_OR_VULNERABILITY",
        }
    )
)


def classify_source(expression: str) -> str | None:
    return SOURCE_CALLS.get(expression)


def classify_sink(
    expression: str, arguments: Mapping[str, Any] | None = None
) -> str | None:
    if expression == "open":
        positional = list((arguments or {}).get("positional", ()))
        mode = positional[1].get("literal") if len(positional) > 1 else None
        if isinstance(mode, str) and any(character in mode for character in "wax+"):
            return "FILESYSTEM_WRITE"
        return None
    return SINK_CALLS.get(expression)
