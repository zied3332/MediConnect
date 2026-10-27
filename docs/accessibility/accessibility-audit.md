# Rendered browser accessibility audit

## Environment and conditions

27 October 2026, Africa/Lagos. Windows, Django 6.1.2, headless Chrome 156.0.8078.48,
Playwright, axe-core 4.14.0 and Lighthouse 13.5.0. JSON timestamps are UTC.
Base URL: http://127.0.0.1:8765. Desktop viewport: 1280 × 900 CSS pixels.
Reduced motion was requested for axe and keyboard checks. Lighthouse used desktop emulation.
External assets were requested normally; availability can affect reproducibility.

config.accessibility_settings uses isolated SQLite and synthetic fixtures. Real authenticated
browser cookies were issued through Django's backend. Protected routes were accepted only
after HTTP 200 and a matching final pathname. This demonstrates authenticated rendering,
not successful password login or complete role-permission coverage.

## Axe results

All **24 final route conditions loaded with zero detected axe violations**. Axe does not
provide a percentage score here. The full passes, violations, incomplete and inapplicable
arrays remain in reports/final/<page>-axe.json. Enabled tags: wcag2a, wcag2aa, wcag21aa,
wcag22aa and best-practice.

<!-- ROUTES -->

| Page condition | Role | Exact route | Loaded | Violations | Incomplete groups |
|---|---|---|---|---|---|
| home | public | / | loaded | 0 | 1 |
| login | public | /accounts/login/ | loaded | 0 | 1 |
| patient-registration | public | /accounts/signup/ | loaded | 0 | 0 |
| doctor-registration | public | /accounts/doctor/signup/ | loaded | 0 | 1 |
| doctor-search | public | /?q=Audit | loaded | 0 | 1 |
| patient-dashboard | patient | /dashboard/patient/ | loaded | 0 | 1 |
| medical-record | patient | /medical-records/my/ | loaded | 0 | 0 |
| prescriptions | patient | /medical-records/prescriptions/ | loaded | 0 | 0 |
| examinations | patient | /medical-records/patients/1/examinations/ | loaded | 0 | 0 |
| booking | patient | /appointments/book/ | loaded | 0 | 0 |
| booking-slots | patient | /appointments/book/doctor/2/ | loaded | 0 | 0 |
| doctor-dashboard | doctor | /dashboard/doctor/ | loaded | 0 | 1 |
| patients | doctor | /dashboard/doctor/patients/ | loaded | 0 | 0 |
| availability | doctor | /dashboard/doctor/availability/ | loaded | 0 | 0 |
| consultations | doctor | /consultations/ | loaded | 0 | 1 |
| admin-dashboard | admin | /dashboard/admin/ | loaded | 0 | 0 |
| users | admin | /dashboard/admin/users/ | loaded | 0 | 1 |
| specialties | admin | /dashboard/admin/specialties/ | loaded | 0 | 2 |
| record-management | admin | /medical-records/management/records/ | loaded | 0 | 0 |
| profile | patient | /dashboard/profile/ | loaded | 0 | 0 |
| doctor-appointments | doctor | /appointments/doctor/?tab=past | loaded | 0 | 0 |
| patient-brief | doctor | /consultations/1/fiche/ | loaded | 0 | 1 |
| doctor-appointments-past | doctor | /appointments/doctor/?when=past | loaded | 0 | 0 |
| examination-management | admin | /medical-records/management/examinations/ | loaded | 0 | 0 |

<!-- END ROUTES -->

The public /?q=Audit page displays the existing notice that discovery results are not connected.
It is the rendered search-submission state, **not a working doctor-results page**.
The authenticated booking selector and slots were audited separately.
The doctor ?tab=past parameter is unrecognized and leaves the default empty upcoming view;
the populated additional condition uses ?when=past. Baseline covered 23 conditions.

## Lighthouse

<!-- LIGHTHOUSE -->

| Page | Route | Score / 100 | Final URL |
|---|---|---|---|
| home | / | 100 | http://127.0.0.1:8765/ |
| login | /accounts/login/ | 100 | http://127.0.0.1:8765/accounts/login/ |
| patient-dashboard | /dashboard/patient/ | 100 | http://127.0.0.1:8765/dashboard/patient/ |
| doctor-dashboard | /dashboard/doctor/ | 100 | http://127.0.0.1:8765/dashboard/doctor/ |
| admin-dashboard | /dashboard/admin/ | 100 | http://127.0.0.1:8765/dashboard/admin/ |

<!-- END LIGHTHOUSE -->

Before fixes: Home 96, Login 100, patient dashboard 100, doctor dashboard 100, admin dashboard
94. All five final pages score 100 with correct final URLs and no runtime errors or run warnings.
JSON and HTML reports are retained in baseline and final directories.

The first chrome-launcher connection failed; reports/baseline/lighthouse-launcher-failures.json
retains those errors. Playwright remote debugging resolved it. A transient Windows report-write
failure for examination management was rerun successfully; the merged final summary contains
that successful observation. The server was restarted after template edits and audits repeated.

## Confirmed defects and fixes

| Original browser failure | Root cause | Minimal fix | Recheck |
|---|---|---|---|
| Home steps: #a88727 on white, 3.40:1 | Small low-contrast gold text | Darken to #6b5720 | 6.98:1; axe clean; Lighthouse 100 |
| Admin quick-overview Review: #c6a83c on white, 2.31:1 | Inline low-contrast gold | Accessible gold variable | 6.98:1; axe clean; Lighthouse 100 |
| Empty doctor appointment table: scrollable-region-focusable | No focusable content inside overflow region | Named region with tabindex=0 | Axe clean; Tab and ArrowRight scroll at 320px |
| Home root width 1513px at doubled text in 1280px viewport | Nonwrapping navigation and fixed height | Permit wrapping; use minimum height | Final root width 1280px; screenshot reviewed |
| Users root width 711px at 320px | Absolute hidden row labels escaped scroll container | Position role forms relatively | Final width 320px; keyboard reaches scrolled specialty action |

Original axe node/color evidence, responsive measurements and screenshots are retained.
Five application files changed. Browser regression assertions cover loaded routes, violations,
Lighthouse URLs/scores, keyboard outcomes and responsive document widths.

## Incomplete checks and limitations

<!-- INCOMPLETE -->

| Page | Rule needing review | Nodes |
|---|---|---|
| home | color-contrast | 2 |
| login | color-contrast | 1 |
| doctor-registration | color-contrast | 1 |
| doctor-search | color-contrast | 3 |
| patient-dashboard | color-contrast | 4 |
| doctor-dashboard | color-contrast | 1 |
| consultations | color-contrast | 2 |
| users | color-contrast | 1 |
| specialties | aria-prohibited-attr | 1 |
| specialties | color-contrast | 1 |
| patient-brief | color-contrast | 1 |

<!-- END INCOMPLETE -->

Incomplete groups are **not passes**; inspect their node-level evidence in each axe JSON.
All final pages have one main, one h1, a title and a language attribute. These support semantic
structure without proving every relationship, heading's quality or alternative text's meaning.
No screen reader was used. No complete WCAG conformance or final grade is claimed.
See the separate reports for gradient, zoom, camera, AI and manual-review limitations.

## Regression validation

- Django system check: no issues.
- Full Django suite: **305 passed**, 165.702 seconds, isolated SQLite settings.
- JavaScript behavior suite: **50 passed**, zero failed.
- Browser verifier: 24 axe conditions, 5 Lighthouse pages, 12 keyboard workflows and 40 width checks pass.
- Python compilation, JavaScript syntax checks and Git whitespace checks pass.
- Native PostgreSQL regression execution was not repeated.

Transcripts: reports/django-tests.txt and reports/javascript-tests.txt.
Machine-readable validation: reports/validation.json.

## Git provenance

Infrastructure commit 233bb4f inadvertently landed on Stage 4 after sandbox permissions blocked
initial branch creation. Stage 5 was then created at that commit. No history was rewritten.
Fix commit: e550c82. Browser regression commit: cb10a4a. The evidence commit is recorded in Git history.
No push or merge was performed. Unrelated schema-export files were not edited or staged.
