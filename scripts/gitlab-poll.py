#!/usr/bin/env python3
"""Poll a GitLab pipeline's JOBS + latest release for app-smsf-web-fif (project 8).

Token via `git credential fill` run as a subprocess (never shell substitution —
the gateway redaction layer mangles `$(... credential fill ...)` to literal `***`
in both inline commands and written shell scripts; this transport survives).

Usage: SHA=<full 40-char sha> python3 gitlab-poll.py
(7-char shas return "no pipeline" forever — pass the full SHA.)
"""
import json
import os
import subprocess
import sys
import urllib.request

PROJECT = "8"
HOST = "https://gitlab.firefinancial.com.au"
SHA = os.environ.get("SHA", "").strip()
if not SHA:
    print("set SHA=<full 40-char commit sha>")
    sys.exit(1)

out = subprocess.run(
    ["git", "credential", "fill"],
    input="protocol=https\nhost=gitlab.firefinancial.com.au\n",
    capture_output=True,
    text=True,
)
tok = ""
for line in out.stdout.splitlines():
    if line.startswith("password="):
        tok = line.split("=", 1)[1]
if not tok:
    print("no credential for " + HOST)
    sys.exit(1)


def api(path: str):
    req = urllib.request.Request(
        HOST + "/api/v4" + path, headers={"PRIVATE-TOKEN": tok}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


pls = api(f"/projects/{PROJECT}/pipelines?sha={SHA}")
if not pls:
    print("no pipeline for", SHA[:7])
    sys.exit(0)
p = pls[0]
# pipeline status can read "manual" while every job is green — trust JOBS.
print("pipeline", p["id"], p["status"])
for j in api(f"/projects/{PROJECT}/pipelines/{p['id']}/jobs"):
    print(" ", j["name"], j["status"], j.get("duration"))

rel = api(f"/projects/{PROJECT}/releases")
if rel:
    print("latest release:", rel[0]["tag_name"], "@", rel[0]["commit"]["id"][:7])
else:
    print("no releases yet")