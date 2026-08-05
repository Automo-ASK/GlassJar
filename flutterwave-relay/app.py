import os

import httpx
from flask import Flask, Response, request

app = Flask(__name__)

RELAY_SECRET = os.environ["RELAY_SECRET"]
FLW_BASE = "https://api.flutterwave.com/v3"
FORWARD_HEADERS = {"authorization", "content-type", "accept"}


@app.route("/health")
def health():
    return {"ok": True}


@app.route(
    "/proxy/<path:subpath>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
def proxy(subpath):
    if request.headers.get("X-Relay-Auth") != RELAY_SECRET:
        return {"error": "unauthorized"}, 401

    upstream_headers = {
        k: v for k, v in request.headers.items() if k.lower() in FORWARD_HEADERS
    }

    with httpx.Client(timeout=30.0) as client:
        r = client.request(
            method=request.method,
            url=f"{FLW_BASE}/{subpath}",
            headers=upstream_headers,
            content=request.get_data(),
            params=request.args,
        )

    return Response(
        r.content,
        status=r.status_code,
        mimetype=r.headers.get("content-type", "application/json"),
    )
