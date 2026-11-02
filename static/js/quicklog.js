(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const HINT =
    '<div class="log-hint">Pick something above and the right fields show up here.<br>' +
    "You can always add the extras later from the admin.</div>";

  // ── per-form behavior ───────────────────────────────────────
  function initChips(form) {
    $$("[data-chips]", form).forEach((box) => {
      const hidden = $("[data-chips-value]", box);
      const list = $("[data-chips-list]", box);
      const input = $("[data-chips-input]", box);
      let names = hidden.value.split(",").map((s) => s.trim()).filter(Boolean);

      function render() {
        list.innerHTML = "";
        names.forEach((name, i) => {
          const chip = document.createElement("span");
          chip.className = "chip-x";
          chip.textContent = name;
          const x = document.createElement("button");
          x.type = "button";
          x.textContent = "×";
          x.setAttribute("aria-label", "Remove " + name);
          x.addEventListener("click", () => { names.splice(i, 1); render(); });
          chip.appendChild(x);
          list.appendChild(chip);
        });
        hidden.value = names.join(", ");
      }
      function add(value) {
        value = value.replace(/,/g, " ").trim();
        if (value && !names.some((n) => n.toLowerCase() === value.toLowerCase())) names.push(value);
        input.value = "";
        render();
      }

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(input.value); }
        else if (e.key === "Backspace" && !input.value && names.length) { names.pop(); render(); }
      });
      input.addEventListener("input", (e) => {
        // Picking a suggestion from the datalist arrives as a replacement-text input event.
        if (e.inputType === "insertReplacementText" || e.inputType === undefined) add(input.value);
      });
      input.addEventListener("blur", () => add(input.value));
      render();
    });
  }

  function initLocation(form) {
    const data = $('script[type="application/json"]', form);
    const venue = form.elements.venue;
    if (!data || !venue) return;
    const places = JSON.parse(data.textContent);
    venue.addEventListener("input", () => {
      const matches = places.filter((p) => p.name.toLowerCase() === venue.value.trim().toLowerCase());
      if (matches.length !== 1) return;
      const place = matches[0];
      if (form.elements.city) form.elements.city.value = place.city;
      if (form.elements.state) form.elements.state.value = place.state;
      if (form.elements.setting && place.setting) form.elements.setting.value = place.setting;
    });
  }

  function initTeams(form) {
    const home = form.elements.home_team;
    const away = form.elements.away_team;
    if (!home || !away) return;
    const sync = () => {
      $$("select[data-team-select]", form).forEach((select) => {
        Array.from(select.options).forEach((o) => {
          if (o.value === "home") o.textContent = home.value.trim() || "Home";
          if (o.value === "away") o.textContent = away.value.trim() || "Away";
        });
      });
    };
    home.addEventListener("input", sync);
    away.addEventListener("input", sync);
    sync();
  }

  function initVisibility(form) {
    const apply = () => {
      $$("[data-visible-if]", form).forEach((el) => {
        const [field, values] = el.dataset.visibleIf.split("=");
        const current = form.elements[field] ? form.elements[field].value : "";
        el.hidden = !values.split("|").includes(current);
      });
    };
    form.addEventListener("change", apply);
    apply();
  }

  function initActs(form) {
    const add = $("[data-add-act]", form);
    if (!add) return;
    const host = $("[data-acts]", form);
    const template = $("[data-act-template]", form);
    const total = form.elements["acts-TOTAL_FORMS"];
    add.addEventListener("click", () => {
      const n = parseInt(total.value, 10);
      host.insertAdjacentHTML("beforeend", template.innerHTML.replaceAll("__prefix__", n));
      total.value = n + 1;
      const row = host.lastElementChild;
      const first = $("input", row);
      if (first) first.focus();
    });
    form.addEventListener("click", (e) => {
      const remove = e.target.closest("[data-remove-act]");
      if (remove) remove.closest("[data-act-row]").remove();
    });
  }

  function initForm(form) {
    if (!form) return;
    initChips(form);
    initLocation(form);
    initTeams(form);
    initVisibility(form);
    initActs(form);
    if (window.matchMedia("(hover: hover)").matches) {
      const first = $("input:not([type=hidden]):not([type=date]), select", form);
      if (first) first.focus({ preventScroll: true });
    }
  }

  // ── panel (used inside the drawer and on the /log/ page) ────
  function setAccent(panel, option) {
    if (option && option.dataset.color) {
      panel.style.setProperty("--accent", option.dataset.color);
      panel.style.setProperty("--accent-rgb", option.dataset.rgb);
    }
  }

  async function load(panel, kind) {
    const select = $("[data-log-kind]", panel);
    const body = $("[data-log-body]", panel);
    select.value = kind || "";
    if (!kind) { body.innerHTML = HINT; return; }
    setAccent(panel, select.selectedOptions[0]);
    body.classList.add("is-loading");
    try {
      const res = await fetch(select.dataset.base + kind + "/", { headers: { "X-Requested-With": "fetch" } });
      body.innerHTML = await res.text();
      initForm($("form", body));
    } finally {
      body.classList.remove("is-loading");
    }
  }

  function showSuccess(panel, result) {
    const body = $("[data-log-body]", panel);
    panel.dataset.dirty = "1";
    body.innerHTML =
      '<div class="log-success"><span class="log-check"></span><h3>Logged!</h3><p></p>' +
      '<div class="log-success-actions"><button type="button" class="btn" data-another>Log another</button>' +
      '<a class="btn btn-ghost"></a></div></div>';
    $(".log-check", body).innerHTML =
      '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
    $("p", body).textContent = result.message;
    const link = $("a", body);
    link.href = result.view_url;
    link.textContent = "View in " + result.tracker;
    $("[data-another]", body).addEventListener("click", () => load(panel, result.kind));
  }

  function initPanel(panel) {
    const select = $("[data-log-kind]", panel);
    select.addEventListener("change", () => load(panel, select.value));
    initForm($("form", panel));

    panel.addEventListener("submit", async (e) => {
      const form = e.target.closest("[data-qform]");
      if (!form) return;
      e.preventDefault();
      const button = $("[data-submit]", form);
      button.disabled = true;
      button.classList.add("is-busy");
      try {
        const res = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { "X-Requested-With": "fetch" },
        });
        if ((res.headers.get("content-type") || "").includes("json")) {
          showSuccess(panel, await res.json());
        } else {
          const body = $("[data-log-body]", panel);
          body.innerHTML = await res.text();
          const fresh = $("form", body);
          initForm(fresh);
          const bad = $(".has-error", fresh);
          if (bad) bad.scrollIntoView({ block: "center", behavior: "smooth" });
        }
      } catch (err) {
        button.disabled = false;
        button.classList.remove("is-busy");
        alert("Couldn't save — check your connection and try again.");
      }
    });
  }

  // ── drawer ──────────────────────────────────────────────────
  const drawer = document.getElementById("log-drawer");
  const drawerPanel = drawer && $("[data-log-panel]", drawer);

  function openDrawer(kind) {
    if (!drawer) return;
    drawerPanel.dataset.dirty = "";
    if (!drawer.open) drawer.showModal();
    load(drawerPanel, kind || "");
  }

  if (drawer) {
    initPanel(drawerPanel);
    // Closing after something was saved refreshes the page so new entries and stats appear.
    drawer.addEventListener("close", () => { if (drawerPanel.dataset.dirty) location.reload(); });
    drawer.addEventListener("click", (e) => { if (e.target === drawer) drawer.close(); });
    $("[data-drawer-close]", drawer).addEventListener("click", () => drawer.close());

    document.addEventListener("click", (e) => {
      const opener = e.target.closest("[data-log-open]");
      if (opener) { e.preventDefault(); openDrawer(opener.dataset.logOpen || ""); return; }
      const link = e.target.closest('a[href^="/log/"]');
      if (link && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
        e.preventDefault();
        openDrawer(link.getAttribute("href").replace(/^\/log\/|\/$/g, ""));
      }
    });
  } else {
    // The standalone /log/ page: just wire up its own panel.
    $$("[data-log-panel]").forEach(initPanel);
  }
})();
