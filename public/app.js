const API = "/api";

const BASE_CATEGORIES = {
  Income: ["Doug Paycheck", "Amanda Paycheck", "Doug Bonus", "Amanda Bonus", "Doug VA"],
  Savings: ["Emergency Fund (MT)"],
  Bills: [
    "Child Support (MT)", "iCloud (1st) (AP)", "Paramount+ (4th) (AP)", "Spotify (5th) (AP)",
    "Netflix (5th) (AP)", "Cell Phone (9th) (AP)", "OnStar (11th) (AP)", "REMC Fiber (12th) (AP)",
    "Microsoft (12th) (AP)", "Nest (16th) (AP)", "Sallie Mae (16th) (BP)", "REMC (17th) (AP)",
    "Beach Body (17th) (AP)", "Life 360 (17th) (AP)", "Hulu (19th) (AP)", "Sewage (22nd) (AP)",
    "Insurance (23rd) (AP)", "Amazon CC (23rd) (BP)", "Youtube TV (23rd) (AP)", "Water (26th) (AP)",
    "NIPSCO (26th) (BP)", "Peacock (28th) (AP)", "Spotify (29th) (AP)"
  ],
  Expenses: ["Groceries", "Gas", "Other"],
  Debt: [
    "Mortgage (1st) (BP)", "Windows (5th) (BP)", "Ravi (7th) (MT)",
    "Truck (15th) (MT)", "Extra Truck (MT)", "Extra Credit Card (BP) (MT)"
  ]
};

const TYPICAL = {
  "Doug Paycheck": 3639.45, "Amanda Paycheck": 1295.65, "Child Support (MT)": 680.00,
  "iCloud (1st) (AP)": 9.99, "Spotify (5th) (AP)": 16.99, "Netflix (5th) (AP)": 19.99,
  "Cell Phone (9th) (AP)": 425.00, "OnStar (11th) (AP)": 14.99, "REMC Fiber (12th) (AP)": 80.44,
  "Microsoft (12th) (AP)": 21.39, "Nest (16th) (AP)": 15.00, "Sallie Mae (16th) (BP)": 40.00,
  "REMC (17th) (AP)": 150.00, "Beach Body (17th) (AP)": 15.95, "Life 360 (17th) (AP)": 16.04,
  "Hulu (19th) (AP)": 19.95, "Sewage (22nd) (AP)": 71.00, "Insurance (23rd) (AP)": 246.19,
  "Amazon CC (23rd) (BP)": 200.00, "Youtube TV (23rd) (AP)": 120.00, "Water (26th) (AP)": 85.00,
  "NIPSCO (26th) (BP)": 47.00, "Peacock (28th) (AP)": 11.99, "Spotify (29th) (AP)": 19.99,
  "Mortgage (1st) (BP)": 2206.90, "Windows (5th) (BP)": 301.46, "Ravi (7th) (MT)": 709.27,
  "Truck (15th) (MT)": 659.29, "Extra Credit Card (BP) (MT)": 0.0
};

let categories = structuredClone(BASE_CATEGORIES);
let currentPeriod = null;

function money(n) {
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts
  });
  if (!res.ok) {
    let errText = await res.text();
    try {
      const j = JSON.parse(errText);
      errText = j.error || errText;
    } catch {}
    throw new Error(errText || res.statusText);
  }
  return res.json();
}

// Navigation
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("page-" + btn.dataset.page).classList.add("active");
    if (btn.dataset.page === "current") loadCurrent();
    if (btn.dataset.page === "past") loadPast();
    if (btn.dataset.page === "settings") loadSettings();
  });
});

function fillSelect(sel, items, selected) {
  sel.innerHTML = items.map(i => `<option value="${i}" ${i === selected ? "selected" : ""}>${i}</option>`).join("");
}

function populateCategorySelects() {
  const cats = Object.keys(categories);
  ["add-category", "custom-category", "edit-category", "search-category"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (id === "search-category") {
      el.innerHTML = `<option value="">All categories</option>` + cats.map(c => `<option>${c}</option>`).join("");
    } else {
      fillSelect(el, cats);
    }
  });
  updateSubSelect("add");
  updateSubSelect("edit");
}

function updateSubSelect(prefix) {
  const cat = document.getElementById(prefix + "-category")?.value;
  const sub = document.getElementById(prefix + "-subcategory");
  if (cat && categories[cat]) fillSelect(sub, categories[cat]);
}

document.getElementById("add-category")?.addEventListener("change", () => updateSubSelect("add"));
document.getElementById("edit-category")?.addEventListener("change", () => updateSubSelect("edit"));

// Load current period
async function loadCurrent() {
  try {
    const data = await api("/period/current");
    currentPeriod = data.period;
    document.getElementById("period-label").textContent = data.period.label;
    document.getElementById("period-dates").textContent =
      `${data.period.start_date} → ${data.period.end_date}`;

    const s = data.summary;
    const el = document.getElementById("leftover-amount");
    el.textContent = money(s.leftover);
    el.className = "amount " + (s.leftover >= 0 ? "positive" : "negative");
    document.getElementById("leftover-sub").textContent =
      `Income ${money(s.Income)} − Outgoing ${money(s.total_out)}`;

    document.getElementById("metrics").innerHTML = ["Income","Bills","Debt","Expenses","Savings"]
      .map(k => `<div class="metric"><div class="label">${k}</div><div class="value">${money(s[k])}</div></div>`).join("");

    // Auto items
    const auto = data.auto_items || [];
    const autoEl = document.getElementById("auto-items");
    if (!auto.length) {
      autoEl.innerHTML = `<p class="muted">No additional due items.</p>`;
    } else {
      autoEl.innerHTML = auto.map((item, i) => `
        <div class="item">
          <div class="name">${item.subcategory}<div class="cat">${item.category} · ${item.ptype}</div></div>
          <input type="number" value="${item.amount}" step="0.01" id="auto-amt-${i}" style="width:90px" />
          <button class="btn small primary" onclick="addAuto(${i}, '${item.category}', '${item.subcategory}', '${item.ptype}')">Add</button>
        </div>`).join("") +
        `<button class="btn secondary" style="margin-top:0.5rem" onclick="addAllAuto()">Add all</button>`;
      window._auto = auto;
    }

    // Transactions
    renderTxns(data.transactions || []);
  } catch (e) {
    console.error(e);
    document.getElementById("period-label").textContent = "Error loading data";
    document.getElementById("period-dates").textContent = String(e.message || e);
    document.getElementById("leftover-amount").textContent = "—";
  }
}

function renderTxns(txns) {
  const pending = txns.filter(t => t.status === "Pending");
  const paid = txns.filter(t => t.status === "Paid");

  document.getElementById("pending-list").innerHTML = pending.length
    ? `<h3 style="color:#f87171;margin:0.5rem 0">🔴 Pending</h3>` +
      pending.map(t => txnRow(t, true)).join("")
    : "";

  document.getElementById("paid-list").innerHTML = paid.length
    ? `<h3 style="color:#4ade80;margin:1rem 0 0.5rem">✅ Paid</h3>` +
      paid.map(t => txnRow(t, false)).join("")
    : (pending.length ? "" : `<p class="muted">No transactions yet.</p>`);
}

function txnRow(t, showPaid) {
  return `<div class="item">
    <div class="date">${t.date?.slice(5) || ""}</div>
    <div class="name">${t.subcategory}<div class="cat">${t.category}</div></div>
    <div class="amount">${money(t.amount)}</div>
    <div class="actions">
      ${showPaid ? `<button class="btn small primary" onclick="markPaid(${t.id})">Paid</button>` : ""}
      <button class="btn small secondary" onclick="openEdit(${t.id})">Edit</button>
    </div>
  </div>`;
}

window.addAuto = async (i, cat, sub, ptype) => {
  const amt = parseFloat(document.getElementById("auto-amt-" + i).value) || 0;
  await api("/transactions", {
    method: "POST",
    body: JSON.stringify({
      period_id: currentPeriod.id,
      date: currentPeriod.start_date,
      amount: amt,
      category: cat,
      subcategory: sub,
      description: ptype,
      method: ptype === "Auto-pay" ? "Credit Card" : "Manual",
      status: ptype === "Auto-pay" ? "Paid" : "Pending"
    })
  });
  loadCurrent();
};

window.addAllAuto = async () => {
  for (let i = 0; i < window._auto.length; i++) {
    const item = window._auto[i];
    const amt = parseFloat(document.getElementById("auto-amt-" + i).value) || item.amount;
    await api("/transactions", {
      method: "POST",
      body: JSON.stringify({
        period_id: currentPeriod.id,
        date: currentPeriod.start_date,
        amount: amt,
        category: item.category,
        subcategory: item.subcategory,
        description: item.ptype,
        method: item.ptype === "Auto-pay" ? "Credit Card" : "Manual",
        status: item.ptype === "Auto-pay" ? "Paid" : "Pending"
      })
    });
  }
  loadCurrent();
};

window.markPaid = async (id) => {
  await api("/transactions/" + id, { method: "PATCH", body: JSON.stringify({ status: "Paid" }) });
  loadCurrent();
};

window.openEdit = async (id) => {
  const t = await api("/transactions/" + id);
  document.getElementById("edit-id").value = t.id;
  document.getElementById("edit-date").value = t.date;
  document.getElementById("edit-amount").value = t.amount;
  fillSelect(document.getElementById("edit-category"), Object.keys(categories), t.category);
  updateSubSelect("edit");
  fillSelect(document.getElementById("edit-subcategory"), categories[t.category] || [], t.subcategory);
  document.getElementById("edit-status").value = t.status;
  document.getElementById("edit-desc").value = t.description || "";
  document.getElementById("edit-modal").classList.remove("hidden");
};

document.getElementById("edit-cancel").onclick = () => {
  document.getElementById("edit-modal").classList.add("hidden");
};

document.getElementById("edit-form").onsubmit = async (e) => {
  e.preventDefault();
  const id = document.getElementById("edit-id").value;
  await api("/transactions/" + id, {
    method: "PATCH",
    body: JSON.stringify({
      date: document.getElementById("edit-date").value,
      amount: parseFloat(document.getElementById("edit-amount").value),
      category: document.getElementById("edit-category").value,
      subcategory: document.getElementById("edit-subcategory").value,
      status: document.getElementById("edit-status").value,
      description: document.getElementById("edit-desc").value
    })
  });
  document.getElementById("edit-modal").classList.add("hidden");
  loadCurrent();
};

document.getElementById("edit-delete").onclick = async () => {
  const id = document.getElementById("edit-id").value;
  if (!confirm("Delete this transaction?")) return;
  await api("/transactions/" + id, { method: "DELETE" });
  document.getElementById("edit-modal").classList.add("hidden");
  loadCurrent();
};

document.getElementById("btn-next-period").onclick = async () => {
  await api("/period/next", { method: "POST" });
  loadCurrent();
};

// Add form
document.getElementById("add-form").onsubmit = async (e) => {
  e.preventDefault();
  await api("/transactions", {
    method: "POST",
    body: JSON.stringify({
      period_id: currentPeriod.id,
      date: document.getElementById("add-date").value,
      amount: parseFloat(document.getElementById("add-amount").value),
      category: document.getElementById("add-category").value,
      subcategory: document.getElementById("add-subcategory").value,
      description: document.getElementById("add-desc").value,
      method: document.getElementById("add-method").value,
      status: document.getElementById("add-status").value
    })
  });
  e.target.reset();
  document.getElementById("add-date").valueAsDate = new Date();
  alert("Saved");
};

document.getElementById("btn-add-custom").onclick = async () => {
  const cat = document.getElementById("custom-category").value;
  const name = document.getElementById("custom-name").value.trim();
  if (!name) return alert("Enter a name");
  await api("/custom", { method: "POST", body: JSON.stringify({ category: cat, name }) });
  document.getElementById("custom-name").value = "";
  await loadCategories();
  alert("Added");
};

async function loadCategories() {
  try {
    const customs = await api("/custom");
    categories = structuredClone(BASE_CATEGORIES);
    customs.forEach(c => {
      if (categories[c.category] && !categories[c.category].includes(c.name)) {
        categories[c.category].push(c.name);
      }
    });
    populateCategorySelects();
  } catch (e) {
    populateCategorySelects();
  }
}

async function loadPast() {
  const periods = await api("/periods");
  const sel = document.getElementById("past-select");
  sel.innerHTML = periods.map(p =>
    `<option value="${p.id}">${p.label}${p.is_current ? " (current)" : ""}</option>`
  ).join("");
  sel.onchange = () => showPast(sel.value);
  if (periods.length) showPast(periods[0].id);
}

async function showPast(id) {
  const data = await api("/period/" + id);
  const s = data.summary;
  const el = document.getElementById("past-leftover");
  el.textContent = money(s.leftover);
  el.className = "amount " + (s.leftover >= 0 ? "positive" : "negative");
  document.getElementById("past-metrics").innerHTML = ["Income","Bills","Debt","Expenses","Savings"]
    .map(k => `<div class="metric"><div class="label">${k}</div><div class="value">${money(s[k])}</div></div>`).join("");
  document.getElementById("past-txns").innerHTML = (data.transactions || [])
    .map(t => `<div class="item"><div class="date">${t.date?.slice(5)}</div><div class="name">${t.subcategory}</div><div class="amount">${money(t.amount)}</div><div class="cat">${t.status}</div></div>`)
    .join("") || `<p class="muted">No transactions</p>`;
}

async function loadSettings() {
  const customs = await api("/custom");
  document.getElementById("custom-list").innerHTML = customs.length
    ? customs.map(c => `<div class="item"><div class="name">${c.category} → ${c.name}</div></div>`).join("")
    : `<p class="muted">None yet</p>`;
}

// Search
document.getElementById("search-input")?.addEventListener("input", doSearch);
document.getElementById("search-category")?.addEventListener("change", doSearch);

async function doSearch() {
  const q = document.getElementById("search-input").value;
  const cat = document.getElementById("search-category").value;
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (cat) params.set("category", cat);
  const results = await api("/search?" + params);
  document.getElementById("search-results").innerHTML = results.length
    ? results.map(t => `<div class="item"><div class="date">${t.date?.slice(5)}</div><div class="name">${t.subcategory}<div class="cat">${t.category}</div></div><div class="amount">${money(t.amount)}</div></div>`).join("")
    : `<p class="muted">No results</p>`;
}

// Init
document.getElementById("add-date").valueAsDate = new Date();
loadCategories().then(loadCurrent);
