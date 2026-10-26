"use strict";

const DATA_URL = "./data/aircraft.json";
const PAGE_SIZE = 30;
const el = {
  search: document.querySelector("#search-input"),
  sort: document.querySelector("#sort-select"),
  refresh: document.querySelector("#refresh-button"),
  clear: document.querySelector("#clear-button"),
  list: document.querySelector("#aircraft-list"),
  message: document.querySelector("#message-panel"),
  count: document.querySelector("#result-count"),
  page: document.querySelector("#page-label"),
  previous: document.querySelector("#previous-button"),
  next: document.querySelector("#next-button"),
  records: document.querySelector("#stat-records"),
  codes: document.querySelector("#stat-codes"),
  makers: document.querySelector("#stat-makers"),
  status: document.querySelector("#catalog-status"),
  updated: document.querySelector("#last-updated"),
};
let aircraft = [];
let results = [];
let page = 1;
let loadedAt = null;
let loading = false;
let loadError = null;

function clean(value) { return typeof value === "string" ? value.trim() : ""; }
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}
function number(value) { return new Intl.NumberFormat().format(value); }
function showMessage(message) {
  el.message.textContent = message;
  el.message.classList.toggle("visible", Boolean(message));
}
function updateStats() {
  el.records.textContent = number(aircraft.length);
  el.codes.textContent = number(aircraft.filter((record) => clean(record.icao_type_designator)).length);
  el.makers.textContent = number(new Set(aircraft.map((record) => clean(record.manufacturer).toLocaleLowerCase()).filter(Boolean)).size);
  el.status.textContent = loading ? "Updating…" : loadError && !aircraft.length ? "Unavailable" : "Ready";
  el.updated.textContent = loadedAt ? "Loaded " + loadedAt.toLocaleString() : loadError ? "Could not load catalog" : "Waiting for data";
}
function sortRecords(records) {
  const field = el.sort.value;
  return records.slice().sort((left, right) => {
    const a = clean(left[field]), b = clean(right[field]);
    if (!a && b) return 1;
    if (a && !b) return -1;
    return a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });
  });
}
function card(record) {
  const code = clean(record.icao_type_designator);
  const model = clean(record.model) || "Unknown model";
  const maker = clean(record.manufacturer) || "Unknown manufacturer";
  const description = clean(record.description);
  const source = clean(record.source) || "Source not recorded";
  const status = clean(record.verification_status) || "Unspecified";
  const unverified = status.toLowerCase() !== "verified";
  const url = clean(record.source_url);
  const sourceLink = /^https:\/\//i.test(url)
    ? '<a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">Open source ↗</a>'
    : "No source link recorded";
  return '<article class="aircraft-card"><div class="card-main">' +
    '<div class="icao-code' + (code ? "" : " no-code") + '">' + escapeHtml(code || "NO CODE") + '</div>' +
    '<div class="aircraft-name"><h3>' + escapeHtml(model) + '</h3><p>' + escapeHtml(maker) + (description ? " · " + escapeHtml(description) : "") + '</p></div>' +
    '<span class="card-badge' + (unverified ? " unverified" : "") + '">' + escapeHtml(status.replace(/_/g, " ")) + '</span></div>' +
    '<div class="card-details"><strong>Source:</strong> ' + escapeHtml(source) +
    ' &nbsp;·&nbsp; <strong>Source ID:</strong> ' + escapeHtml(clean(record.source_id) || "Not recorded") +
    ' &nbsp;·&nbsp; <strong>Retrieved:</strong> ' + escapeHtml(clean(record.source_retrieved_at) || "Unknown") +
    ' &nbsp;·&nbsp; ' + sourceLink + '</div></article>';
}
function updatePagination() {
  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  el.page.textContent = "Page " + page + " of " + pages;
  el.previous.disabled = page <= 1 || loading;
  el.next.disabled = page >= pages || loading;
}
function render() {
  if (loading && !aircraft.length) {
    el.list.innerHTML = "";
    showMessage("Loading the latest catalog…");
    el.count.textContent = "Loading catalog…";
    updatePagination();
    return;
  }
  if (loadError && !aircraft.length) {
    el.list.innerHTML = "";
    showMessage("The catalog could not be loaded. Check the deployed data path or connection, then try Refresh data.");
    el.count.textContent = "Catalog unavailable";
    updatePagination();
    return;
  }
  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  page = Math.min(page, pages);
  el.list.innerHTML = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map(card).join("");
  el.count.textContent = results.length === aircraft.length
    ? number(results.length) + " aircraft records"
    : number(results.length) + " of " + number(aircraft.length) + " records";
  showMessage(results.length ? "" : aircraft.length ? "No aircraft match your search. Try a model, manufacturer, or ICAO code." : "The catalog is empty. Run the scheduled refresh workflow to populate it.");
  updatePagination();
}
function filter() {
  const query = el.search.value.trim().toLocaleLowerCase();
  results = sortRecords(aircraft.filter((record) => {
    const haystack = [record.icao_type_designator, record.model, record.manufacturer, record.description, record.source]
      .map(clean).join(" ").toLocaleLowerCase();
    return !query || haystack.includes(query);
  }));
  page = 1;
  render();
}
async function loadCatalog() {
  if (loading) return;
  loading = true;
  loadError = null;
  el.refresh.disabled = true;
  el.refresh.innerHTML = '<span aria-hidden="true">↻</span> Loading…';
  updateStats();
  render();
  try {
    const response = await fetch(DATA_URL + "?v=" + Date.now(), {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("Catalog request failed with HTTP " + response.status);
    const payload = await response.json();
    if (!Array.isArray(payload) || payload.some((record) => !record || typeof record !== "object" || Array.isArray(record))) {
      throw new Error("Catalog JSON must be an array of aircraft objects");
    }
    aircraft = payload;
    loadedAt = new Date();
    filter();
  } catch (error) {
    loadError = error instanceof Error ? error.message : "Unknown catalog error";
    showMessage(aircraft.length ? "Refresh failed; showing the last loaded catalog. " + loadError : "Unable to load aircraft data. " + loadError + " Try Refresh data again.");
  } finally {
    loading = false;
    el.refresh.disabled = false;
    el.refresh.innerHTML = '<span aria-hidden="true">↻</span> Refresh data';
    updateStats();
    render();
  }
}
el.search.addEventListener("input", filter);
el.sort.addEventListener("change", filter);
el.refresh.addEventListener("click", loadCatalog);
el.clear.addEventListener("click", () => {
  el.search.value = "";
  el.sort.value = "manufacturer";
  filter();
  el.search.focus();
});
el.previous.addEventListener("click", () => {
  if (page > 1) { page -= 1; render(); el.list.scrollIntoView({ behavior: "smooth", block: "start" }); }
});
el.next.addEventListener("click", () => {
  if (page < Math.ceil(results.length / PAGE_SIZE)) { page += 1; render(); el.list.scrollIntoView({ behavior: "smooth", block: "start" }); }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
    event.preventDefault();
    el.search.focus();
  }
});
loadCatalog();
