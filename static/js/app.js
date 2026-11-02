(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Plotly sizes itself when it first draws, which can be before the grid / hidden
  // tab has its real width — so re-measure whenever something becomes visible.
  function resizeCharts(root = document) {
    if (!window.Plotly) return;
    $$(".js-plotly-plot", root).forEach((el) => {
      if (el.offsetParent !== null) Plotly.Plots.resize(el);
    });
  }

  // ── tabs ────────────────────────────────────────────────────
  $$("[data-tabs]").forEach((wrap) => {
    const buttons = $$("[data-tab]", wrap);
    const panels = $$("[data-panel]", wrap);
    if (!buttons.length) return;

    function show(key, remember) {
      if (!panels.some((p) => p.dataset.panel === key)) key = buttons[0].dataset.tab;
      buttons.forEach((b) => b.classList.toggle("is-active", b.dataset.tab === key));
      panels.forEach((p) => (p.hidden = p.dataset.panel !== key));
      if (remember) history.replaceState(null, "", "#" + key);
      requestAnimationFrame(() => resizeCharts(wrap));
    }

    buttons.forEach((b) => b.addEventListener("click", () => show(b.dataset.tab, true)));
    show(location.hash.slice(1) || buttons[0].dataset.tab, false);
  });

  window.addEventListener("load", () => resizeCharts());

  // ── search / filter / sort for entry lists ──────────────────
  $$("[data-filter-scope]").forEach((scope) => {
    const list = $("[data-list]", scope);
    if (!list) return;
    const items = $$("[data-item]", list);
    const controls = $$("[data-filter]", scope);
    const sortSelect = $("[data-sort]", scope);
    const count = $("[data-count]", scope);
    const empty = $("[data-empty]", scope);

    function apply() {
      const search = controls.find((c) => c.dataset.filter === "search");
      const q = ((search && search.value) || "").trim().toLowerCase();
      const selects = controls.filter((c) => c.dataset.filter !== "search");
      let shown = 0;
      items.forEach((item) => {
        let ok = !q || (item.dataset.search || "").includes(q);
        selects.forEach((s) => {
          if (s.value && item.dataset[s.dataset.filter] !== s.value) ok = false;
        });
        item.hidden = !ok;
        if (ok) shown += 1;
      });
      if (count) count.textContent = shown;
      if (empty) empty.hidden = shown !== 0;
    }

    function sort() {
      const mode = sortSelect ? sortSelect.value : "newest";
      const byDate = (a, b) => (a.dataset.date || "").localeCompare(b.dataset.date || "");
      const byRating = (a, b) => (parseFloat(b.dataset.rating) || -1) - (parseFloat(a.dataset.rating) || -1);
      const compare = { newest: (a, b) => byDate(b, a), oldest: byDate, rating: byRating }[mode];
      items.sort(compare).forEach((item) => list.appendChild(item));
    }

    controls.forEach((c) => c.addEventListener("input", apply));
    if (sortSelect) sortSelect.addEventListener("change", sort);
    apply();
  });

  // ── dialogs (book shelf) ────────────────────────────────────
  $$("[data-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const dlg = document.getElementById(btn.dataset.open);
      if (dlg && dlg.showModal) dlg.showModal();
    });
  });
  $$("dialog.sheet").forEach((dlg) => {
    dlg.addEventListener("click", (e) => {
      if (e.target === dlg) dlg.close();
    });
    $$("[data-close]", dlg).forEach((b) => b.addEventListener("click", () => dlg.close()));
  });
})();
