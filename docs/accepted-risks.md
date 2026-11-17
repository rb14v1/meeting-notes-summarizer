# Accepted dependency risks

This file lists known CRITICAL or HIGH CVEs in this project's dependencies
that have **no fixed version yet**. Any CVE that already has a fix must be
fixed by upgrading the dependency. It must not be listed here.

Check this list on every dependency scan and by each entry's review date at
the latest. When a fix comes out, upgrade the dependency and remove the entry.

| Package | Ecosystem | CVE / Advisory | Severity | Justification | Owner | Review date |
|---------|-----------|----------------|----------|---------------|-------|-------------|
| _none_  | –         | –              | –        | No unfixed CRITICAL/HIGH CVEs are known as of 2026-11-17. | rakesh.r | 2027-02-17 |

## Pinned patched versions

- Backend (`backend/requirements.txt`): `Django>=5.2.11,<5.3` (CVE-2026-1287 and
  other HIGH CVEs fixed in 5.2.11; resolves to the latest 5.2.x patch),
  `djangorestframework==3.16.1`, `djangorestframework-simplejwt==5.5.1`.
- Frontend (`frontend/package.json`): `axios@^1.13.5` (CVE-2026-25639),
  `react-router-dom@^6.30.2` (open-redirect XSS). Transitive versions are
  fixed by `frontend/package-lock.json`, which npm generates.

## Adding an entry

1. Confirm that no patched version exists upstream.
2. Add a row with the advisory ID, severity, why the risk is acceptable
   (for example, the code path is never reached or there is a mitigation in
   place), an owner, and a review date no more than 90 days away.
