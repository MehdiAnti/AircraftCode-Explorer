"use strict";

const DATA_URL = "./data/aircraft.json";
const REGISTRY_URL = "./data/registry";
const PAGE_SIZE = 30;
const SEARCH_DELAY = 120;
const SORT_FIELDS = ["manufacturer", "model", "icao_type_designator", "description"];
const REGISTRY_FIELDS = {
  icao24: "icao24",
  registration: "registration",
  typecode: "icao_type_designator",
  operator: "operator",
};
const el = {
  search: document.querySelector("#search-input"),
  mode: document.querySelector("#search-mode"),
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
let indexedAircraft = [];
let sortedIndexes = new Map();
let results = [];
let page = 1;
let loadedAt = null;
let loading = false;
let loadError = null;
let searchTimer = null;
let registrySearchSequence = 0;
let registrySearching = false;
let statusMessage = "";
const registryCache = new Map();

function clean(value) { return typeof value === "string" ? value.trim() : ""; }
function normalized(value) { return clean(value).toLocaleLowerCase(); }
function registryNormalized(value) { return clean(value).toLocaleLowerCase().replace(/[^a-z0-9]/g, ""); }
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
  el.makers.textContent = number(new Set(aircraft.map((record) => normalized(record.manufacturer)).filter(Boolean)).size);
  el.status.textContent = loading ? "Updating…" : loadError && !aircraft.length ? "Unavailable" : "Ready";
  el.updated.textContent = loadedAt ? "Loaded " + loadedAt.toLocaleString() : loadError ? "Could not load catalog" : "Waiting for data";
}
function buildSearchIndex(records) {
  indexedAircraft = records.map((record) => ({
    record,
    searchText: [
      record.icao_type_designator,
      record.model,
      record.manufacturer,
      record.description,
      record.source,
    ].map(normalized).filter(Boolean).join(" "),
    sortValues: Object.fromEntries(SORT_FIELDS.map((field) => [field, normalized(record[field])])),
  }));
  sortedIndexes = new Map();
}
function sortedIndex(field) {
  if (!sortedIndexes.has(field)) {
    sortedIndexes.set(field, indexedAircraft.slice().sort((left, right) => {
      const a = left.sortValues[field];
      const b = right.sortValues[field];
      if (!a && b) return 1;
      if (a && !b) return -1;
      return a.localeCompare(b, undefined, { numeric: true });
    }));
  }
  return sortedIndexes.get(field) || indexedAircraft;
}
function detailsMarkup(record, registryMode) {
  const fields = registryMode
    ? [
      ["Registration", record.registration],
      ["ICAO24 address", record.icao24],
      ["ICAO type code", record.icao_type_designator],
      ["Manufacturer ICAO", record.manufacturer_icao],
      ["Manufacturer", record.manufacturer],
      ["Model", record.model],
      ["Serial number", record.serial_number],
      ["Line number", record.line_number],
      ["ICAO aircraft type", record.icao_aircraft_type],
      ["Operator", record.operator],
      ["Callsign", record.operator_callsign],
      ["Operator ICAO", record.operator_icao],
      ["Operator IATA", record.operator_iata],
      ["Owner", record.owner],
      ["Test registration", record.test_registration],
      ["Registered", record.registered],
      ["Registration until", record.registration_until],
      ["Status", record.status],
      ["Built", record.built],
      ["First flight date", record.first_flight_date],
      ["Seat configuration", record.seat_configuration],
      ["Engines", record.engines],
      ["Modes", record.modes],
      ["ADS-B", record.adsb],
      ["ACARS", record.acars],
      ["Notes", record.notes],
      ["Category", record.category_description],
      ["Source", record.source],
      ["Retrieved at", record.source_retrieved_at],
    ]
    : [
      ["ICAO type code", record.icao_type_designator],
      ["Manufacturer", record.manufacturer],
      ["Model", record.model],
      ["Description", record.description],
      ["Source", record.source],
      ["Source ID", record.source_id],
      ["Retrieved at", record.source_retrieved_at],
    ];
  const content = fields.filter(([, value]) => clean(value)).map(([label, value]) =>
    '<div class="detail-field"><span>' + escapeHtml(label) + '</span><strong>' + escapeHtml(value) + '</strong></div>'
  ).join("");
  const url = clean(record.source_url);
  const sourceLink = /^https:\/\//i.test(url)
    ? '<a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">Open source ↗</a>'
    : "";
  return '<div class="card-details-content">' + content +
    (sourceLink ? '<div class="detail-source-link">' + sourceLink + '</div>' : "") +
    '<p class="detail-note">Imported source data is not independently verified.</p></div>';
}
function card(record, index) {
  const code = clean(record.icao_type_designator || record.typecode);
  const model = clean(record.model) || "Unknown model";
  const maker = clean(record.manufacturer) || "Unknown manufacturer";
  const registration = clean(record.registration);
  const operator = clean(record.operator);
  const description = clean(record.description);
  const registryMode = el.mode.value !== "catalog";
  const status = clean(record.verification_status) || "Unspecified";
  const unverified = status.toLowerCase() !== "verified";
  const subtitle = registryMode
    ? [maker, registration, operator].filter(Boolean).join(" · ")
    : [maker, description].filter(Boolean).join(" · ");
  const badge = registryMode ? "Individual aircraft" : status.replace(/_/g, " ");
  const detailId = "aircraft-detail-" + index;
  return '<article class="aircraft-card"><button class="card-main card-toggle" type="button" aria-expanded="false" aria-controls="' + detailId + '">' +
    '<span class="icao-code' + (code ? "" : " no-code") + '">' + escapeHtml(code || "NO CODE") + '</span>' +
    '<span class="aircraft-name"><span class="aircraft-title">' + escapeHtml(model) + '</span><span class="aircraft-subtitle">' + escapeHtml(subtitle || "Details unavailable") + '</span></span>' +
    '<span class="card-badge' + (unverified ? " unverified" : "") + '">' + escapeHtml(badge) + '</span></button>' +
    '<div id="' + detailId + '" class="card-details" hidden>' + detailsMarkup(record, registryMode) + '</div></article>';
}
function updatePagination() {
  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  el.page.textContent = "Page " + page + " of " + pages;
  el.previous.disabled = page <= 1 || loading || registrySearching;
  el.next.disabled = page >= pages || loading || registrySearching;
}
function render() {
  if (el.mode.value === "catalog" && loading && !aircraft.length) {
    el.list.innerHTML = "";
    showMessage("Loading the latest catalog…");
    el.count.textContent = "Loading catalog…";
    updatePagination();
    return;
  }
  if (el.mode.value === "catalog" && loadError && !aircraft.length) {
    el.list.innerHTML = "";
    showMessage("The catalog could not be loaded. Check the deployed data path or connection, then try Refresh data.");
    el.count.textContent = "Catalog unavailable";
    updatePagination();
    return;
  }
  const pages = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  page = Math.min(page, pages);
  el.list.innerHTML = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((item, index) => card(item.record, (page - 1) * PAGE_SIZE + index)).join("");
  if (el.mode.value === "catalog") {
    el.count.textContent = results.length === aircraft.length
      ? number(results.length) + " aircraft models"
      : number(results.length) + " of " + number(aircraft.length) + " models";
  } else {
    el.count.textContent = registrySearching ? "Searching registry…" : number(results.length) + " matching aircraft";
  }
  showMessage(registrySearching ? "Searching the aircraft registry…" : statusMessage || (results.length ? "" : "No matches found. Try a different search or search mode."));
  updatePagination();
}
function filterCatalog() {
  const query = normalized(el.search.value);
  const ordered = sortedIndex(el.sort.value);
  results = query ? ordered.filter((item) => item.searchText.includes(query)) : ordered;
  page = 1;
  statusMessage = "";
  render();
}
async function loadRegistryShard(mode, firstCharacter) {
  const key = mode + "/" + firstCharacter;
  if (registryCache.has(key)) return registryCache.get(key);
  const request = (async () => {
    const response = await fetch(REGISTRY_URL + "/" + mode + "/" + firstCharacter + ".json.gz", {
      cache: "no-cache",
      headers: { Accept: "application/gzip, application/json" },
    });
    if (response.status === 404) return [];
    if (!response.ok) throw new Error("Registry request failed with HTTP " + response.status);
    if (typeof DecompressionStream === "undefined") {
      throw new Error("This browser cannot decompress the registry data. Try a recent version of Chrome, Edge, Firefox, or Safari.");
    }
    const compressed = await response.arrayBuffer();
    const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream("gzip"));
    return JSON.parse(await new Response(stream).text());
  })();
  registryCache.set(key, request);
  try {
    const records = await request;
    if (!Array.isArray(records)) throw new Error("Invalid registry shard format");
    return records;
  } catch (error) {
    registryCache.delete(key);
    throw error;
  }
}
async function filterRegistry() {
  const sequence = ++registrySearchSequence;
  const mode = el.mode.value;
  const query = registryNormalized(el.search.value);
  const field = REGISTRY_FIELDS[mode];
  results = [];
  page = 1;
  statusMessage = "";
  if (query.length < 2) {
    registrySearching = false;
    statusMessage = "Enter at least 2 letters or numbers to search registrations, ICAO type codes, or operators.";
    render();
    return;
  }
  const firstCharacter = query.slice(0, 2);
  registrySearching = true;
  render();
  try {
    const records = await loadRegistryShard(mode, firstCharacter);
    if (sequence !== registrySearchSequence) return;
    results = records
      .filter((record) => registryNormalized(record[field]).startsWith(query))
      .map((record) => ({ record }));
    results.sort((left, right) =>
      registryNormalized(left.record[field]).localeCompare(registryNormalized(right.record[field]), undefined, { numeric: true })
    );
    statusMessage = "";
  } catch (error) {
    if (sequence !== registrySearchSequence) return;
    statusMessage = error instanceof Error ? error.message : "Unable to search the aircraft registry.";
  } finally {
    if (sequence === registrySearchSequence) {
      registrySearching = false;
      render();
    }
  }
}
function filter() {
  if (el.mode.value === "catalog") {
    registrySearchSequence += 1;
    registrySearching = false;
    filterCatalog();
  } else {
    filterRegistry();
  }
}
function scheduleSearch() {
  if (searchTimer !== null) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    searchTimer = null;
    filter();
  }, SEARCH_DELAY);
}
async function loadCatalog(forceRefresh = false) {
  if (loading) return;
  registryCache.clear();
  loading = true;
  loadError = null;
  el.refresh.disabled = true;
  el.refresh.innerHTML = '<span aria-hidden="true">↻</span> Loading…';
  updateStats();
  render();
  try {
    const url = forceRefresh ? DATA_URL + "?v=" + Date.now() : DATA_URL;
    const response = await fetch(url, {
      cache: forceRefresh ? "no-store" : "default",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("Catalog request failed with HTTP " + response.status);
    const payload = await response.json();
    if (!Array.isArray(payload) || payload.some((record) => !record || typeof record !== "object" || Array.isArray(record))) {
      throw new Error("Catalog JSON must be an array of aircraft objects");
    }
    aircraft = payload;
    buildSearchIndex(aircraft);
    loadedAt = new Date();
    loadError = null;
    filter();
  } catch (error) {
    loadError = error instanceof Error ? error.message : "Unknown catalog error";
    statusMessage = aircraft.length ? "Refresh failed; showing the last loaded catalog. " + loadError : "Unable to load aircraft data. " + loadError + " Try Refresh data again.";
  } finally {
    loading = false;
    el.refresh.disabled = false;
    el.refresh.innerHTML = '<span aria-hidden="true">↻</span> Refresh data';
    updateStats();
    if (el.mode.value === "catalog") render();
  }
}
el.search.addEventListener("input", scheduleSearch);
el.mode.addEventListener("change", () => {
  el.sort.closest(".sort-control").hidden = el.mode.value !== "catalog";
  const placeholders = {
    catalog: "Search model, manufacturer, ICAO code…",
    icao24: "Enter an ICAO24 address, e.g. abc123…",
    registration: "Enter a registration, e.g. N123AB…",
    typecode: "Enter an ICAO type code, e.g. B738…",
    operator: "Enter an operator name, e.g. Lufthansa…",
  };
  el.search.placeholder = placeholders[el.mode.value] || placeholders.catalog;
  filter();
});
el.sort.closest(".sort-control").hidden = el.mode.value !== "catalog";
el.sort.addEventListener("change", filter);
el.refresh.addEventListener("click", () => loadCatalog(true));
el.clear.addEventListener("click", () => {
  if (searchTimer !== null) clearTimeout(searchTimer);
  searchTimer = null;
  el.search.value = "";
  el.sort.value = "manufacturer";
  filter();
  el.search.focus();
});
el.list.addEventListener("click", (event) => {
  const toggle = event.target.closest(".card-toggle");
  if (!toggle) return;
  const details = document.getElementById(toggle.getAttribute("aria-controls"));
  if (!details) return;
  const expanded = toggle.getAttribute("aria-expanded") === "true";
  toggle.setAttribute("aria-expanded", String(!expanded));
  details.hidden = expanded;
  toggle.closest(".aircraft-card")?.classList.toggle("expanded", !expanded);
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
