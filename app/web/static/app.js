const state = {
  caseId: Number(localStorage.getItem("fennec.caseId")) || null,
  modules: [],
  findings: [],
  filter: "all",
  matches: [],
  selected: new Set(),
  openGroups: loadOpenGroups(),
};

const notice = document.querySelector("#notice");
const caseList = document.querySelector("#case-list");
const toolList = document.querySelector("#tool-list");
const findingsBody = document.querySelector("#findings");
const runsList = document.querySelector("#runs");

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

function persist() {
  if (state.caseId) localStorage.setItem("fennec.caseId", String(state.caseId));
  localStorage.setItem("fennec.groups", JSON.stringify([...state.openGroups]));
}

async function loadCases(selectId) {
  const cases = await api("/api/cases");
  caseList.replaceChildren();
  if (cases.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "None yet.";
    caseList.append(empty);
    state.caseId = null;
    showWorkspace(false);
    return cases;
  }
  const open = selectId || state.caseId || cases[0].id;
  for (const item of cases) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.name;
    button.title = item.name;
    button.className = item.id === open ? "active" : "";
    button.addEventListener("click", () => openCase(item.id));
    caseList.append(button);
  }
  if (open) await openCase(open);
  return cases;
}

function showWorkspace(open) {
  document.querySelector("#welcome").hidden = open;
  document.querySelector("#results").hidden = !open;
  document.querySelector("#export-links").hidden = !open;
}

async function openCase(id) {
  state.caseId = id;
  persist();
  const caseFile = await api(`/api/cases/${id}`);
  showWorkspace(true);
  document.querySelector("#export-json").href = `/api/cases/${id}/export`;
  document.querySelector("#export-html").href = `/api/cases/${id}/export.html`;
  document.querySelector("#export-pdf").href = `/api/cases/${id}/export.pdf`;
  document.querySelector("#case-kicker").textContent = `Case ${caseFile.id}`;
  document.querySelector("#case-title").textContent = caseFile.name;
  document.querySelector("#case-notes").textContent = caseFile.notes || "";
  document.querySelector("#case-stats").textContent =
    `${caseFile.findings.length} findings · ${caseFile.runs.length} lookups · ${ (caseFile.links || []).length } links`;
  state.findings = caseFile.findings;
  renderFindings();
  renderRuns(caseFile.runs);
  renderLinks(caseFile.links || []);
  paintCaseList();
}

function paintCaseList() {
  api("/api/cases").then((cases) => {
    [...caseList.querySelectorAll("button")].forEach((button, index) => {
      button.classList.toggle("active", cases[index] && cases[index].id === state.caseId);
    });
  });
}

const GROUPS = [
  { id: "basic", label: "Basic" },
  { id: "social", label: "Social" },
  { id: "addresses", label: "Addresses" },
  { id: "network", label: "Network" },
  { id: "crypto", label: "Crypto" },
  { id: "files", label: "Files" },
];

function renderTools() {
  toolList.replaceChildren();
  for (const group of GROUPS) {
    const items = state.modules.filter((item) => item.category === group.id);
    if (!items.length) continue;
    const open = state.openGroups.has(group.id);
    const heading = document.createElement("button");
    heading.type = "button";
    heading.className = "tool-group";
    heading.setAttribute("aria-expanded", open ? "true" : "false");
    const title = document.createElement("span");
    title.textContent = `${group.label} (${items.length})`;
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
    chip.textContent = `${item.label}: ${item.value}`;
    chip.title = state.selected.has(item.module) ? "Click to skip this tool" : "Click to include this tool";
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

function renderFindings() {
  const rows = state.findings.filter((row) => state.filter === "all" || row.kind === state.filter);
  findingsBody.replaceChildren();
  document.querySelector("#finding-count").textContent = `${rows.length} shown · ${state.findings.length} total`;
  const kinds = ["all", ...new Set(state.findings.map((row) => row.kind))];
  const filters = document.querySelector("#filters");
  filters.replaceChildren();
  for (const kind of kinds) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = kind;
    button.className = kind === state.filter ? "on" : "";
    button.addEventListener("click", () => {
      state.filter = kind;
      renderFindings();
    });
    filters.append(button);
  }
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="empty" colspan="5">Nothing on this case yet. Use the search bar.</td>';
    findingsBody.append(tr);
    return;
  }
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of ["kind", "value", "source", "confidence", "evidence"]) {
      const td = document.createElement("td");
      td.textContent = row[key] || "";
      tr.append(td);
    }
    findingsBody.append(tr);
  }
}

function renderRuns(rows) {
  runsList.replaceChildren();
  if (!rows.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No lookups yet.";
    runsList.append(li);
    return;
  }
  for (const run of rows) {
    const li = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = `${run.module_id} · ${run.input_value}`;
    const meta = document.createElement("span");
    meta.className = run.status;
    meta.textContent = run.error ? `${run.status}: ${run.error}` : `${run.status} · ${run.created_at || ""}`;
    li.append(title, document.createElement("br"), meta);
    runsList.append(li);
  }
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
    li.textContent = `${row.kind} · ${row.value} · ${row.count} findings`;
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
      state.selected = new Set(state.matches.map((item) => item.module));
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
    await loadCases(created.id);
  } catch (error) {
    setNotice(error.message);
  }
});

async function boot() {
  state.modules = await api("/api/modules");
  renderTools();
  renderChips();
  await loadCases(state.caseId);
}

boot().catch((error) => setNotice(error.message));
