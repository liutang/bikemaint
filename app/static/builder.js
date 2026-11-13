(() => {
  "use strict";
  // Drag and drop for the bike builder (specs/004-bike-builder). Progressive enhancement: every
  // action also exists as a plain form, and the server re-validates every request. This script
  // only decides where a drop lands and forwards it to the same endpoints through HTMX.
  let drag = null; // { source, id, type, parentRef, el }

  const builder = () => document.getElementById("builder");
  const targetFor = (ref) =>
    Array.from(builder().querySelectorAll(".drop-target")).find((el) => el.dataset.ref === ref);
  const insideDragged = (el) => drag.source === "node" && drag.el.closest("li").contains(el);

  // Can the dragged part go before `row` (a sibling position under row's parent)?
  function canPlaceBefore(row) {
    if (drag.source === "node" && row.dataset.parentRef === drag.parentRef) return true;
    const parent = targetFor(row.dataset.parentRef);
    return Boolean(parent);
  }

  // Where would a drop on `target` land? null means "not allowed here".
  function resolve(target, event) {
    const ref = target.dataset.ref;
    if (ref === "storage") return drag.source !== "storage" ? { target: "storage", before: "" } : null;
    if (insideDragged(target)) return null;
    if (target.classList.contains("node-row") && target.dataset.id !== drag.id) {
      const box = target.getBoundingClientRect();
      if (event.clientY - box.top < box.height * 0.3 && canPlaceBefore(target)) {
        return { target: target.dataset.parentRef, before: target.dataset.id };
      }
    }
    if (drag.source === "node" && ref === drag.parentRef) return { target: ref, before: "" };
    return { target: ref, before: "" };
  }

  function markTargets() {
    builder().classList.add("is-dragging");
    builder().querySelectorAll(".drop-target").forEach((el) => {
      const reorderable =
        el.classList.contains("node-row") && el.dataset.id !== drag.id && !insideDragged(el) && canPlaceBefore(el);
      const valid = resolve(el, { clientY: Infinity }) !== null || reorderable;
      el.classList.toggle("is-valid", valid);
      el.classList.toggle("is-invalid", !valid);
    });
  }

  function clear() {
    const root = builder();
    if (!root) return;
    root.classList.remove("is-dragging");
    root.querySelectorAll(".is-valid, .is-invalid, .is-over").forEach((el) =>
      el.classList.remove("is-valid", "is-invalid", "is-over"));
    root.querySelectorAll(".is-dragging").forEach((el) => el.classList.remove("is-dragging"));
  }

  function send(drop) {
    if (!window.htmx) return;
    const isNew = drag.source === "palette";
    const values = isNew
      ? { component_type: drag.type, target: drop.target, before_component_id: drop.before }
      : { component_id: drag.id, target: drop.target, before_component_id: drop.before };
    const path = isNew ? "/add" : "/move";
    values.root = builder().dataset.root;
    htmx.ajax("POST", `/builder${path}`, { target: "#builder", swap: "outerHTML", values });
  }

  document.addEventListener("dragstart", (event) => {
    const item = event.target.closest && event.target.closest("#builder [draggable='true']");
    if (!item) return;
    drag = { source: item.dataset.source, id: item.dataset.id || null, type: item.dataset.type,
             parentRef: item.dataset.parentRef || null, el: item };
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", item.dataset.type || "");
    item.classList.add("is-dragging");
    markTargets();
  });

  document.addEventListener("dragover", (event) => {
    const target = drag && event.target.closest && event.target.closest("#builder .drop-target");
    if (!target) return;
    const ok = resolve(target, event) !== null;
    event.dataTransfer.dropEffect = ok ? "move" : "none";
    builder().querySelectorAll(".is-over").forEach((el) => el.classList.remove("is-over"));
    if (ok) {
      event.preventDefault();
      target.classList.add("is-over");
    }
  });

  document.addEventListener("drop", (event) => {
    const target = drag && event.target.closest && event.target.closest("#builder .drop-target");
    if (!target) return;
    const drop = resolve(target, event);
    event.preventDefault();
    if (drop) send(drop);
    clear();
    drag = null;
  });

  document.addEventListener("dragend", () => { clear(); drag = null; });

  // The builder is swapped whole after every action, which would close the palette sections the
  // rider opened (specs/033 FR-006). Remember which were open before the swap, reopen them after.
  let openSections = null;
  const sections = (root) => Array.from(root.querySelectorAll("details.palette-category"));
  document.body.addEventListener("htmx:beforeSwap", (event) => {
    const { target } = event.detail;
    if (target && target.id === "builder") openSections = sections(target).map((el) => el.open);
  });
  document.body.addEventListener("htmx:afterSwap", () => {
    const root = builder();
    if (openSections && root) {
      sections(root).forEach((el, i) => { el.open = Boolean(openSections[i]); });
    }
    openSections = null;
  });

  // A refused action comes back as a 422 carrying the whole builder plus the reason.
  document.body.addEventListener("htmx:beforeSwap", (event) => {
    const { xhr, target } = event.detail;
    if (xhr && xhr.status === 422 && target && target.id === "builder") {
      event.detail.shouldSwap = true;
      event.detail.isError = false;
    }
  });
})();
