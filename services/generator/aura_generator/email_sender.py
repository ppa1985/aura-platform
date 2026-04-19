"""Email delivery. Console backend for dev; SMTP hook left as a TODO."""

from __future__ import annotations

import logging

from .config import settings

log = logging.getLogger("aura.email")


def send_verification_code(to_email: str, code: str) -> None:
    if settings.email_backend == "console":
        # Loud log line so the dev can read it out of `uvicorn` output.
        log.warning(
            "\n========================================\n"
            "  AURA: verification code for %s\n"
            "  CODE: %s\n"
            "========================================",
            to_email,
            code,
        )
        return
    raise NotImplementedError(f"email backend not implemented: {settings.email_backend}")
