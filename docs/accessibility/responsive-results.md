# Responsive accessibility observations

27 October 2026. Ten representative pages × four settings = **40 browser scenarios**.
Screenshots: screenshots/baseline/ and screenshots/final/<page>-<setting>.png.
[Raw widths, control rectangles and table styles](reports/final/responsive.json).

## Methods

- 320px: viewport 320 × 900 CSS pixels, device pixel ratio 1.
- 200percent-text: at 1280 × 900, snapshot each computed font size and set twice its pixel value.
  This simulates isolated text resizing; it does not use native browser font-size UI.
- 400percent-equivalent: 320 CSS-pixel width corresponds to 1280px at 400% zoom.
  Height stays 900px. This is **not native browser zoom** and does not reproduce its magnification,
  browser chrome, pixel rendering or reduced CSS viewport height.
- text-spacing: line-height 1.5, letter-spacing .12em, word-spacing .16em and paragraph bottom
  margin 2em, important overrides at 1280 × 900.

The table reports the measured **document-width check**, not comprehensive usability.
Scrollable table content may extend beyond the viewport without causing document overflow.
The final Users 320px, Home doubled-text and booking-slots 320px screenshots were visually
inspected: Users fits with a local scrolling table; Home navigation wraps without visible overlap;
slot controls form a narrow vertical flow. Long single-line input placeholders truncate naturally.
Other retained screenshots need further human clipping, overlap and readability review.
Full visual accessibility for all 40 scenarios is **not verified**.

<!-- RESPONSIVE -->

| Page | Route | Setting | Viewport width | Document width | Width check |
|---|---|---|---|---|---|
| home | / | 320px | 320 | 320 | pass |
| home | / | 200percent-text | 1280 | 1280 | pass |
| home | / | 400percent-equivalent | 320 | 320 | pass |
| home | / | text-spacing | 1280 | 1280 | pass |
| login | /accounts/login/ | 320px | 320 | 320 | pass |
| login | /accounts/login/ | 200percent-text | 1280 | 1280 | pass |
| login | /accounts/login/ | 400percent-equivalent | 320 | 320 | pass |
| login | /accounts/login/ | text-spacing | 1280 | 1280 | pass |
| patient-registration | /accounts/signup/ | 320px | 320 | 320 | pass |
| patient-registration | /accounts/signup/ | 200percent-text | 1280 | 1280 | pass |
| patient-registration | /accounts/signup/ | 400percent-equivalent | 320 | 320 | pass |
| patient-registration | /accounts/signup/ | text-spacing | 1280 | 1280 | pass |
| doctor-registration | /accounts/doctor/signup/ | 320px | 320 | 320 | pass |
| doctor-registration | /accounts/doctor/signup/ | 200percent-text | 1280 | 1280 | pass |
| doctor-registration | /accounts/doctor/signup/ | 400percent-equivalent | 320 | 320 | pass |
| doctor-registration | /accounts/doctor/signup/ | text-spacing | 1280 | 1280 | pass |
| patient-dashboard | /dashboard/patient/ | 320px | 320 | 320 | pass |
| patient-dashboard | /dashboard/patient/ | 200percent-text | 1280 | 1280 | pass |
| patient-dashboard | /dashboard/patient/ | 400percent-equivalent | 320 | 320 | pass |
| patient-dashboard | /dashboard/patient/ | text-spacing | 1280 | 1280 | pass |
| examinations | /medical-records/patients/1/examinations/ | 320px | 320 | 320 | pass |
| examinations | /medical-records/patients/1/examinations/ | 200percent-text | 1280 | 1280 | pass |
| examinations | /medical-records/patients/1/examinations/ | 400percent-equivalent | 320 | 320 | pass |
| examinations | /medical-records/patients/1/examinations/ | text-spacing | 1280 | 1280 | pass |
| booking-slots | /appointments/book/doctor/2/ | 320px | 320 | 320 | pass |
| booking-slots | /appointments/book/doctor/2/ | 200percent-text | 1280 | 1280 | pass |
| booking-slots | /appointments/book/doctor/2/ | 400percent-equivalent | 320 | 320 | pass |
| booking-slots | /appointments/book/doctor/2/ | text-spacing | 1280 | 1280 | pass |
| availability | /dashboard/doctor/availability/ | 320px | 320 | 320 | pass |
| availability | /dashboard/doctor/availability/ | 200percent-text | 1280 | 1280 | pass |
| availability | /dashboard/doctor/availability/ | 400percent-equivalent | 320 | 320 | pass |
| availability | /dashboard/doctor/availability/ | text-spacing | 1280 | 1280 | pass |
| users | /dashboard/admin/users/ | 320px | 320 | 320 | pass |
| users | /dashboard/admin/users/ | 200percent-text | 1280 | 1280 | pass |
| users | /dashboard/admin/users/ | 400percent-equivalent | 320 | 320 | pass |
| users | /dashboard/admin/users/ | text-spacing | 1280 | 1280 | pass |
| record-management | /medical-records/management/records/ | 320px | 320 | 320 | pass |
| record-management | /medical-records/management/records/ | 200percent-text | 1280 | 1280 | pass |
| record-management | /medical-records/management/records/ | 400percent-equivalent | 320 | 320 | pass |
| record-management | /medical-records/management/records/ | text-spacing | 1280 | 1280 | pass |

<!-- END RESPONSIVE -->

## Failures and rechecks

- Home doubled text: document width 1513px in a 1280px viewport. Wrapping navigation fixes it to 1280px.
- Users 320px and zoom-equivalent width: root width 711px. Relative form positioning contains
  hidden table labels and fixes it to 320px, without hiding table content.
- Availability and Users tables keep local overflow-x:auto. Keyboard checks show Users specialty
  Save scrolls into view; the appointment table focuses and scrolls with ArrowRight.

Native text-size UI, native 400% zoom, every table's scrollability, every focus indicator's
obscuration and platform font differences remain unverified.
