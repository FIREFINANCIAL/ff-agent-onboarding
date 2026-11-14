#!/usr/bin/env python3
"""Create GitLab MRs for the fif/* repos via REST (push-options silently no-op).

Token comes from `git credential fill` (never printed). Verifies creation with a
GET -- a silent no-op is the known failure mode, so always confirm.

Usage:
  python3 mr-create-rest.py <project_id> <source_branch> "MR title" <<'EOF'
MR description markdown (stdin)
EOF
"""
import json, subprocess, sys, urllib.request

HOST = "gitlab.firefinancial.com.au"

def resolve_token():
    r = subprocess.run(
        ["git", "credential", "fill"],
        input=f"protocol=https\nhost={HOST}\n\n",
        capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    sys.exit("no gitlab token in git credential store")

def main():
    pid, src_branch, title = sys.argv[1], sys.argv[2], sys.argv[3]
    desc = sys.stdin.read().strip()
    tok = resolve_token()
    body = json.dumps({
        "source_branch": src_branch,
        "target_branch": "develop",
        "title": title,
        "description": desc,
        "remove_source_branch": True,
    }).encode()
    req = urllib.request.Request(
        f"https://{HOST}/api/v4/projects/{pid}/merge_requests",
        data=body,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except Exception as e:
        sys.exit(f"create failed: {e}")
    verify = urllib.request.Request(
        f"https://{HOST}/api/v4/projects/{pid}/merge_requests?source_branch={src_branch}&state=all",
        headers={"Authorization": f"Bearer {tok}"},
    )
    with urllib.request.urlopen(verify, timeout=30) as r:
        found = json.loads(r.read())
    print(json.dumps({
        "iid": d.get("iid"), "state": d.get("state"), "web_url": d.get("web_url"),
        "verified_found": len(found),
    }, indent=1))

if __name__ == "__main__":
    main()
