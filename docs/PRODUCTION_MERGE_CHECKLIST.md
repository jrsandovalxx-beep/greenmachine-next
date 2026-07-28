# Production merge checklist

Run by the Product Owner immediately before any merge into `main` (authored fresh in
GMR-001, implementation criterion 1c). Every line is demonstrated with output captured
at merge time — not asserted from history. Nobody else in the chain can make these
checks at the moment they matter.

1. **Both approvals exist.** GPT's implementation verdict names the approved head SHA,
   and the Product Owner approves the release (D-011, D-018). Neither alone suffices.
2. **Ancestry, not equality.** The approved SHA is an ancestor of the branch being
   merged:

   ```bash
   git merge-base --is-ancestor <approved-SHA> <branch>
   ```

   Exit code 0 is the pass. Merge commits move the head, so head equality is the wrong
   check; ancestry is the binding that survives them (D-018).
3. **Branch protection re-captured now.** Protection evidence is point-in-time (GMN-000A
   verdict): re-run `gh api` for the protection of both `main` and `staging` and compare
   against the approved configuration — pull requests required, `enforce_admins` on,
   force pushes disallowed, deletions disallowed. Missing or weakened protection blocks
   the merge unless separately ruled in writing under D-020.
4. **Merge commit, never squash.** A squash merge creates a new SHA and breaks the
   approval binding; the reviewed SHA must remain an ancestor of the merge commit
   (D-018).
5. **Checker clean at the merge point.** `python scripts/check_consistency.py` on the
   branch being merged, output captured.
