# 0005 Python gate tools and build backend

Date: 2026-11-14. Decided by: coordinator under decision 0002, item 1, recorded in step 0C
part 1.

## Decision

The Python gate tools and the build backend are accepted under decision 0002, item 1 (standard,
established packages, pinned at exact versions). Versions equal the pins in `pyproject.toml`.

| Package | Version | Released | Licence | Licence read from |
| :--- | :--- | :--- | :--- | :--- |
| pytest-cov | 7.1.0 | 2026-03-21 | MIT | `LICENSE` in the installed distribution |
| hypothesis | 6.169.2 | 2026-10-14 | MPL-2.0 | `LICENSE.txt` in the installed distribution |
| complexipy | 8.0.1 | 2026-09-07 | MIT | `LICENSE` in the installed distribution |
| bandit | 1.9.4 | 2026-02-25 | Apache-2.0 | `LICENSE` in the installed distribution |
| pip-audit | 2.10.1 | 2026-06-10 | Apache-2.0 | `LICENSE` in the installed distribution |
| hatchling | 1.32.4 | 2026-09-20 | MIT | `LICENSE.txt` in the PyPI wheel (not installed here) |

Release dates are the upload dates PyPI reports for each version. Hatchling 1.33.0 (2026-10-28)
is under 30 days old on this date, so 1.32.4 is pinned (decision 0002, item 1).

## Runtime pins

`pypdf` 6.21.2 (uploaded 2026-10-21) is under 30 days old on 2026-11-14. The pin stands because
it is the version in the target environment table in `CLAUDE.md`, which the work PC carries.
Decision 0002, item 1 lets the work PC adapt the version if it cannot install it. `github-copilot-sdk`
1.0.8 (2026-07-22) is over 30 days old. Neither is imported yet.

## Duplication gate

The Python duplication gate reuses the `jscpd` pinned in `web/` (decision 0001, 5.4.1). The
Python gates therefore need `npm ci` in `web/` first.

## Not verified

- Transitive packages and their ages were not read; `pip-audit` in the gates is the only check
  on them.
- Licences of `pypdf` and `github-copilot-sdk` were not read from licence files; PyPI metadata
  reports BSD-3-Clause and MIT.
