# UI Contract: 073 Builder Drag and Collapse

This extends `specs/004-bike-builder` and `specs/020-free-placement-and-categories/contracts/ui-contract.md`.

## Tree row markup (`partials/builder.html`, `render_nodes`)

A row for a part with sub-parts:

```html
<li class="builder-node">
  <div class="node-row drop-target" draggable="true" data-source="node" data-id="7" ... data-ref="component:7" data-parent-ref="bike:1">
    <button class="twisty" type="button" aria-expanded="true" aria-label="Collapse Front wheel" title="Hide sub-parts">{chevron icon}</button>
    <span class="drag-handle">…</span> {part icon} <a class="node-name">Front wheel</a> <span class="chip">Wheel</span>
    <span class="sub-count">2 parts</span>
    <span class="node-actions">…</span>
  </div>
  <ul class="builder-nodes">…</ul>
</li>
```

- **Without sub-parts**: in place of the button, the row has `<span class="twisty-space" aria-hidden="true"></span>`, and it has no `.sub-count`.
- **The count**: `.sub-count` is hidden unless its `li` has `is-collapsed`. N is `node.descendant_count`, with "1 part" or "N parts".

## Classes the script sets

| Class / element | Where | Meaning |
|---|---|---|
| `is-dragging` | `#builder` and the dragged row or item | A drag is in progress |
| `is-lifted` | dragged `li.builder-node` | Hidden while its gap is shown |
| `li.drop-slot > .slot-row` (`.part-icon`, `.slot-name`, `.slot-where`) | inside a `ul.builder-nodes` | The gap: where the drop lands, and "on <holder>" |
| `is-over` | holder `.node-row`, or `.storage-drop` | The part (or storage) that will receive the drop |
| `is-valid` | `.storage-drop` | Storage accepts this drag |
| `is-collapsed` | `li.builder-node` | Sub-parts hidden (a gap may still show inside) |
| `is-closing` | `li.builder-node` | Sub-parts are mid-collapse; the count already shows |

The script also stores the `bikemaint.collapsed` key in `localStorage`: a JSON array of component ids (strings).

## Requests

These are unchanged. `POST /builder/add` takes `component_type`, `target`, `before_component_id` and `root`. `POST /builder/move` takes `component_id`, `target`, `before_component_id` and `root`. A drop "below the last sibling" sends an empty `before_component_id`.
