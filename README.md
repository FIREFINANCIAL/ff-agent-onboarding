# ff-agent-onboarding

One repo to hand a new AI agent so it can work on the FireFinancial app from day one.

## Why this exists

Every rule and pitfall in this repo was learned by an agent session that lost time (or
nearly lost work) to it. A new agent that reads `AGENTS.md` here starts with all of it.

## Handing an agent the work (Brendan's checklist)

1. **Access:** GitLab account on gitlab.firefinancial.com.au + PAT (read + MR-author only)
   for `fif/app-smsf-api-fif`, `fif/app-smsf-web-fif`, `fif-eks-gitops`.
   No AWS / kubectl / prod-DB / secret access — deliberately.
2. **Clones:** agent makes its OWN clones of the three repos (never shares the
   dev-sandbox clones — concurrent sessions sweep each other's uncommitted work into
   stashes; see AGENTS.md §4).
3. **First instruction:** "Read `AGENTS.md` in this repo, then `CLAUDE.md` /
   `AGENTS.md` in each of the three repos, before touching anything."
4. **Rules of engagement** are already shipped in the repos' CLAUDE.md (MR-only, no agent
   deploys, commit gate, no secrets in repo) — this repo repeats them; the repos enforce.
5. **Verify gates:** unit tests + `tsc --noEmit` / phpunit + Playwright (web) green
   before any MR. Deploys and merge-promotions happen only on Brendan's confirmed word.
6. **Scripts:** `scripts/mr-create-rest.py` (MR creation — push-options silently no-op),
   `scripts/gitlab-poll.py` (pipeline job/release polling). Both resolve tokens at
   runtime via `git credential fill` — no stored credentials in this repo.

## What belongs in new agent sessions' first messages

Point at `AGENTS.md` §1–§2 (topology + non-negotiables) and §5 (verify loops). Add the
task. Everything else it should find here by section number.

## Risk note

The gitops https remote on Brendan's Mac embeds a PAT in `.git/config`. New agents with
read access to that clone technically get the token. Rotation/restriction is Brendan's
call; this repo contains no credentials itself (hosts/IPs withheld — it's public).
