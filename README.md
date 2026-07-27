# greenmachine-next

GreenMachine Next is an MLB home-run evaluation and research platform.

It does not produce wagers, stakes, picks, or automated betting recommendations.

## Status

Bootstrap in progress (GMN-000A). This repository contains no application code yet;
the package skeleton, CI, and context files arrive in later bootstrap tickets.

## Branches

- `main` — production. Protected: changes arrive only by pull request.
- `staging` — Product Owner testing. Protected: changes arrive only by pull request.
- `feature/*` — implementation branches, created from `staging`.

## Line endings

Text files are committed and checked out with LF line endings on every platform;
see `.gitattributes`. Binary files and evidence paths are exempt from all text
conversion. This project ships digest-pinned evidence, so a default checkout must
reproduce the committed bytes exactly.
