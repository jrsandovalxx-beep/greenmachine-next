# GMN-000A — completed record

- Reviewed SHA: `3d5e4fde3d6065fad1078749c85eb61b96fde9de`
- Verdict date: 2026-07-28
- ticket text: pre-plan bootstrap (D-027); reviewed under Regime A per D-028a

```VERDICT
# APPROVED WITH NOTES

**Verdict applies only to SHA:** `3d5e4fde3d6065fad1078749c85eb61b96fde9de`

The revision-binding deficiency from the prior review is cured. The supplement provides:

- branch: `main`;
- verbatim `git rev-parse HEAD`;
- a clean working-tree result;
- the complete, untruncated initial-commit diff.

## Acceptance determination

**REASONING — All thirteen GMN-000A acceptance criteria are met.**

The full diff independently confirms that the revision contains exactly the four permitted files:

- `.gitattributes`;
- `.gitignore`;
- `LICENSE`;
- `README.md`.

It also confirms:

- `.gitattributes` uses the active rule `* text eol=lf`, not a bare active `* text=auto`;
- binary extensions and `evidence/**` / `data/**` are excluded from conversion;
- `.gitignore` covers Python artifacts, virtual environments, Streamlit secrets, editors, operating-system files and common credential files;
- the license is genuinely proprietary rather than a placeholder;
- the README contains no local paths, credentials, odds, probabilities or automated betting recommendation language.

Combined with the original build report, the evidence establishes that:

- all six destructive operations were rejected;
- both force-push tests used genuinely divergent refs, proven by `1 1` left-right counts and `[ahead 1, behind 1]`;
- feature-branch work remained permitted;
- the fresh Windows clone reproduced the committed bytes under `core.autocrlf=true`;
- the repository returned to exactly `main` and `staging`;
- `main` retained exactly the reviewed initial commit.

## Judgment calls

### Zero required GitHub approvals

**REASONING — Approved for the documented solo-owner configuration.**

Requiring one approval would deadlock a solo repository because the pull-request author cannot satisfy their own required approval. Requiring a pull request with zero GitHub approvals still prevents direct protected-branch updates.

This configuration does not encode GPT review inside GitHub. Independent review remains a separate governance requirement.

### `main` deletion evidence

**REASONING — Adequate.**

The exact required deletion command was rejected. The builder accurately disclosed that GitHub's default-branch guard caused the rejection before branch protection was consulted.

The configured `allow_deletions:false` value is shown for `main`, the identical configuration was applied to `staging`, and the protection rule itself was directly exercised by the rejected `staging` deletion. Temporarily changing the default branch to force the second mechanism to fire was unnecessary and would have introduced avoidable configuration risk.

## Required release note

**UNVERIFIABLE — Branch protection remains point-in-time evidence.**

The reviewed SHA immutably identifies the four repository files. It does **not** bind GitHub branch-protection settings, which can be changed independently of Git history.

The report demonstrates that protection existed and operated during the tests on **July 27, 2026, approximately 20:53–20:55 UTC**. Current protection status cannot be established from that historical output alone.

Protection evidence is repository configuration, not commit content. It must be re-captured immediately before any production merge. Any missing or weakened protection at that time blocks the merge unless separately ruled under the project's governance process.

No further GMN-000A evidence is required for the reviewed SHA.
```
