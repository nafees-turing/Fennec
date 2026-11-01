const state = { caseId: null, modules: [], findings: [], filter: "all" };

const notice = document.querySelector("#notice");
const caseList = document.querySelector("#case-list");
const findingsBody = document.querySelector("#findings");
const runsList = document.querySelector("#runs");

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    ...options,
  });
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

async function loadCases(selectId) {
  const cases = await api("/api/cases");
  caseList.replaceChildren();
  if (cases.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No cases yet.";
    caseList.append(empty);
    return cases;
  }
  for (const item of cases) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.name;
    button.className = item.id === state.caseId ? "active" : "";
    button.addEventListener("click", () => openCase(item.id));
    caseList.append(button);
  }
  const open = selectId || state.caseId || cases[0].id;
  if (open && open !== state.caseId) await openCase(open);
  return cases;
}

async function openCase(id) {
  state.caseId = id;
  const caseFile = await api(`/api/cases/${id}`);
  document.querySelector("#welcome").hidden = true;
  document.querySelector("#results").hidden = false;
  document.querySelector("#case-kicker").textContent = `Case ${caseFile.id}`;
  document.querySelector("#case-title").textContent = caseFile.name;
  document.querySelector("#case-notes").textContent = caseFile.notes || "";
  state.findings = caseFile.findings;
  renderFindings();
  renderRuns(caseFile.runs);
  renderModules();
  highlightCase();
}

function highlightCase() {
  for (const button of caseList.querySelectorAll("button")) {
    button.classList.toggle("active", button.textContent && true);
  }
  api("/api/cases").then((cases) => {
    const buttons = [...caseList.querySelectorAll("button")];
    buttons.forEach((button, index) => {
      button.classList.toggle("active", cases[index] && cases[index].id === state.caseId);
    });
  });
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
    tr.innerHTML = '<td class="empty" colspan="5">No findings yet.</td>';
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
    li.textContent = "No runs yet.";
    runsList.append(li);
    return;
  }
  for (const run of rows) {
    const li = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = `${run.module_id} · ${run.input_value}`;
    const meta = document.createElement("span");
    meta.className = run.status;
    meta.textContent = run.error ? `${run.status}: ${run.error}` : run.status;
    li.append(title, document.createElement("br"), meta);
    runsList.append(li);
  }
}

function renderModules() {
  const host = document.querySelector("#modules");
  host.hidden = state.caseId == null;
  host.replaceChildren();
  for (const module of state.modules) {
    const card = document.createElement("article");
    card.className = module.available ? "module" : "module locked";
    const title = document.createElement("h3");
    title.textContent = `${module.title} · ${module.milestone}`;
    const summary = document.createElement("small");
    summary.textContent = module.available ? module.summary : module.reason;
    card.append(title, summary);
    if (module.available) {
      const form = document.createElement("form");
      const input = document.createElement("input");
      input.name = "value";
      input.required = true;
      input.placeholder = module.placeholder;
      input.setAttribute("aria-label", module.input_label);
      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = "Run";
      form.append(input, button);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        button.disabled = true;
        document.body.classList.add("busy");
        const wait = module.id === "email" ? "Email scan in progress. This can take about a minute." : "";
        setNotice(wait);
        try {
          await api(`/api/cases/${state.caseId}/runs`, {
            method: "POST",
            body: JSON.stringify({ module: module.id, value: input.value }),
          });
          input.value = "";
          setNotice("");
          await openCase(state.caseId);
        } catch (error) {
          setNotice(error.message);
        } finally {
          button.disabled = false;
          document.body.classList.remove("busy");
        }
      });
      card.append(form);
    }
    host.append(card);
  }
}

document.querySelector("#new-case").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const created = await api("/api/cases", {
      method: "POST",
      body: JSON.stringify({ name: form.name.value, notes: form.notes.value }),
    });
    form.reset();
    setNotice("");
    await loadCases(created.id);
  } catch (error) {
    setNotice(error.message);
  }
});

async function boot() {
  state.modules = await api("/api/modules");
  await loadCases();
}

boot().catch((error) => setNotice(error.message));
