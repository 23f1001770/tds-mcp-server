import os
import hashlib
from contextvars import ContextVar

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

EMAIL = "23f1001770@ds.study.iitm.ac.in"
challenge_var = ContextVar("exam_challenge", default="")

mcp = FastMCP(
    "TDS Challenge Server",
    stateless_http=True,
    json_response=True,
)

@mcp.tool()
def solve_challenge() -> str:
    """Hash the challenge received in the HTTP request headers."""
    challenge = challenge_var.get()
    if len(challenge) != 32:
        raise ValueError("Missing or invalid X-Exam-Challenge header")
    return hashlib.sha256(
        f"{challenge}:{EMAIL}".encode("utf-8")
    ).hexdigest()[:16]


class HeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        challenge = headers.get(
            b"x-exam-challenge", b""
        ).decode("ascii")
        token = challenge_var.set(challenge)
        try:
            await self.app(scope, receive, send)
        finally:
            challenge_var.reset(token)


app = HeaderMiddleware(
    mcp.streamable_http_app(
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )
    )
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
