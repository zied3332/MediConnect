# Computed rendered contrast

27 October 2026. Chromium getComputedStyle supplied colors from the rendered application.
Ancestor solid backgrounds were composited; ratios use WCAG relative luminance.
Thresholds: normal text 4.5:1; large text 3:1; sampled meaningful borders/focus 3:1.
Large text means at least 24px regular or 18.67px bold.
These are samples, not a complete inventory. [Raw selectors and values](reports/final/contrast.json).

<!-- CONTRAST -->

| Element and state | Foreground | Effective background | Ratio | Threshold | Result |
|---|---|---|---|---|---|
| Home step numbers (normal) | rgb(107, 87, 32) | rgb(255, 255, 255) | 6.98:1 | 4.5:1 | pass |
| Home heading (normal) | rgb(48, 48, 48) | rgb(255, 254, 251) | 13.09:1 | 3:1 | not verified |
| Search input text (normal) | rgb(51, 51, 51) | rgb(255, 255, 255) | 12.63:1 | 4.5:1 | pass |
| Search input boundary (normal) | rgb(122, 128, 121) | rgb(255, 255, 255) | 4.05:1 | 3:1 | pass |
| Search button (normal) | rgb(37, 37, 37) | rgb(255, 235, 77) | 12.59:1 | 4.5:1 | pass |
| Search button hover (hover) | rgb(37, 37, 37) | rgb(246, 223, 63) | 11.35:1 | 4.5:1 | pass |
| Login keyboard focus (focus) | rgb(31, 95, 139) | rgb(255, 255, 255) | 6.84:1 | 3:1 | pass |
| Login error text (error) | rgb(161, 45, 45) | rgb(255, 255, 255) | 7.17:1 | 4.5:1 | pass |
| Admin Review link (normal) | rgb(107, 87, 32) | rgb(255, 255, 255) | 6.98:1 | 4.5:1 | pass |
| Booking disabled control (normal) | — | — | — | — | not verified |

<!-- END CONTRAST -->

## Original confirmed failures

| Element | Original foreground | Background | Before | Threshold | After |
|---|---|---|---:|---:|---|
| Home steps 01–03 | #a88727 | #ffffff | 3.40:1 | 4.5:1 | #6b5720, 6.98:1 |
| Admin quick-overview Review | #c6a83c | #ffffff | 2.31:1 | 4.5:1 | #6b5720, 6.98:1 |

Baseline axe nodes identify exact affected elements and pairs.

## Limits

The home heading has a radial-gradient ancestor. The 13.09:1 value is against its underlying
solid color only; the actual worst gradient pixel pair is **not verified**.
Opaque search-form backgrounds cover the gradient, allowing those samples to be evaluated.
Shadows, imagery, all remaining axe incomplete contrast nodes and all component boundaries
need further review. No disabled booking button rendered in this condition: no measurement
or disabled-state pass is asserted. Disabled controls are generally exempt from contrast rules.
Hover and error values apply only to the sampled search button and login error.
Focus area and obscuration are not established solely by contrast ratios.
