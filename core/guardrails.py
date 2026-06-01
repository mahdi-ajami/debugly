import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional

_SENSITIVE_PATTERNS = [
    re.compile(r"(?:sk-[a-zA-Z0-9]{20,})", re.I),
    re.compile(r"(?:ghp_[a-zA-Z0-9]{36,})", re.I),
    re.compile(r"(?:gho_[a-zA-Z0-9]{36,})", re.I),
    re.compile(r"(?:ghu_[a-zA-Z0-9]{36,})", re.I),
    re.compile(r"(?:ghs_[a-zA-Z0-9]{36,})", re.I),
    re.compile(r"(?:ghr_[a-zA-Z0-9]{36,})", re.I),
    re.compile(r"(?:AKIA[0-9A-Z]{16})"),
    re.compile(r"(?:-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)"),
    re.compile(r"(?:Bearer\s+[a-zA-Z0-9\-._~+/]{20,})", re.I),
]

_DANGEROUS_CODE_PATTERNS = [
    re.compile(r"rm\s+-rf\s+(?:/\s*|\$HOME\s*|\~)", re.I),
    re.compile(r"DROP\s+TABLE", re.I),
    re.compile(r"DROP\s+DATABASE", re.I),
    re.compile(r"TRUNCATE\s+TABLE", re.I),
    re.compile(r"shutdown\s+-[a-z]*\s+now", re.I),
    re.compile(r":\(\)\s*\{.*:\|:&\};:", re.I),
]


class GuardrailResult:
    def __init__(self, passed: bool, message: str = "", sanitized: str = ""):
        self.passed = passed
        self.message = message
        self.sanitized = sanitized or ""


class InputGuardrails:
    @staticmethod
    def check_length(text: str, max_chars: int = 8000) -> GuardrailResult:
        if len(text) > max_chars:
            return GuardrailResult(False, f"Input exceeds {max_chars} characters", text[:max_chars])
        return GuardrailResult(True)

    @staticmethod
    def check_sensitive_data(text: str) -> GuardrailResult:
        sanitized = text
        for pat in _SENSITIVE_PATTERNS:
            sanitized = pat.sub("[REDACTED]", sanitized)
        if sanitized != text:
            return GuardrailResult(True, "Sensitive data redacted", sanitized)
        return GuardrailResult(True)

    @staticmethod
    def check_dangerous_code(text: str) -> GuardrailResult:
        for pat in _DANGEROUS_CODE_PATTERNS:
            if pat.search(text):
                return GuardrailResult(False, f"Dangerous code pattern detected: {pat.pattern[:40]}")
        return GuardrailResult(True)


class OutputGuardrails:
    @staticmethod
    def check_sensitive_data(text: str) -> GuardrailResult:
        sanitized = text
        for pat in _SENSITIVE_PATTERNS:
            sanitized = pat.sub("[REDACTED]", sanitized)
        if sanitized != text:
            return GuardrailResult(True, "Sensitive data redacted from output", sanitized)
        return GuardrailResult(True)

    @staticmethod
    def check_dangerous_code(text: str) -> GuardrailResult:
        if "rm -rf" in text and ("/" in text or "$HOME" in text):
            return GuardrailResult(False, "Output blocked: contains dangerous rm -rf command")
        return GuardrailResult(True)
