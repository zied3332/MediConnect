# MediConnect Stage 5 accessibility evidence

Audit date: **27 October 2026**, Africa/Lagos (UTC+1). Synthetic local data only.

- [Browser audit and exact routes](accessibility-audit.md)
- [Keyboard observations](keyboard-test-results.md)
- [Computed contrast](contrast-results.md)
- [Responsive observations](responsive-results.md)
- [University rubric summary](jury-summary.md)
- [Baseline reports](reports/baseline/) and [final reports](reports/final/)
- [Baseline screenshots](screenshots/baseline/) and [final screenshots](screenshots/final/)

Automated passes and scores are limited observations, not WCAG conformance.

## Reproduce

From the repository root, use the project's existing Python environment. In PowerShell:

    $env:DJANGO_SETTINGS_MODULE = 'config.accessibility_settings'
    python manage.py migrate --noinput
    python -m scripts.accessibility_seed
    python manage.py runserver 127.0.0.1:8765 --noreload

The settings replace PostgreSQL with an isolated .audit.sqlite3 database and disable external
email and AI credentials. Synthetic patient/doctor/admin sessions are created by Django's
authentication backend. No production credentials or data are needed.

In another terminal:

    npm.cmd install --prefix .audit-tools --cache .audit-npm-cache --no-audit --no-fund --ignore-scripts axe-core@4.14.0 lighthouse@13.5.0
    $env:AUDIT_RUN = 'final'
    node scripts/accessibility_audit.cjs
    node scripts/accessibility_lighthouse.cjs
    node scripts/accessibility_keyboard.cjs
    node scripts/accessibility_contrast.cjs
    node scripts/accessibility_verify.cjs
    python scripts/accessibility_document.py
    $env:DJANGO_SETTINGS_MODULE = 'config.accessibility_settings'
    python manage.py check
    python manage.py test --keepdb -v 1
    node --test static/js/tests/*.test.cjs
    git diff --check

The runners reused an existing Playwright package from the local Python installation.
Set PLAYWRIGHT_PACKAGE to an absolute path to an existing Playwright Node package on another
machine. Chrome was already installed; no browser download was required. Runners use the
Windows Chrome path in their source; the axe runner also accepts CHROME_PATH.

Restart the --noreload server after template edits to clear its template cache. Finish each
browser run before restarting. AUDIT_RUN=baseline writes another baseline; preserve checked-in
evidence when reproducing. AUDIT_PAGE reruns a single named axe page and merges its summary.

Local .audit-* runtime files, tool downloads and synthetic session cookies are ignored.
Lighthouse reports redact session values. The examination fixture references a placeholder
file; upload/download success was not tested.
