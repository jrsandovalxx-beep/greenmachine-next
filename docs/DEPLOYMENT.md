# Deployment — Streamlit Community Cloud staging

Authored in GMR-004 submission 1 (REBUILD_PLAN §GMR-004). Where this document and the
hash-pinned plan disagree, the plan wins and this document is defective. The staging
host is Streamlit Community Cloud (D-024). Submission 2 executes the redeploy and
rollback procedures below **verbatim**; an improvised step is a documentation defect.

## The app

| Item | Value |
|---|---|
| Entrypoint | `streamlit_app.py` (repository root) |
| Requirements | `requirements.txt`, installed automatically by the host (includes the `-e .` self-install, GM-040-HF1 / D-030) |
| Branch tracked by staging | `staging` |
| Fields rendered | name, environment, version, commit — nothing else |

The shell renders no product screen and no score of any kind. It exists to prove the
deployment pipeline end to end.

## How the shell resolves its fields

- **Environment:** the `GM_ENVIRONMENT` configuration value (`staging` / `production`),
  with an explicit `local` fallback when unset. Never inferred.
- **Version:** `importlib.metadata.version("greenmachine")`, with an explicit `unknown`
  fallback when the package is not installed. The `-e .` line in `requirements.txt` is
  what makes this resolve on the host (GM-040-HF1).
- **Commit — git first, so a stale configuration value can never mask a live checkout:**
  1. `git rev-parse --short HEAD` when a git checkout is present — including detached
     HEAD, which is a valid state with a valid SHA and is displayed;
  2. else `GM_COMMIT`, displayed with the explicit provenance marker `abc1234 (env)` so
     a reader can see the value came from configuration, not the checkout;
  3. otherwise the literal `unknown`. Never a crash.

**The secrets bridge.** At startup the shell copies `GM_ENVIRONMENT` and `GM_COMMIT`
from Streamlit secrets into the process environment, **only where the key is absent
from `os.environ`** — the bridge never overwrites an existing value, and the resolution
order above is unchanged by it. **Observed on this host (2026-08-03, GMR-004
submission 2):** Community Cloud already exports root-level secrets as environment
variables — `GM_ENVIRONMENT` was present in `os.environ` before the bridge ran, and the
bridge wrote nothing — so the bridge is a **no-op on this host** for root-level keys.
It stays in place as approved, harmless defense-in-depth for environments where a
secrets source exists but is not exported (for example a local run with a
`.streamlit/secrets.toml`). An earlier revision of this paragraph said Community Cloud
configures apps "not through environment variables"; that premise was wrong and is
corrected here to match observed behaviour.

## App visibility

The staging app is **public**, by deliberate Product Owner choice (2026-08-03), so the
build can be watched. That is acceptable while the shell renders four fields and no
provider data. **Revisit trigger:** the first ticket that puts real provider data on
the page — the ingestion ticket, not the fixtures screen. The repository itself stays
private over provider-data licensing, so visibility is a per-surface decision, never a
default carried forward silently.

## Initial staging deploy (Product Owner, once)

1. On share.streamlit.io: **Create app** (the control's label as observed at the first
   real deploy, 2026-08-03; an earlier revision of this runbook said "New app") →
   repository `jrsandovalxx-beep/greenmachine-next`, branch `staging`, main file path
   `streamlit_app.py`.
2. In the app's **Settings → Secrets**, set:

   ```toml
   GM_ENVIRONMENT = "staging"
   ```

   Secrets live only in the Community Cloud UI. The repository must never contain a
   `secrets.toml` (architecture-enforced: `test_no_secret_shaped_deployment_file_exists`).
3. Deploy, then verify all four fields render and:
   - environment reads exactly `staging`;
   - version reads the installed package version, not `unknown`;
   - commit reads the output of `git rev-parse --short staging`, run against the same
     commit the host deployed.
4. **If the commit field reads `unknown`**, the host exposed no git metadata and the
   `GM_COMMIT` route is the only one available. In that case add to the secrets:

   ```toml
   GM_COMMIT = "<output of git rev-parse --short staging>"
   ```

   and the page must then display `<that value> (env)`, marker included. From that
   point on, **updating `GM_COMMIT` is a mandatory step of every redeploy** (step 2
   of the redeploy procedure), owned by this runbook: staleness there is a documented
   procedural risk, not a claim that it cannot happen.

   **Observed on this host (2026-08-03, GMR-004 submission 2):** the commit field
   resolved through git on the first deploy — `7329f02`, no `(env)` marker — so
   Community Cloud does expose git metadata and this contingency was tested and found
   unnecessary here. This step, and step 2 of the redeploy procedure, remain
   conditional and are currently unused.

## Redeploy (every merge to `staging`)

1. Merge the approved PR into `staging` (merge commit, never squash — D-018). Community
   Cloud redeploys the tracked branch automatically; if the page does not refresh, use
   **Manage app → Reboot**.
2. **Only if the `GM_COMMIT` route is in use** (step 4 above): update `GM_COMMIT` in the
   app's secrets to the new `git rev-parse --short staging` before verifying. Both the
   SHA and the marker must change on the page.
3. Verify the deployed page shows the new commit (and the merged change, when it is
   visible in the shell).

## Rollback (defined objectively — REBUILD_PLAN §GMR-004 criterion 8)

Rollback is a `git revert` PR into `staging`. The branch is protected and history moves
forward; there is no force push and no branch surgery.

1. From updated `staging`: `git revert <SHA of the commit being rolled back>` on a new
   branch (for a merge commit: `git revert -m 1 <merge SHA>`).
2. Open a PR into `staging`; it is reviewed and merged per the lifecycle.
3. Redeploy per the redeploy procedure (including the `GM_COMMIT` step if that route is
   in use).
4. Success means **all three**, shown:
   - (a) `git rev-parse staging^{tree}` equals the prior commit's tree hash — content
     identity, not narrative;
   - (b) the deployed app displays the **new revert commit's** SHA — history moved
     forward;
   - (c) the reverted change's visible marker is gone from the page.

## What never appears on a deployed page

No secret, no private path, no traceback (REBUILD_PLAN §GMR-004 criterion 9). Nothing
from the D-015/D-017 forbidden surface — no outcome language of any kind, no wagering
vocabulary, no score, no tier: the shell renders four fields and nothing else.
