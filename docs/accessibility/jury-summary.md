# University accessibility evidence

27 October 2026. **No final grade is assigned and no WCAG conformance claim is made.**

| Criterion | Maximum | Verified evidence | Remaining limits |
|---|---:|---|---|
| Semantic HTML | 0.5 | 24 loaded conditions have one main, h1, title and language; rendered axe structural checks | Reading order and content relationships need human/screen-reader review |
| ARIA and alternative text | 0.5 | Zero detected axe violations; dialog states, validation and dynamic status/focus observed | Alt-text suitability and announcements not fully verified |
| Contrast and readability | 0.5 | Two failures fixed to 6.98:1; 8 solid-color samples pass; 40 width checks and selected screenshots | Gradient, incomplete nodes, native zoom and full visual review remain open |
| Keyboard navigation | 0.5 | 12 actual browser workflows pass, including dialogs, Escape, pagination and scrolling | Camera/AI completion, complete focus order and other browsers remain open |
| **Total** | **2.0** | Evidence supports evaluation of all four criteria | **Maximum only, not an awarded mark** |

## Suggested demonstration

1. Open final Home and admin-dashboard Lighthouse HTML reports: each scores 100.
   Compare baseline Home 96 and admin 94.
2. Open final summary.json and a full axe JSON: show loaded route, zero violations and separately
   retained incomplete checks.
3. Compare baseline/final Users 320px screenshots and Home step colors with measured values.
4. Show keyboard JSON focus targets and dialog screenshots; reproduce Tab, Shift+Tab, Enter,
   Space, Escape and ArrowRight in the isolated local application.
5. Show 305 Django and 50 JavaScript regression tests. Unit tests support regressions but
   do not substitute for browser evidence.

Five confirmed defects were fixed. All 24 final axe conditions have zero detected violations;
all five Lighthouse pages score 100; twelve keyboard workflows and forty width checks pass.

Public doctor discovery remains a placeholder. Server observations also recorded a 404 for
/static/js/home.js; AI/classic search-mode interaction success is not claimed.
Real biometric recognition, external AI generation/publishing, screen readers, native zoom,
alternative browser engines, complete manual review and PostgreSQL regressions remain unverified.
Axe incomplete checks are explicitly retained.

See [audit](accessibility-audit.md), [keyboard](keyboard-test-results.md),
[contrast](contrast-results.md) and [responsive](responsive-results.md).
