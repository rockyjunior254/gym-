# STRAKLY TRAINEE PORTAL — VISUAL REFERENCES & DESIGN SPECIFICATIONS

This document outlines the visual benchmark, component library, and styling rules established for the Trainee Portal, inspired by the **FitPulse** fitness experience.

---

## 1. COLOR HIERARCHY

```css
:root {
  --fp-bg: #F3F3F3;            /* Clean light grey studio canvas */
  --fp-surface: #FFFFFF;       /* Crisp white elevated cards */
  --fp-surface-alt: #FAFAFA;   /* Subtle secondary surfaces */
  --fp-ink: #0D0704;           /* Deep athletic dark ink */
  --fp-muted: #79787E;         /* Medium slate grey for subtitles */
  --fp-lime: #C3E716;          /* Vibrant neon lime highlight */
  --fp-lime-dark: #A6C70E;     /* Darker lime for hover states */
  --fp-coral: #DA281C;         /* Energetic athletic red for alerts & PRs */
  --fp-sand: #E1C8A5;          /* Warm neutral contrast */
  --fp-border: #E8E8E9;        /* Border line separation */
  --fp-border-focus: #0D0704;  /* High contrast focus ring */
}
```

---

## 2. CORE COMPONENT PATTERNS

### Stat Cards
- Rounded corners: `border-radius: 16px;`
- Clean white card background with `border: 1px solid #EAEAEB;`
- Bold numeric metric in `--fp-ink` font-size `1.75rem` to `2.25rem`.
- Lime badge for positive trends (`+12%`, `Target Reached`).

### Action Buttons
- **Primary CTA:** Deep Ink background `#0D0704` with white text, or vibrant Neon Lime `#C3E716` with dark ink text.
- **Secondary CTA:** Transparent background, `1.5px solid #0D0704`, rounded `12px` or pill `9999px`.
- **Destructive / Cancellation:** Coral Red `#DA281C` outline or solid button.

### Circular Target Widget
- SVG circle gauge displaying daily target completion percentage.
- Highlighted with bright lime `#C3E716` progress stroke.

### Table & List Architecture
- Rounded outer containers.
- Light table header with uppercase tracking (`font-size: 0.75rem; font-weight: 700; color: #79787E;`).
- Alternating or clean border-bottom separators.
- Badges: Pill shaped with high contrast text.

---

## 3. STRICT BUSINESS COMPLIANCE
- **Strictly Cash Only:** Store orders, membership renewals, and PT sessions display "Pay physical cash at front desk".
- **Strictly Front Desk Attendance:** Trainee attendance records are marked manually by front desk administrators; trainee view is read-only log & summary.
