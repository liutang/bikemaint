(() => {
  "use strict";
  // Drag and drop for the parts builder (specs/004, 073). Progressive enhancement: every action
  // also exists as a plain form, and the server re-validates every request. While dragging, the
  // part lifts out and a gap opens exactly where it would land; rows glide to make room.
  //   top 30% of a row: above it | bottom 30% of a row with no shown sub-parts: below it
  //   otherwise: inside it (first sub-part when its sub-parts show, else last)
  const ZONE = 0.3;
  const STICK = 0.12; // the pointer must move this much past a zone's edge before the gap moves
  const KEY = "bikemaint.collapsed";
  let drag = null; // { source, id, type, parentRef, el, li }
  let drop = null; // { key, target, before, place() }
  let slot = null;
  let holder = null; // a temporary list made to hold the gap under a part with none
  let spring = null;

  const builder = () => document.getElementById("builder");
  const locked = () => builder() && builder().hasAttribute("data-locked");
  const rowFor = (ref) => Array.from(builder().querySelectorAll(".node-row")).find((el) => el.dataset.ref === ref);
  const skip = (li) => li === slot || (drag && li === drag.li);
  const subList = (li) => li.querySelector(":scope > ul.builder-nodes");
  const isCollapsed = (li) => li.classList.contains("is-collapsed");
  const childItems = (li) => (subList(li) ? Array.from(subList(li).children).filter((c) => !skip(c)) : []);
  const idOf = (li) => li.querySelector(":scope > .node-row").dataset.id;
  const nextItem = (li) => {
    let n = li.nextElementSibling;
    while (n && skip(n)) n = n.nextElementSibling;
    return n;
  };
  const listIn = (el) => {
    let ul = subList(el);
    if (!ul) {
      ul = holder = document.createElement("ul");
      ul.className = "builder-nodes";
      el.appendChild(ul);
    }
    return ul;
  };

  function loadCollapsed() {
    try { return new Set(JSON.parse(localStorage.getItem(KEY) || "[]")); } catch (e) { return new Set(); }
  }
  function saveCollapsed(set) {
    try { localStorage.setItem(KEY, JSON.stringify([...set])); } catch (e) { /* this view only */ }
  }

  function makeSlot() {
    const li = document.createElement("li");
    li.className = "drop-slot";
    const row = document.createElement("div");
    row.className = "slot-row";
    const icon = drag.el.querySelector(".part-icon");
    if (icon) row.appendChild(icon.cloneNode(true));
    const name = drag.el.querySelector(".node-name, .side-name");
    for (const [cls, text] of [["slot-name", name ? name.textContent.trim().replace(/\s+/g, " ") : ""], ["slot-where", ""]]) {
      const span = document.createElement("span");
      span.className = cls;
      span.textContent = text;
      row.appendChild(span);
    }
    const sample = builder().querySelector(".node-row");
    if (sample) row.style.minHeight = `${sample.offsetHeight}px`; // rows move by exactly one row
    li.appendChild(row);
    return li;
  }

  // Rows glide instead of jumping (FLIP). It follows the rider's own hand, so it stays on with
  // Reduce Motion (short and small; specs/073 research §3).
  const moving = () => builder().querySelectorAll(".builder-root .node-row, .drop-slot .slot-row");
  function snapshot() {
    const seen = new Map();
    moving().forEach((el) => { if (el.offsetParent) seen.set(el, el.getBoundingClientRect()); });
    return seen;
  }
  function glide(seen) {
    if (typeof Element.prototype.animate !== "function") return;
    moving().forEach((el) => {
      if (!el.offsetParent) return;
      el.getAnimations().forEach((a) => a.cancel());
      const now = el.getBoundingClientRect();
      const was = seen.get(el);
      if (!was) {
        el.animate([{ opacity: 0, transform: "scaleY(0.4)" }, { opacity: 1, transform: "none" }], { duration: 160, easing: "ease-out" });
        return;
      }
      const dx = was.left - now.left;
      const dy = was.top - now.top;
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
      el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }],
                 { duration: 200, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" });
    });
  }
  // Where a row really sits, ignoring the glide it may be in the middle of.
  function settledBox(row) {
    const box = row.getBoundingClientRect();
    const t = getComputedStyle(row).transform;
    return { top: box.top - (t && t !== "none" ? new DOMMatrixReadOnly(t).m42 : 0), height: box.height };
  }

  function forRow(row, event) {
    const box = settledBox(row);
    const y = (event.clientY - box.top) / box.height;
    const li = row.parentElement;
    const id = row.dataset.id;
    const current = drop && drop.key.slice(1) === id ? drop.key[0] : "";
    const top = ZONE + (current === "b" ? STICK : current === "i" ? -STICK : 0);
    const bottom = 1 - ZONE - (current === "a" ? STICK : current === "i" ? -STICK : 0);
    if (y < top) return { key: `b${id}`, target: row.dataset.parentRef, before: id, place: () => li.before(slot) };
    const kids = isCollapsed(li) ? [] : childItems(li); // a collapsed part takes the gap alone
    if (kids.length) {
      return { key: `i${id}`, target: row.dataset.ref, before: idOf(kids[0]), place: () => kids[0].before(slot) };
    }
    if (y > bottom) {
      const next = nextItem(li);
      return { key: `a${id}`, target: row.dataset.parentRef, before: next ? idOf(next) : "", place: () => li.after(slot) };
    }
    return { key: `i${id}`, target: row.dataset.ref, before: "", place: () => listIn(li).appendChild(slot) };
  }

  function holderName(ref) {
    const row = rowFor(ref);
    if (row) return row.querySelector(".node-name").textContent.trim();
    return builder().dataset.root.startsWith("bike:") ? "the bike" : "this part";
  }

  function unplace() {
    if (slot) slot.remove();
    if (holder && !holder.children.length) holder.remove();
    holder = null;
    builder().querySelectorAll(".is-over").forEach((el) => el.classList.remove("is-over"));
  }

  function show(next) {
    const seen = snapshot();
    unplace();
    drop = next;
    if (next && next.target === "storage") {
      builder().querySelector(".storage-drop").classList.add("is-over");
    } else if (next) {
      next.place();
      slot.querySelector(".slot-where").textContent = `on ${holderName(next.target)}`;
      const parent = rowFor(next.target);
      if (parent) parent.classList.add("is-over");
    }
    glide(seen);
  }

  // Hovering inside a collapsed part for a moment opens it; the gap becomes its first sub-part.
  function springOpen(next) {
    clearTimeout(spring);
    const row = next.key[0] === "i" && rowFor(next.target);
    const li = row && row.parentElement;
    if (!li || !isCollapsed(li)) return;
    spring = setTimeout(() => {
      if (!drag || !drop || drop.key !== next.key) return;
      const seen = snapshot();
      slot.remove();
      setCollapsed(li, false, false);
      const kids = childItems(li);
      if (kids.length) drop = { key: next.key, target: next.target, before: idOf(kids[0]), place: () => kids[0].before(slot) };
      drop.place();
      glide(seen);
    }, 700);
  }

  function finish() {
    clearTimeout(spring);
    const root = builder();
    if (root) {
      unplace();
      root.classList.remove("is-dragging");
      root.querySelectorAll(".is-valid, .is-dragging, .is-lifted").forEach((el) =>
        el.classList.remove("is-valid", "is-dragging", "is-lifted"));
    }
    drag = drop = slot = null;
  }

  function send(d, source) {
    if (!window.htmx) return;
    const isNew = source.source === "palette";
    const values = isNew
      ? { component_type: source.type, target: d.target, before_component_id: d.before }
      : { component_id: source.id, target: d.target, before_component_id: d.before };
    values.root = builder().dataset.root;
    htmx.ajax("POST", `/builder${isNew ? "/add" : "/move"}`, { target: "#builder", swap: "outerHTML", values });
  }

  document.addEventListener("dragstart", (event) => {
    const item = event.target.closest && event.target.closest("#builder [draggable='true']");
    if (!item) return;
    drag = { source: item.dataset.source, id: item.dataset.id || null, type: item.dataset.type,
             parentRef: item.dataset.parentRef || null, el: item,
             li: item.dataset.source === "node" ? item.parentElement : null };
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", item.dataset.type || "");
    item.classList.add("is-dragging");
    slot = makeSlot();
    builder().classList.add("is-dragging");
    if (drag.source !== "storage") builder().querySelector(".storage-drop").classList.add("is-valid");
    // Lift the part after the browser has taken its drag picture; its gap opens in its place.
    requestAnimationFrame(() => {
      if (!drag || !drag.li || locked()) return;
      const next = nextItem(drag.li);
      show({ key: "start", target: drag.parentRef, before: next ? idOf(next) : "",
             place: () => { drag.li.classList.add("is-lifted"); drag.li.before(slot); } });
    });
  });

  document.addEventListener("dragover", (event) => {
    if (!drag || !event.target.closest || !builder() || !builder().contains(event.target)) return;
    const t = event.target;
    let next;
    if (locked() && !t.closest(".storage-drop")) {
      return; // specs/079: an archived screen only takes parts off to storage
    } else if (t.closest(".drop-slot")) {
      next = drop;
    } else if (t.closest(".storage-drop")) {
      next = drag.source !== "storage" ? { key: "storage", target: "storage", before: "" } : null;
    } else if (t.closest(".node-row")) {
      next = forRow(t.closest(".node-row"), event);
    } else if (t.closest(".builder-root")) {
      const area = t.closest(".builder-root");
      const ul = subList(area);
      const below = !ul || event.clientY > ul.getBoundingClientRect().bottom;
      // Below every row: last at the top level. Gaps between rows keep the current gap.
      next = below ? { key: "end", target: area.dataset.ref, before: "", place: () => listIn(area).appendChild(slot) } : drop;
    } else {
      return;
    }
    if (!next) {
      event.dataTransfer.dropEffect = "none";
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    if (!drop || next.key !== drop.key) {
      show(next);
      springOpen(next);
    }
  });

  document.addEventListener("drop", (event) => {
    if (!drag || !event.target.closest || !builder().contains(event.target)) return;
    event.preventDefault();
    const d = drop;
    const source = drag;
    if (d && d.target !== "storage") {
      // Dropping into a collapsed part opens it, so the placed part stays in view.
      const set = loadCollapsed();
      const parent = rowFor(d.target);
      if (parent && set.delete(parent.dataset.id)) saveCollapsed(set);
      // Leave the part where it was dropped until the server's answer replaces the tree.
      if (source.li && slot.isConnected) {
        slot.replaceWith(source.li);
        slot = null;
      }
    }
    finish();
    if (d) send(d, source);
  });

  document.addEventListener("dragend", () => { if (drag) finish(); });

  // ---------- Collapsible parts (specs/073 US2) ----------
  function setCollapsed(li, collapse, animate) {
    const row = li.querySelector(":scope > .node-row");
    const btn = row.querySelector(":scope > .twisty");
    const ul = subList(li);
    if (!btn || !ul) return;
    const name = row.querySelector(".node-name").textContent.trim();
    btn.setAttribute("aria-expanded", String(!collapse));
    btn.setAttribute("aria-label", `${collapse ? "Expand" : "Collapse"} ${name}`);
    btn.title = collapse ? "Show sub-parts" : "Hide sub-parts";
    const set = loadCollapsed();
    if (collapse) set.add(row.dataset.id); else set.delete(row.dataset.id);
    saveCollapsed(set);
    ul.getAnimations().forEach((a) => a.cancel());
    if (!animate || typeof ul.animate !== "function") {
      li.classList.toggle("is-collapsed", collapse);
      return;
    }
    if (!collapse) li.classList.remove("is-collapsed");
    const h = ul.offsetHeight;
    const frames = [{ height: "0px", opacity: 0 }, { height: `${h}px`, opacity: 1 }];
    if (collapse) frames.reverse();
    ul.style.overflow = "hidden";
    li.classList.toggle("is-closing", collapse);
    ul.animate(frames, { duration: 190, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" }).onfinish = () => {
      ul.style.overflow = "";
      li.classList.remove("is-closing");
      if (collapse) li.classList.add("is-collapsed");
    };
  }

  function applyCollapsed() {
    const root = builder();
    if (!root) return;
    const set = loadCollapsed();
    root.querySelectorAll(".builder-root .node-row").forEach((row) => {
      if (set.has(row.dataset.id)) setCollapsed(row.parentElement, true, false);
    });
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest && event.target.closest("#builder .twisty");
    if (!btn) return;
    const li = btn.closest("li.builder-node");
    setCollapsed(li, !isCollapsed(li), true);
  });

  applyCollapsed();

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
    applyCollapsed();
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
