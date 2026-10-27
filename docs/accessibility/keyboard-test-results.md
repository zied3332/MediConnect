# Real-browser keyboard verification

27 October 2026. Headless Chrome, actual Playwright keyboard events and document.activeElement
observations. These are browser-automated checks, **not human-operated manual testing** or
screen-reader evidence. Initial viewport: 1280 × 900; mobile workflows: 320 × 900.
The tabTo helper navigates with successive Tab presses and never calls focus to bypass navigation.

Each row describes expected behavior and the actual matching observation. Exact focus targets,
rectangles, outline styles and results: [keyboard.json](reports/final/keyboard.json).

<!-- KEYBOARD -->

| Workflow | Role | Route | Expected and actual observation | Result |
|---|---|---|---|---|
| Skip link, forward and reverse Tab | public | / | First Tab reaches skip link; Tab advances; Shift+Tab returns; Enter focuses main. | pass |
| Face login dialog | public | /accounts/login/ | Space opens; close button receives focus; Tab/Shift+Tab stay inside; Escape hides; opener regains focus. | pass |
| Face enrollment dialog | patient | /dashboard/profile/ | Space opens; close button receives focus; Tab/Shift+Tab stay inside; Escape hides; enrollment button regains focus. | pass |
| Availability deletion confirmation | doctor | /dashboard/doctor/availability/ | Space opens confirmation; Cancel receives focus; Tab cycles inside; Escape cancels and restores opener focus. | pass |
| Mobile sidebar | patient | /dashboard/patient/ | At 320px Enter expands; 25 mixed Tab/Shift+Tab events remain inside; Escape restores toggle focus. | pass |
| Login validation | public | /accounts/login/ | Enter submits empty form; rendered alerts contain errors and fields are marked invalid. | pass |
| Examination filtering | patient | /medical-records/patients/1/examinations/ | Typing an unmatched value hides fixture and updates status; focus stays in search; clearing restores item. | pass |
| Consultation pagination | doctor | /consultations/ | Tab reaches next-page link; Enter loads page 2; result count receives focus. | pass |
| Appointment risk tooltip | doctor | /appointments/doctor/?when=past | Tab reaches populated risk badge and reveals tooltip; Escape dismisses. | pass |
| Patient brief panel updates | doctor | /consultations/1/ | Enter loads real brief fragment and expanded state; Space closes; opener regains focus. | pass |
| Scrollable appointment table | doctor | /appointments/doctor/ | Tab reaches named overflow region at 320px; ArrowRight increases scrollLeft; focus-visible is true. | pass |
| Users table actions at 320px | admin | /dashboard/admin/users/ | Tab reaches specialty Save; horizontal container scrolls button into viewport; focus-visible is true. | pass |

<!-- END KEYBOARD -->

## Focus evidence

Computed outlines and focus-visible state are recorded for keyboard targets. The login input's
3px blue outline measures 6.84:1 against white. Dialog screenshots show initial keyboard focus.
Users-table Save action rectangles are inside the 320px viewport after Tab navigation.
This samples focus appearance, rather than proving every indicator remains unobscured everywhere.

## Not verified

- Successful facial recognition, real camera capture/enrollment, permission UI and biometric matching.
  The actual dialog shell and initialization/error state were tested without enrolling a real face.
- External AI generation completion, success polling, publishing and focus after those server updates.
  Real brief-fragment opening and closing were verified.
- Permanent deletion submission: Escape cancellation was tested.
- Successful password login/registration, complete booking submission, every form-error variant,
  nested specialty dialogs, complete focus order and all hover-tooltip persistence cases.
- Screen-reader output, human manual keyboard operation and alternative browser engines.

The first risk-tooltip attempt used ?tab=past and was **not verified**, because it showed no risk
badges. The original failure is retained in keyboard-first-attempt.json. A corrected ?when=past
run used real populated fixture rows and passed. Mocked JavaScript results are not counted here.
