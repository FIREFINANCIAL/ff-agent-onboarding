# AGENTS.md — FireFinancial app: read this before touching anything

You are joining work on the **FireFinancial app** (Next.js client web + Laravel admin API,
shipped to EKS by GitLab CI + Flux). This file is the earned-knowledge pack: topology,
rules, verify loops, and the pitfalls that cost real sessions to learn. It does NOT replace
the per-repo `CLAUDE.md` / `AGENTS.md` files — read those too, they win on any conflict.

## 1. Repos & topology

| Repo (gitlab.firefinancial.com.au) | id | What | Local clone |
|---|---|---|---|
| `fif/app-smsf-api-fif` | 7 | Laravel API (FrankenPHP) | `~/firefinancial/dev-sandbox/smsf-api` |
| `fif/app-smsf-web-fif` | 8 | Next.js web | `~/firefinancial/dev-sandbox/smsf-web` |
| `fif/fif-eks-gitops` | — | Flux deployment manifests | `~/firefinancial/fif-eks-gitops` |

| Tier | URL | Runs on |
|---|---|---|
| prod (client) | `my.firefinancial.com.au` | EKS, branch `master` |
| prod (admin) | `adviser.firefinancial.com.au` | EKS, branch `master` |
| develop (admin) | `adviser-develop.firefinancial.com.au` | EKS, branch `develop` |
| staging (feature gate) | `staging.firefinancial.com.au` | Vultr VPS pm2: web :3101, api :8102 |
| dr / sandbox | :3100 / :3200 on same VPS; `test.firefinancial.ai` = :3200 | own DBs, never touch prod data |

VPS: Vultr box hosting the pm2 tree — host/IP withheld in this public repo; ask Brendan.
`deploy`/`master` on EKS images: client web = `app-smsf-web-fif`, admin = `app-smsf-api-fif`
(+ Filament admin panel inside the api image).

## 2. Non-negotiables (from the repos' CLAUDE.md — enforced by humans)

- **Everything lands via reviewed MR.** Direct pushes to `develop`/`master` are banned —
  no docs-only, one-liner, or urgent exception. Merge only after a human reviewer
  (Brendan or Klyp) approves.
- **The agent does not build or deploy.** Prepare the change → push feature branch →
  open MR → merge after review → trigger the pipeline's manual `deploy-<tier>` job —
  each step only after Brendan confirms that exact action. Images are built by the
  pipeline only, never from a workstation.
- **No secrets, logs, DB dumps, or personal data in any repo.** Git history is never
  rewritten to remove a mistake: fix forward + `.gitignore` guard + rotate the secret.
- **Commit title gate** (husky on web-fif, versioning job on both): titles on shared and
  feature branches must start `feat|fix|perf|breaking|initial|merge` (web-fif even
  rejects docs-only titles on local branches — use `fix(docs):`). Conventional commits,
  imperative, ≤72 chars.
- **Token hygiene:** GitLab tokens resolve at runtime via `git credential fill`
  (host `gitlab.firefinancial.com.au`), run from a **Python script file** — never shell
  `$()` substitution (a gateway redaction layer mangles it to literal `***`). Never print.
  The `.ai`-era GitHub tree is decommissioned (retired 11 Nov 2026) — plans saying
  "port to .ai" are void.

## 3. First setup

1. Clone the two app repos + gitops repo where Brendan says (the paths above are
   Brendan's Mac; make your own clones — see §4).
2. web: `npm install`. api: `docker compose` is the test runtime — see §5.
3. Read `CLAUDE.md` in all three repos, `AGENTS.md` in the web repo.

## 4. Clone safety (real 11-Nov incident)

- **Uncommitted work in a shared clone is NOT safe between your turns.** Another agent
  session may sweep your changes into a stash and checkout its own branch. Tell:
  foreign `git branch --show-current`, foreign `stash@{0}`, someone else's `git status`.
  Recovery: never guess — `git stash list` + `git stash show --name-only stash@{n}`,
  create a worktree (`git worktree add <path> <your-sha>`), `git stash apply stash@{n}`
  inside it (apply, not pop — leaves their stash), commit immediately.
- **Run feature builds in your own worktree, not the shared clone.** Worktree quirks:
  - web: no `node_modules` → symlink the main clone's in, then `npx tsc --noEmit` works.
  - api: no `vendor` → symlink FAILS (absolute autoload paths bake the original checkout
    into it); instead copy `vendor`/`phpunit.xml`/`.env` in and run `composer dump-autoload`
    once inside the container.
- **Sandbox clones sit on a stale local `develop`** (dozens of commits behind). Tell:
  `git diff develop --name-only` shows ~90 unrelated files. Before push: `git fetch origin`
  + rebase your feature branch onto `origin/develop`.
- **Branch-name conventions differ per repo:** api uses `fix/…`, web uses `sandbox/…/
  feat/…` styles — `git branch --list` each clone; don't assume one name across trees.
- **Before branching:** `git stash push -m "stale-tree-mods-pre-<work>"` any pre-existing
  dirt, `git add` explicit paths only, so old dirt can't ride your commit.
- **Report per-repo `(branch, HEAD hash, clean?)` from actual `git status`/`git log`** —
  never report a commit hash that wasn't committed (diff ≠ commit).

## 5. Verify loops (green before MR; tests are Brendan's first question)

**web:**
- `npx vitest run` + `npx tsc --noEmit` for every change.
- Playwright live check: dev server in a background process
  (`npm run dev -- --port 3100`, then `curl -s -o /dev/null -w "%{http_code}" localhost:3100/<route>`,
  run tests in a separate call), `PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test tests/<spec>`.
  Kill it after (`pkill -f "next dev"`). **`:3100` on the shared clone is pm2 prod local —
  for throwaway E2E use your own port; never target pm2 prod.**
- Headless + `next dev` (Turbopack): SSR shell renders but **zero client hydration** —
  green pages.spec proves nothing. For hydrating E2E use `next build && next start --port <own>`.

**api (PHP):**
- In-container: from the dev-sandbox compose dir,
  `docker compose run --rm setup sh -c 'php -d memory_limit=2G vendor/bin/phpunit tests/<File>Test.php'`
  (plain `php artisan test` OOMs or prints help — pass the file path).
- Full-suite failures: isolated-repro = deterministic; in-suite-only = order/throttle
  (429 = rate-limiter env drift; "field is required" = pre-existing validation —
  `git show <sha> -- <file> | grep required` proves your diff adds none).
- **Baseline-clean proof: run suspect specs on a clean checkout (git worktree at the
  parent sha) vs your diff, same server mode.** Dev-vs-standalone copy drift fakes
  regressions ("reset link" vs "6-digit reset code") that are 0.

## 6. Ship loop

1. Feature branch → MR → human review → merge (dev MRs → `develop`).
2. `build` + `versioning` jobs → release tag auto-cuts. Pipeline status may read `manual`
   while **all jobs are green** — trust job states, not pipeline status.
3. After Brendan confirms, trigger `deploy-staging`; verify on
   staging.firefinancial.com.au; **master promotion is a SEPARATE confirmed deploy.**
4. EKS deploys for api: gitops pattern = one-line image-tag bump
   (`flux/apps/master/app-smsf-{web,api}-fif/deployment.yaml`, tag = full commit SHA) →
   commit `fix(smsf-web|api): bump master image to <sha> (<ver> — <why>)` → MR → merge
   after review → Flux rolls (deploy-<tier> job only after Brendan confirms that job).

## 7. Deploy verification (kubectl creds lapse silently — depend on this instead)

**Content-hash chunk roll proof.** Client-visible changes ship in content-hashed
`.next` chunks; identical source → identical chunk names on every build.
1. Your change must add a **runtime string** (JSX class string or UI copy — comments and
   `data-testid`s may be stripped; class strings survive) unique to the changed file.
2. After deploy: `grep -rl "<marker>" .next/static/chunks/` in your checkout.
3. `curl https://my.firefinancial.com.au/_next/static/chunks/<same-name>` (or the tier URL)
   → **200 = Flux roll landed**. 404→200 transition, or a never-seen name appearing, is
   the real signal; unchanged shared chunks 200 regardless and prove nothing.
4. EKS API side: verify via gitops bump commit (Flux Ready) — the kubectl context is the
   cluster ARN, but SSO creds
   silently expire ("must be logged in to the server") — use the chunk probe + gitops
   commit instead of assuming kubectl works.
5. Both sites 200 + `POST /api/statement-n8n` → 401 = alive and auth-guarded.

## 8. GitLab API quirks (each cost ~30 min)

- **`git push -o merge_request.create` silently no-ops.** Create MRs via REST:
  POST `/projects/:id/merge_requests` `{source_branch, target_branch, title,
  description, remove_source_branch: true}` + Bearer token → verify with GET
  `.../merge_requests?source_branch=<b>&state=all`. Use `scripts/mr-create-rest.py`.
- **Merging via API = PUT** `/projects/<pid>/merge_requests/<iid>/merge` with mandatory
  `sha` (head commit). POST → 404; missing sha → 400.
- **`pipelines?sha=` needs the full 40-character SHA** — 7-char returns "no pipeline" forever.
- Pipeline plumbing scripts: `scripts/gitlab-poll.py` (jobs + release poll; token via
  Python subprocess `git credential fill`, zero shell substitution).
- api-fif/web-fif remotes are SSH-form; the gitops https remote URL carries a PAT —
  extract at runtime, never print, never commit it.

## 9. Local-env pitfalls (this estate runs on macOS)

- **`search_files` silently returns 0 matches on `~/firefinancial`** — use `find`/`grep`
  via terminal in that tree.
- **macOS has no `timeout`** — `timeout 45 kubectl …` silently no-ops (empty stdout,
  exit 0). Use your tool's own timeout.
- **Fuzzy patch on dense TSX/PHP:** anchor on a string unique to the target block (a
  runtime label), never a short structural tail (`</div>\n)` matches the wrong block);
  never an old_string ending inside an opening brace. Read the diff hunk after EVERY edit
  + syntax-check the touched file (`php -l` / `tsc --noEmit` / vitest) — 2-call repairs
  beat reverted mangled files. Never `sed` a gitops manifest (a "probe" sed DID rewrite
  deployment.yaml once) — inspect with grep, edit with patch.
- Docker-worktree trap: host-path symlinks dangle inside containers; copied `vendor`
  bakes absolute autoload paths → run `composer dump-autoload` in-container (§5).
- pm2 ports: `pm2 env <id> | grep -i port`, then curl the port literally (the shell's
  `$PORT` is pm2's, not yours).
- Laravel config cache: `.env` edits are silently masked until `php artisan config:clear`
  (and restore the cache after) — any env-gated feature check needs this sequence.

## 10. Not covered here

- Throwaway-account E2E seeding + API shape gotchas (super/bank/profiles): lives in
  Brendan's `ff-app-ops` / `smsf-web-both-trees` skill — ask his Hermes session for the
  recipe, don't guess credentials.
- Product/content conventions: the `smsf-society-codebase` skill on Brendan's Mac.
- Turnstile/E2E automation limits: automation legitimately **cannot** mint CF Turnstile
  tokens (bot-detection by design); armed-gate configs are validated by one real human login.
