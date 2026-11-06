const state = {
  caseId: Number(localStorage.getItem("fennec.caseId")) || null,
  modules: [],
  findings: [],
  filter: "all",
  matches: [],
  selected: new Set(),
  openGroups: loadOpenGroups(),
  defaults: new Set(),
  personalDefaults: [],
  cases: [],
  caseQuery: "",
  toolQuery: "",
  casesOpen: localStorage.getItem("fennec.casesOpen") !== "0",
  toolsOpen: localStorage.getItem("fennec.toolsOpen") !== "0",
  profileId: null,
  tab: "result",
  profiles: [],
};

const notice = document.querySelector("#notice");
const caseList = document.querySelector("#case-list");
const toolList = document.querySelector("#tool-list");
const lookupsHost = document.querySelector("#lookups");

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
  const body = await response.json();
  if (!response.ok) {
    const message = body.error ? body.error.message : "Request failed";
    throw new Error(message);
  }
  return body.data;
}

function setNotice(text) {
  notice.textContent = text || "";
}

function loadOpenGroups() {
  try {
    const saved = JSON.parse(localStorage.getItem("fennec.groups") || "null");
    if (Array.isArray(saved) && saved.length) return new Set(saved);
  } catch (error) {
    /* keep default */
  }
  return new Set(["basic"]);
}

function caseHue(id) {
  const index = Math.abs(Number(id) || 0) % 8;
  return `var(--case-${index})`;
}

function tint(node, id) {
  node.style.setProperty("--case", caseHue(id));
  node.classList.add("tinted");
}

function persist() {
  if (state.caseId) localStorage.setItem("fennec.caseId", String(state.caseId));
  localStorage.setItem("fennec.groups", JSON.stringify([...state.openGroups]));
  localStorage.setItem("fennec.casesOpen", state.casesOpen ? "1" : "0");
  localStorage.setItem("fennec.toolsOpen", state.toolsOpen ? "1" : "0");
}

function applyFolds() {
  document.querySelector("#cases-body").hidden = !state.casesOpen;
  document.querySelector("#tools-body").hidden = !state.toolsOpen;
  const casesToggle = document.querySelector("#cases-toggle");
  const toolsToggle = document.querySelector("#tools-toggle");
  casesToggle.setAttribute("aria-expanded", state.casesOpen ? "true" : "false");
  toolsToggle.setAttribute("aria-expanded", state.toolsOpen ? "true" : "false");
  casesToggle.querySelector(".chevron").textContent = state.casesOpen ? "▾" : "▸";
  toolsToggle.querySelector(".chevron").textContent = state.toolsOpen ? "▾" : "▸";
}

async function loadCases(selectId, skipOpen) {
  const cases = await api("/api/cases");
  state.cases = cases;
  if (cases.length === 0) {
    state.caseId = null;
    renderCases();
    showWorkspace(false);
    return cases;
  }
  const open = selectId || state.caseId || cases[0].id;
  renderCases();
  if (open && !skipOpen) await openCase(open, true);
  return cases;
}

function renderCases() {
  caseList.replaceChildren();
  const query = state.caseQuery.trim().toLowerCase();
  let rows = state.cases;
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "None yet.";
    caseList.append(empty);
    return;
  }
  if (query) {
    rows = rows.filter((item) => item.name.toLowerCase().includes(query));
  } else {
    const top = rows.slice(0, 5);
    if (state.caseId && !top.some((item) => item.id === state.caseId)) {
      const current = rows.find((item) => item.id === state.caseId);
      if (current) top.unshift(current);
    }
    rows = top;
  }
  for (const item of rows) {
    const button = document.createElement("button");
    button.type = "button";
    button.title = item.name;
    button.className = item.id === state.caseId ? "active tinted" : "tinted";
    tint(button, item.id);
    button.append(icon("case"));
    const label = document.createElement("span");
    label.textContent = item.name;
    button.append(label);
    button.addEventListener("click", () => go(`/cases/${item.id}`));
    caseList.append(button);
  }
  if (!query && state.cases.length > rows.length) {
    const more = document.createElement("p");
    more.className = "hint";
    more.textContent = `${state.cases.length - rows.length} more — search to find them`;
    caseList.append(more);
  }
  if (query && !rows.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No case matches.";
    caseList.append(empty);
  }
}

function showWorkspace(open) {
  document.querySelector("#welcome").hidden = open;
  document.querySelector("#results").hidden = !open;
  document.querySelector("#export-links").hidden = !open;
  document.querySelector("#profile-page").hidden = true;
  document.querySelector("#settings-page").hidden = true;
}

function route() {
  if (location.pathname === "/settings") return { settings: true, caseId: state.caseId, profileId: null };
  const match = location.pathname.match(/^\/cases\/(\d+)(?:\/profiles\/(\d+))?$/);
  if (!match) return { settings: false, caseId: state.caseId, profileId: null };
  return { settings: false, caseId: Number(match[1]), profileId: match[2] ? Number(match[2]) : null };
}

function go(path) {
  history.pushState({}, "", path);
  return renderRoute();
}

async function renderRoute() {
  const { caseId, profileId, settings } = route();
  await loadCases(caseId || state.caseId, true);
  if (settings) {
    showSettingsPage();
    return;
  }
  if (profileId && caseId) {
    await showProfilePage(caseId, profileId);
    return;
  }
  if (caseId) await openCase(caseId, true);
}

function hrefFor(text, kind) {
  const value = String(text || "").trim();
  if (!value) return null;
  if (/^https?:\/\//i.test(value) || value.startsWith("mailto:")) return value;
  if (kind === "email" || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return `mailto:${value}`;
  if ((kind === "wikidata" || kind === "Wikidata") && /^Q\d+$/i.test(value)) {
    return `https://www.wikidata.org/wiki/${value}`;
  }
  return null;
}

function appendValue(node, text, kind) {
  const href = hrefFor(text, kind);
  if (!href) {
    node.append(document.createTextNode(text));
    return;
  }
  const link = document.createElement("a");
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.className = "ext";
  link.textContent = text;
  node.append(link);
}

function fillList(node, values, kind) {
  node.replaceChildren();
  values.forEach((value, index) => {
    if (index) node.append(document.createTextNode(" · "));
    appendValue(node, value, kind);
  });
}

async function openCase(id, keepUrl) {
  state.caseId = id;
  persist();
  if (!keepUrl) history.pushState({}, "", `/cases/${id}`);
  const caseFile = await api(`/api/cases/${id}`);
  showWorkspace(true);
  document.querySelector("#export-json").href = `/api/cases/${id}/export`;
  document.querySelector("#export-html").href = `/api/cases/${id}/export.html`;
  document.querySelector("#export-pdf").href = `/api/cases/${id}/export.pdf`;
  document.querySelector("#case-kicker").textContent = `Case ${caseFile.id}`;
  const title = document.querySelector("#case-title");
  title.textContent = caseFile.name;
  tint(title, caseFile.id);
  tint(document.querySelector(".workspace"), caseFile.id);
  document.querySelector("#case-notes").textContent = caseFile.notes || "";
  document.querySelector("#case-stats").textContent =
    `${caseFile.findings.length} findings · ${caseFile.runs.length} lookups · ${ (caseFile.links || []).length } links`;
  state.findings = caseFile.findings;
  state.profiles = caseFile.profiles || [];
  renderProfiles(caseFile.profiles || []);
  renderLookups(caseFile.lookups || []);
  renderLinks(caseFile.links || []);
  showTab(state.tab);
  paintCaseList();
}

function showTab(name) {
  state.tab = name;
  for (const button of document.querySelectorAll("#case-tabs [data-tab]")) {
    button.classList.toggle("on", button.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    panel.hidden = panel.id !== `tab-${name}`;
  }
}

function paintCaseList() {
  api("/api/cases").then((cases) => {
    [...caseList.querySelectorAll("button")].forEach((button, index) => {
      if (!cases[index]) return;
      button.classList.toggle("active", cases[index].id === state.caseId);
      tint(button, cases[index].id);
    });
  });
}

const GROUPS = [
  { id: "basic", label: "Basic", icon: "basic" },
  { id: "social", label: "Social", icon: "social" },
  { id: "addresses", label: "Addresses", icon: "addresses" },
  { id: "network", label: "Network", icon: "network" },
  { id: "crypto", label: "Crypto", icon: "crypto" },
  { id: "files", label: "Files", icon: "files" },
];

const TOOL_ICONS = {
  email: "email",
  phone: "phone",
  name: "basic",
  person: "basic",
  username: "basic",
  social: "social",
  github: "social",
  gitlab: "social",
  keybase: "social",
  gravatar: "social",
  npm: "social",
  dockerhub: "social",
  hackernews: "social",
  reddit: "social",
  chess: "social",
  lichess: "social",
  stackoverflow: "social",
  devto: "social",
  wikipedia: "basic",
  pgp: "basic",
  address: "addresses",
  company: "addresses",
  sanctions: "addresses",
  geocode: "addresses",
  domain: "network",
  geoip: "network",
  rdns: "network",
  internetdb: "network",
  bgp: "network",
  greynoise: "network",
  otx: "network",
  certs: "network",
  securitytxt: "network",
  archive: "network",
  bitcoin: "crypto",
  ethereum: "crypto",
  metadata: "files",
};

function kindHue(kind) {
  if (["email", "phone", "name", "username", "line_type", "region", "carrier", "timezone"].includes(kind)) return "basic";
  if (["account", "note", "query"].includes(kind)) return "social";
  if (["address", "company", "place", "coords", "sanction"].includes(kind)) return "addresses";
  if (["domain", "ip", "hostname", "asn", "org", "port", "prefix", "cert_name", "rir", "noise", "software", "cve"].includes(kind)) return "network";
  if (["wallet", "balance", "tx_count"].includes(kind)) return "crypto";
  if (["file", "hash", "format", "exif", "gps"].includes(kind)) return "files";
  return "search";
}

function icon(name, hue) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", `icon hue-${hue || name}`);
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
}

function renderTools() {
  toolList.replaceChildren();
  const query = state.toolQuery.trim().toLowerCase();
  for (const group of GROUPS) {
    const items = state.modules.filter((item) => {
      if (item.category !== group.id) return false;
      if (!query) return true;
      const hay = `${item.title} ${item.id} ${item.summary || ""}`.toLowerCase();
      return hay.includes(query);
    });
    if (!items.length) continue;
    const open = query ? true : state.openGroups.has(group.id);
    const heading = document.createElement("button");
    heading.type = "button";
    heading.className = `tool-group hue-${group.id}`;
    heading.setAttribute("aria-expanded", open ? "true" : "false");
    const title = document.createElement("span");
    title.append(icon(group.icon, group.id), document.createTextNode(` ${group.label} (${items.length})`));
    const chevron = document.createElement("span");
    chevron.className = "chevron";
    chevron.textContent = open ? "▾" : "▸";
    heading.append(title, chevron);
    heading.addEventListener("click", () => {
      if (state.openGroups.has(group.id)) state.openGroups.delete(group.id);
      else state.openGroups.add(group.id);
      persist();
      renderTools();
    });
    toolList.append(heading);
    if (!open) continue;
    const body = document.createElement("div");
    body.className = "tool-body";
    for (const module of items) {
      const button = document.createElement("button");
      button.type = "button";
      button.disabled = !module.available;
      button.className = state.selected.has(module.id) ? "related" : "";
      button.append(icon(TOOL_ICONS[module.id] || module.category || "dot", module.category));
      const label = document.createElement("span");
      label.textContent = module.title;
      button.append(label);
      if (module.network) {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = "net";
        button.append(tag);
      }
      button.title = module.available ? module.summary : module.reason;
      button.addEventListener("click", () => pinTool(module));
      body.append(button);
    }
    toolList.append(body);
  }
}

function pinTool(module) {
  if (!module.available) return;
  const exists = state.matches.some((item) => item.module === module.id);
  if (exists) {
    if (state.selected.has(module.id)) state.selected.delete(module.id);
    else state.selected.add(module.id);
  } else {
    state.matches.push({
      module: module.id,
      value: document.querySelector("#smart-input").value.trim() || module.placeholder,
      label: module.title,
      kind: module.id,
    });
    state.selected.add(module.id);
  }
  renderChips();
  renderTools();
}

function renderChips() {
  const host = document.querySelector("#smart-chips");
  host.replaceChildren();
  if (!state.matches.length) {
    const chip = document.createElement("span");
    chip.className = "chip miss";
    chip.textContent = "Detected tools appear here as tags. Click to include or skip.";
    host.append(chip);
    renderTools();
    return;
  }
  for (const item of state.matches) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = state.selected.has(item.module) ? "chip on" : "chip";
    const module = state.modules.find((row) => row.id === item.module);
    chip.classList.add(`hue-${module ? module.category : "search"}`);
    chip.append(icon(TOOL_ICONS[item.module] || "dot", module ? module.category : "search"));
    chip.append(document.createTextNode(` ${item.label}: ${item.value}`));
    chip.title = state.selected.has(item.module)
      ? "On for this search"
      : state.defaults.has(item.module)
        ? "Default tool — click to include"
        : "Off by default — click to include this time";
    chip.addEventListener("click", () => {
      if (state.selected.has(item.module)) state.selected.delete(item.module);
      else state.selected.add(item.module);
      renderChips();
      renderTools();
    });
    host.append(chip);
  }
  renderTools();
}

function renderProfiles(profiles) {
  const host = document.querySelector("#profiles");
  host.replaceChildren();
  document.querySelector("#profile-count").textContent = `${profiles.length} combined`;
  if (!profiles.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Profiles appear here when a search has a person identifier. Not-found tools stay in Searches only.";
    host.append(empty);
    return;
  }
  for (const profile of profiles) {
    const card = document.createElement("article");
    card.className = "profile-card profile-summary";
    const title = document.createElement("h3");
    title.append(icon("basic", "basic"));
    title.append(document.createTextNode(` ${profile.title}`));
    card.append(title);
    if (profile.avatar_url) {
      const img = document.createElement("img");
      img.className = "avatar";
      img.src = profile.avatar_url;
      img.alt = "";
      img.width = 48;
      img.height = 48;
      card.prepend(img);
    }
    const dl = document.createElement("dl");
    const preview = [
      ["Emails", profile.emails, "email"],
      ["Phones", profile.phones, "phone"],
      ["Usernames", (profile.usernames || []).slice(0, 4), "username"],
      ["Accounts", (profile.accounts || []).slice(0, 3), "url"],
    ];
    for (const [label, values, kind] of preview) {
      if (!values || !values.length) continue;
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      fillList(dd, values, kind);
      dl.append(dt, dd);
    }
    card.append(dl);
    const more = document.createElement("a");
    more.className = "more";
    more.href = `/cases/${state.caseId}/profiles/${profile.id}`;
    more.textContent = "Open full profile →";
    more.addEventListener("click", (event) => {
      event.preventDefault();
      go(`/cases/${state.caseId}/profiles/${profile.id}`);
    });
    card.append(more);
    host.append(card);
  }
}

function renderProfileDetail(profile) {
  const host = document.querySelector("#profile-full");
  host.replaceChildren();
  const card = document.createElement("article");
  card.className = "profile-card";
  const title = document.createElement("h3");
  title.append(icon("basic", "basic"));
  title.append(document.createTextNode(` ${profile.title}`));
  card.append(title);
  if (profile.avatar_url) {
    const img = document.createElement("img");
    img.className = "avatar";
    img.src = profile.avatar_url;
    img.alt = "";
    img.width = 96;
    img.height = 96;
    card.prepend(img);
  }
  const exports = document.createElement("p");
  exports.className = "export";
  exports.innerHTML = `<a class="ext" href="/api/cases/${state.caseId}/profiles/${profile.id}/export.html">HTML</a>
    <a class="ext" href="/api/cases/${state.caseId}/profiles/${profile.id}/export.pdf">PDF</a>`;
  card.append(exports);
  const dl = document.createElement("dl");
  const groups = [
    ["Names", profile.names, "name"],
    ["Emails", profile.emails, "email"],
    ["Phones", profile.phones, "phone"],
    ["Usernames", profile.usernames, "username"],
    ["Accounts", profile.accounts, "url"],
    ["Addresses", profile.addresses, "address"],
    ["Companies", profile.companies, "company"],
    ["Places", profile.places, "place"],
    ["URLs", profile.urls, "url"],
    ["Wallets", profile.wallets, "wallet"],
    ["Wikidata", profile.wikidata, "wikidata"],
    ["Other", profile.other, "other"],
  ];
  for (const [label, values, kind] of groups) {
    if (!values || !values.length) continue;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    fillList(dd, values, kind);
    dl.append(dt, dd);
  }
  card.append(dl);
  host.append(card);
}

async function showProfilePage(caseId, profileId) {
  state.caseId = caseId;
  persist();
  const caseFile = await api(`/api/cases/${caseId}`);
  const profile = (caseFile.profiles || []).find((item) => item.id === profileId);
  document.querySelector("#welcome").hidden = true;
  document.querySelector("#results").hidden = true;
  document.querySelector("#export-links").hidden = true;
  document.querySelector("#settings-page").hidden = true;
  document.querySelector("#profile-page").hidden = false;
  document.querySelector("#back-to-case").href = `/cases/${caseId}`;
  const heading = document.querySelector("#case-title");
  heading.textContent = profile ? profile.title : "Profile not found";
  tint(heading, caseId);
  document.querySelector("#case-kicker").textContent = `Case ${caseId} · profile`;
  document.querySelector("#case-notes").textContent = caseFile.name;
  document.querySelector("#case-stats").textContent = profile
    ? `${profile.finding_count} combined findings`
    : "";
  state.profileId = profile ? profile.id : null;
  if (profile) renderProfileDetail(profile);
  else document.querySelector("#profile-full").textContent = "That profile is not on this case.";
}

function findingsTable(rows) {
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const table = document.createElement("table");
  table.innerHTML = "<thead><tr><th>Kind</th><th>Value</th><th>Source</th><th>Confidence</th><th>Evidence</th></tr></thead>";
  const body = document.createElement("tbody");
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="empty" colspan="5">No findings from this tool.</td>';
    body.append(tr);
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of ["kind", "value", "source", "confidence", "evidence"]) {
      const td = document.createElement("td");
      if (key === "kind") {
        const pill = document.createElement("span");
        pill.className = `kind hue-${kindHue(row.kind)}`;
        pill.textContent = row.kind || "";
        td.append(pill);
      } else if (key === "value" || key === "evidence") {
        appendValue(td, row[key] || "", key === "value" ? row.kind : "url");
      } else {
        td.textContent = row[key] || "";
      }
      tr.append(td);
    }
    body.append(tr);
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}

function paintLookupCards(host, lookups, emptyText) {
  host.replaceChildren();
  if (!lookups.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = emptyText;
    host.append(empty);
    return;
  }
  lookups.forEach((lookup, index) => {
    const card = document.createElement("article");
    card.className = "lookup-card";
    const head = document.createElement("header");
    head.className = "lookup-head";
    const title = document.createElement("h3");
    title.append(icon("search", "search"));
    title.append(document.createTextNode(` ${lookup.query}`));
    const meta = document.createElement("p");
    meta.className = "count";
    meta.textContent = `${lookup.runs.length} tools · ${lookup.created_at || ""}`;
    head.append(title, meta);
    card.append(head);
    if ((state.profiles || []).length) {
      const attach = document.createElement("form");
      attach.className = "attach";
      const select = document.createElement("select");
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "Add this search to a profile…";
      select.append(blank);
      for (const profile of state.profiles) {
        const option = document.createElement("option");
        option.value = String(profile.id);
        option.textContent = profile.title;
        select.append(option);
      }
      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = "Attach";
      attach.append(select, button);
      attach.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!select.value || !state.caseId) return;
        try {
          await api(`/api/cases/${state.caseId}/profiles/${select.value}/attach`, {
            method: "POST",
            body: JSON.stringify({ lookup_id: lookup.id }),
          });
          setNotice("Search attached to that profile.");
          state.tab = "profiles";
          await openCase(state.caseId, true);
        } catch (error) {
          setNotice(error.message);
        }
      });
      card.append(attach);
    }
    for (const run of lookup.runs) {
      const block = document.createElement("section");
      block.className = "run-block";
      const label = document.createElement("h4");
      const module = state.modules.find((item) => item.id === run.module_id);
      label.append(icon(TOOL_ICONS[run.module_id] || "dot", module ? module.category : "search"));
      label.append(document.createTextNode(` ${module ? module.title : run.module_id}`));
      const status = document.createElement("span");
      status.className = run.status || "ok";
      status.textContent = run.error ? `${run.status}: ${run.error}` : run.status;
      label.append(status);
      block.append(label);
      block.append(findingsTable(run.findings || []));
      card.append(block);
    }
    host.append(card);
  });
}

function renderLookups(lookups) {
  const total = lookups.reduce((sum, item) => sum + item.runs.reduce((n, run) => n + (run.findings || []).length, 0), 0);
  const count = document.querySelector("#finding-count");
  if (count) count.textContent = `${lookups.length} searches · ${total} findings`;
  paintLookupCards(
    document.querySelector("#current-lookup"),
    lookups.slice(0, 1),
    "Run a lookup above. This tab shows only that result.",
  );
  paintLookupCards(lookupsHost, lookups, "No searches on this case yet.");
}

function renderLinks(rows) {
  const host = document.querySelector("#links");
  host.replaceChildren();
  if (!rows.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No shared values yet.";
    host.append(li);
    return;
  }
  for (const row of rows) {
    const li = document.createElement("li");
    li.append(document.createTextNode(`${row.kind} · `));
    appendValue(li, row.value, row.kind);
    li.append(document.createTextNode(` · ${row.count} findings`));
    host.append(li);
  }
}

let detectTimer = 0;
document.querySelector("#smart-input").addEventListener("input", () => {
  clearTimeout(detectTimer);
  detectTimer = setTimeout(async () => {
    const value = document.querySelector("#smart-input").value.trim();
    if (!value) {
      state.matches = [];
      state.selected = new Set();
      renderChips();
      return;
    }
    try {
      const result = await api(`/api/detect?q=${encodeURIComponent(value)}`);
      state.matches = result.matches || [];
      state.selected = new Set(state.matches.filter((item) => state.defaults.has(item.module)).map((item) => item.module));
      for (const item of state.matches) {
        const module = state.modules.find((row) => row.id === item.module);
        if (module) state.openGroups.add(module.category);
      }
      persist();
      renderChips();
    } catch (error) {
      setNotice(error.message);
    }
  }, 180);
});

document.querySelector("#smart-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.caseId) {
    setNotice("Select a case first.");
    return;
  }
  const value = document.querySelector("#smart-input").value.trim();
  const button = event.currentTarget.querySelector("button");
  const modules = [...state.selected];
  if (!modules.length) {
    setNotice("No default tools match this value. Turn on tags or open Settings.");
    return;
  }
  button.disabled = true;
  document.body.classList.add("busy");
  setNotice("Running selected tags only.");
  try {
    const result = await api(`/api/cases/${state.caseId}/lookup`, {
      method: "POST",
      body: JSON.stringify({ value, modules }),
    });
    const names = result.matches.map((item) => item.label).join(", ");
    setNotice(`Detected ${result.detected}. Ran ${names || "selected tools"}.`);
    document.querySelector("#smart-input").value = "";
    state.tab = "result";
    await openCase(state.caseId);
  } catch (error) {
    setNotice(error.message);
  } finally {
    button.disabled = false;
    document.body.classList.remove("busy");
  }
});

document.querySelector("#new-case").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const created = await api("/api/cases", {
      method: "POST",
      body: JSON.stringify({ name: form.name.value, notes: "" }),
    });
    form.reset();
    setNotice("Case open.");
    await loadCases(created.id, true);
    await go(`/cases/${created.id}`);
  } catch (error) {
    setNotice(error.message);
  }
});

function showSettingsPage() {
  document.querySelector("#welcome").hidden = true;
  document.querySelector("#results").hidden = true;
  document.querySelector("#export-links").hidden = true;
  document.querySelector("#profile-page").hidden = true;
  document.querySelector("#settings-page").hidden = false;
  document.querySelector("#case-kicker").textContent = "Preferences";
  document.querySelector("#case-title").textContent = "Search defaults";
  document.querySelector("#case-notes").textContent = "Personal tools are on by default. Network and crypto stay off until you enable them.";
  document.querySelector("#case-stats").textContent = "";
  renderSettingsForm();
}

function renderSettingsForm() {
  const form = document.querySelector("#settings-form");
  form.replaceChildren();
  for (const group of GROUPS) {
    const items = state.modules.filter((item) => item.category === group.id);
    if (!items.length) continue;
    const box = document.createElement("fieldset");
    box.className = "settings-group";
    const heading = document.createElement("h3");
    heading.className = `hue-${group.id}`;
    heading.append(icon(group.icon, group.id), document.createTextNode(` ${group.label}`));
    box.append(heading);
    for (const module of items) {
      const label = document.createElement("label");
      const check = document.createElement("input");
      check.type = "checkbox";
      check.name = "module";
      check.value = module.id;
      check.checked = state.defaults.has(module.id);
      label.append(check, icon(TOOL_ICONS[module.id] || group.icon, group.id), document.createTextNode(` ${module.title}`));
      box.append(label);
    }
    form.append(box);
  }
}

async function loadSettings() {
  const data = await api("/api/settings");
  state.personalDefaults = data.personal_defaults || [];
  state.defaults = new Set(data.default_modules || state.personalDefaults);
}

document.querySelector("#case-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-tab]");
  if (button) showTab(button.dataset.tab);
});

document.querySelector("#cases-toggle").addEventListener("click", () => {
  state.casesOpen = !state.casesOpen;
  persist();
  applyFolds();
});

document.querySelector("#tools-toggle").addEventListener("click", () => {
  state.toolsOpen = !state.toolsOpen;
  persist();
  applyFolds();
});

document.querySelector("#case-filter").addEventListener("input", (event) => {
  state.caseQuery = event.currentTarget.value;
  renderCases();
});

document.querySelector("#tool-filter").addEventListener("input", (event) => {
  state.toolQuery = event.currentTarget.value;
  renderTools();
});

document.querySelector("#delete-profile").addEventListener("click", async () => {
  if (!state.caseId || !state.profileId) return;
  if (!window.confirm("Remove this profile and its findings from the case? Searches stay unless they have no findings left.")) return;
  try {
    await api(`/api/cases/${state.caseId}/profiles/${state.profileId}`, { method: "DELETE" });
    setNotice("Profile removed.");
    go(`/cases/${state.caseId}`);
  } catch (error) {
    setNotice(error.message);
  }
});

document.querySelector("#settings-link").addEventListener("click", (event) => {
  event.preventDefault();
  go("/settings");
});

document.querySelector("#settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const chosen = [...event.currentTarget.querySelectorAll("input[name=module]:checked")].map((item) => item.value);
  try {
    const saved = await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ default_modules: chosen }),
    });
    state.defaults = new Set(saved.default_modules);
    setNotice("Defaults saved. New searches use these tools.");
  } catch (error) {
    setNotice(error.message);
  }
});

document.querySelector("#reset-defaults").addEventListener("click", async () => {
  try {
    const saved = await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ default_modules: state.personalDefaults }),
    });
    state.defaults = new Set(saved.default_modules);
    renderSettingsForm();
    setNotice("Reset to personal defaults.");
  } catch (error) {
    setNotice(error.message);
  }
});

document.querySelector("#back-to-case").addEventListener("click", (event) => {
  event.preventDefault();
  if (state.caseId) go(`/cases/${state.caseId}`);
  else go("/");
});

window.addEventListener("popstate", () => {
  renderRoute().catch((error) => setNotice(error.message));
});

async function boot() {
  state.modules = await api("/api/modules");
  await loadSettings();
  applyFolds();
  renderTools();
  renderChips();
  await renderRoute();
}

boot().catch((error) => setNotice(error.message));
