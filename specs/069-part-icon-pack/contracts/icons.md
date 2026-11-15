# Part icons (specs/069)

Each kind's drawing on a 24x24 grid, as rendered by `partials/icons.html` `part()`. Style: `line` stroke 2, `thin` stroke 1.25, `solid-N` filled with an N-unit edge. `rim` and `spoke` show `wheel`; unknown kinds show `other`.

| Kind | Style | Markup |
|---|---|---|
| `accessories` | line | `<path d="M10 2.5h4M10.5 2.5v3L9 8.5V20a1.5 1.5 0 0 0 1.5 1.5h3A1.5 1.5 0 0 0 15 20V8.5l-1.5-3v-3"/><path d="M9 12.5h6M9 16h6"/>` |
| `apparel` | line | `<path d="M8.5 3 3 6l2 4.5 2.5-1V21h9V9.5l2.5 1L21 6l-5.5-3a3.5 3.5 0 0 1-7 0z"/><path d="M12 6.5v6"/>` |
| `computer` | line | `<rect x="6" y="2.5" width="12" height="15" rx="3"/><path d="M9 7h6M9 10.5h4"/><path d="M12 17.5v3M9 21h6"/>` |
| `lights` | line | `<path d="M3 8h5.5a4 4 0 0 1 0 8H3z"/><path d="M15.5 8.5 21 6.5M15.5 12H21M15.5 15.5l5.5 2"/>` |
| `brake` | line | `<circle cx="10" cy="13" r="8"/><circle cx="10" cy="13" r="2.6" fill="currentColor" stroke="none"/><rect x="14" y="2.5" width="7.5" height="9.5" rx="2" fill="currentColor"/>` |
| `brake_cable` | line | `<path d="M3 2.5c0 8 9 4 9 12"/><circle cx="16.5" cy="17.5" r="4.5"/><circle cx="16.5" cy="17.5" r="1"/>` |
| `brake_lever` | line | `<g transform="translate(2 1)"><path fill="currentColor" d="M3 6.8C3 5.4 4 4.6 5.5 4.6L11.5 4.3C12.5 3.5 13.3 2.4 14.3 2 15.6 1.5 16.6 2.3 16.4 3.7L16.1 6.4C16 7.6 15.1 8.3 14 8.5L5.2 9.1C3.9 9.2 3 8.3 3 6.8Z"/><path d="M14.6 8.6C15.6 12.5 15 17 12.2 21.5"/></g>` |
| `pad` | line | `<path d="M3 12.5A2.5 2.5 0 0 1 5.5 10H9V5.5a3 3 0 0 1 6 0V10h3.5a2.5 2.5 0 0 1 2.5 2.5v5a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z"/><circle cx="12" cy="5.5" r=".3"/>` |
| `rotor` | line | `<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="6" stroke-dasharray="1.6 2.1"/><circle cx="12" cy="12" r="2"/>` |
| `bottom_bracket` | line | `<rect x="6" y="9" width="12" height="6" rx="1"/><path d="M3.5 7.5v9M20.5 7.5v9M3.5 12H6M18 12h2.5"/>` |
| `cassette` | line | `<path d="M4.5 3.5v17M8.25 5v14M12 6.5v11M15.75 8v8M19.5 9.5v5"/>` |
| `chain` | line | `<rect x="2" y="8" width="12" height="8" rx="4"/><rect x="10" y="8" width="12" height="8" rx="4"/><circle cx="6" cy="12" r=".6"/><circle cx="18" cy="12" r=".6"/>` |
| `chainrings` | solid-0.5 | `<path d="M12.00 3.80L14.47 1.18L15.56 4.61L18.92 3.32L18.41 6.89L22.00 7.18L19.99 10.18L23.10 12.00L19.99 13.82L22.00 16.82L18.41 17.11L18.92 20.68L15.56 19.39L14.47 22.82L12.00 20.20L9.53 22.82L8.44 19.39L5.08 20.68L5.59 17.11L2.00 16.82L4.01 13.82L0.90 12.00L4.01 10.18L2.00 7.18L5.59 6.89L5.08 3.32L8.44 4.61L9.53 1.18ZM5.60 12.00A6.4 6.4 0 1 0 18.40 12.00A6.4 6.4 0 1 0 5.60 12.00ZM14.29 15.89A1.6 1.6 0 1 1 17.49 15.89A1.6 1.6 0 1 1 14.29 15.89ZM15.29 15.89A0.6 0.6 0 1 0 16.49 15.89A0.6 0.6 0 1 0 15.29 15.89ZM6.51 15.89A1.6 1.6 0 1 1 9.71 15.89A1.6 1.6 0 1 1 6.51 15.89ZM7.51 15.89A0.6 0.6 0 1 0 8.71 15.89A0.6 0.6 0 1 0 7.51 15.89ZM6.51 8.11A1.6 1.6 0 1 1 9.71 8.11A1.6 1.6 0 1 1 6.51 8.11ZM7.51 8.11A0.6 0.6 0 1 0 8.71 8.11A0.6 0.6 0 1 0 7.51 8.11ZM14.29 8.11A1.6 1.6 0 1 1 17.49 8.11A1.6 1.6 0 1 1 14.29 8.11ZM15.29 8.11A0.6 0.6 0 1 0 16.49 8.11A0.6 0.6 0 1 0 15.29 8.11Z"/>` |
| `crankset` | line | `<circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="1"/><path d="M16.2 16.2 20 20M7.8 7.8 4 4"/>` |
| `derailleur` | solid-0.7 | `<path d="M4.29 3.59A2.5 2.5 0 1 1 9.29 3.59A2.5 2.5 0 1 1 4.29 3.59ZM10.65 9.35L7.18 5.89L9.09 3.98L12.55 7.45ZM10.50 6.40L15.00 4.60L17.00 9.00L17.50 12.40L12.50 11.20L10.50 10.00ZM14.80 7.20A3.6 3.6 0 1 1 22.00 7.20A3.6 3.6 0 1 1 14.80 7.20ZM16.40 10.60L19.00 12.00L13.80 17.40L11.60 15.60ZM8.80 18.60A3.4 3.4 0 1 1 15.60 18.60A3.4 3.4 0 1 1 8.80 18.60ZM10.90 18.60A1.3 1.3 0 1 0 13.50 18.60A1.3 1.3 0 1 0 10.90 18.60ZM17.10 7.20A1.3 1.3 0 1 0 19.70 7.20A1.3 1.3 0 1 0 17.10 7.20ZM5.69 3.59A1.1 1.1 0 1 0 7.89 3.59A1.1 1.1 0 1 0 5.69 3.59Z"/>` |
| `drivetrain` | thin | `<path d="M6.1 7.0L15.3 5.8A6.3 6.3 0 1 1 15.3 18.2L6.1 17.0A5 5 0 0 1 6.1 7.0z"/><circle cx="6.8" cy="12" r="3"/><circle cx="16.2" cy="12" r="4.3"/>` |
| `pedal` | line | `<path d="M2 12h3"/><rect x="5" y="5" width="15" height="14" rx="2.5"/><circle cx="8.5" cy="8.5" r=".5"/><circle cx="16.5" cy="8.5" r=".5"/><circle cx="8.5" cy="15.5" r=".5"/><circle cx="16.5" cy="15.5" r=".5"/><path d="M5 12h15"/>` |
| `shifter` | solid-1 | `<path d="M1 12.8H3.6L4.6 11.4 4.3 7.2Q7.6 5.3 11.2 5.2V3.6H14.2V10.4L19 5.1Q20.6 4.1 20.9 5.8L15.6 12.5 22.4 13Q23.6 13.5 23 14.9L15.1 15.7 14.1 17.9Q13 19.9 11 19.9H8.6Q6.6 19.5 5.1 17.2L3.6 16.2H1Z"/>` |
| `shifter_cable` | line | `<path d="M3 2.5c0 8 9 4 9 12"/><path d="M15 12v9M17.75 13.5v6M20.5 15v3"/>` |
| `fork` | line | `<path d="M12 3v5"/><path d="M8.5 8h7"/><path d="M8.5 8 7 21"/><path d="M15.5 8 17 21"/>` |
| `frame` | line | `<path d="M3 17h8L8.5 6.5 3 17M8.5 6.5H19M11 17l8.3-7.8"/><path d="M19 5.5l.6 4.5M8.5 6.5 8 4"/>` |
| `handlebar` | line | `<path d="M4 6h16"/><path d="M4 6v5a4 4 0 0 0 4 4M20 6v5a4 4 0 0 1-4 4"/><path d="M12 6v3"/>` |
| `handlebar_tape` | line | `<circle cx="9" cy="10" r="6.5"/><circle cx="9" cy="10" r="2.5"/><path d="M15.5 10v8.5a2.5 2.5 0 0 0 2.5 2.5h3"/>` |
| `headset` | line | `<path d="M12 2v20"/><path d="M7 6.5h10M8.5 9.5h7M7 15h10M8.5 18h7"/>` |
| `saddle` | line | `<path d="M12 21.5c-3 0-5-2-5-5 0-3 3-4 3-8V4.5a2 2 0 0 1 4 0V8.5c0 4 3 5 3 8 0 3-2 5-5 5z"/>` |
| `seatpost` | line | `<path d="M5 6c4 1.5 10 1.5 14 0"/><path d="M8.5 9.5h7"/><rect x="10" y="9.5" width="4" height="12" rx="1"/>` |
| `shock` | line | `<circle cx="12" cy="3.5" r="1.5"/><circle cx="12" cy="20.5" r="1.5"/><path d="M12 5v2M12 17v2"/><path d="M8 7h8l-8 2.5h8l-8 2.5h8l-8 2.5h8"/>` |
| `stem` | line | `<rect x="2.5" y="8" width="5" height="11" rx="1.5"/><path d="M7.5 11.5l7-2.5M7.5 15l7.5-2.5"/><circle cx="18" cy="9.5" r="3.5"/>` |
| `axle` | line | `<path d="M5 12h14"/><circle cx="20" cy="12" r="1.5"/><path d="M5 9v6"/><path d="M5 10 2 4"/>` |
| `hub` | line | `<path d="M2 12h20"/><rect x="8" y="9" width="8" height="6" rx="1"/><path d="M6 5.5v13M18 5.5v13"/>` |
| `trainer` | line | `<circle cx="12" cy="9.5" r="6.5"/><circle cx="12" cy="9.5" r="1"/><path d="M5 21l5.5-6M19 21l-5.5-6M3 21h18"/>` |
| `tube` | line | `<circle cx="12" cy="11" r="8"/><circle cx="12" cy="11" r="5.5"/><path d="M12 19v3"/>` |
| `tire` | line | `<circle cx="12" cy="12" r="9.3"/><circle cx="12" cy="12" r="7"/><path d="M12 2.7v2.3M21.3 12H19M12 21.3V19M2.7 12H5"/>` |
| `wheel` | line | `<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="1.5"/><path d="M12 3v7.5M12 13.5V21M3 12h7.5M13.5 12H21M5.6 5.6l5.3 5.3M13.1 13.1l5.3 5.3M18.4 5.6l-5.3 5.3M10.9 13.1l-5.3 5.3"/>` |
| `wheelset` | line | `<circle cx="6.5" cy="12" r="5"/><circle cx="17.5" cy="12" r="5"/><path d="M2.30 12.00L10.70 12.00M3.53 9.03L9.47 14.97M6.50 7.80L6.50 16.20M9.47 9.03L3.53 14.97M13.30 12.00L21.70 12.00M14.53 9.03L20.47 14.97M17.50 7.80L17.50 16.20M20.47 9.03L14.53 14.97" stroke-width="1.2"/>` |
| `bolt` | line | `<path d="M8.5 2.5h7l2 3.5-2 3.5h-7l-2-3.5z"/><path d="M10.5 9.5v12h3v-12M10.5 13h3M10.5 16.5h3"/>` |
| `other` | line | `<path d="M14.5 3.5a5 5 0 0 0-5.3 6.7L3.5 16a2.1 2.1 0 0 0 3 3l5.8-5.7a5 5 0 0 0 6.7-5.3L16 11l-3-1-1-3z"/>` |
