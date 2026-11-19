# UI Contract: 086 Usage Lead Time

| Element | Markup |
|---|---|
| Lead time card | heading "Lead time"; summary "Currently D days, M miles, R rides or H hours, whichever comes first."; `fieldset` "Notify me when a schedule has this much left" with `field`s `notification_lead_time_days` (Days), `lead_miles` (Miles), `lead_rides` (Rides) and `lead_hours` (Hours), in one `.field-row`; auto-save as today |
| Ring, due soon by usage | the value is what's left with its unit (`18 mi`, `1 ride`, `1.5 h`) instead of days; the fill is `1 − left / lead` |
