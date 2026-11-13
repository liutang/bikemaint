# UI Contract: 020 Categorised Palette and Free Placement

Extends `specs/004-bike-builder` and `specs/005-unified-bike-screen` (superseded for placement and palette).

## Palette markup (`app/templates/partials/builder.html`)

```html
<section class="side-section" aria-labelledby="palette-heading">
  <h2 id="palette-heading">Add a new part</h2>
  <details class="palette-category">            <!-- one per category; never `open` on load -->
    <summary>Brakes</summary>
    <ul class="side-list palette">
      <li class="side-item" draggable="true" data-source="palette" data-type="brake_cable">… Brake Cable …</li>
    </ul>
  </details>
  …
</section>
```

- Five `details.palette-category`, in the order Accessories, Brakes, Drivetrain, Frame, Wheels; parts in the order of `data-model.md`.
- Every palette part appears on every bike and part screen.
- The "Add to…" form inside a part lists every placement target in scope (the bike and every part, no filtering).

## Drop targets

- Every `.drop-target` accepts every part type. `data-accepts` is no longer present or relevant; the script blocks only drops inside the dragged part's own sub-tree.
- The server remains the authority: `POST /builder/add` and `POST /builder/move` re-check type and cycle.

## Routes

No new routes. Behavior changes:

| Route | Change |
|---|---|
| `POST /builder/add` | `component_type` must be an offered kind (34); any `target` is accepted; no "already installed there" or "can be mounted" refusals |
| `POST /builder/move` | Any target accepted except itself or its sub-tree (400/422 with "A component cannot be moved into its own installed sub-tree.") |
| `POST /components`, `POST /components/{id}` | Same relaxation; type choice lists the offered kinds |

## Display

Chips, the part detail page and storage cards show the catalog display name (`kind_name` filter), not the raw type id.
