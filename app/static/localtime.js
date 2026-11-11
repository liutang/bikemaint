(() => {
  "use strict";
  // Shows system-recorded UTC timestamps (<time data-local datetime="...Z">) in the viewer's own
  // time zone. Without this script the server-rendered UTC text stays, which is still correct.
  document.querySelectorAll("time[data-local]").forEach((el) => {
    const date = new Date(el.getAttribute("datetime"));
    if (!Number.isNaN(date.getTime())) {
      el.textContent = date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    }
  });
})();
