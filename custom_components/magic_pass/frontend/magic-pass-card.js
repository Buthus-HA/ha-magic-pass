/* Magic Pass card for Home Assistant — bundled with the magic_pass integration.
 * type: custom:magic-pass-card
 * Options: title, entry_id (if several entries), favorites (list of resort names shown in bold),
 *          only_open (bool, default false), only_favorites (bool, default false), hide_tiles (bool)
 */
const MP_I18N = {
  fr: {
    title: "Stations par temps de trajet", search: "Rechercher une station, un canton, un pays…", onlyOpen: "Ouvertes seulement", onlyFav: "Favoris seulement", kmTip: "Couleur : rouge < 20 % du domaine ouvert, orange 20–66 %, vert > 66 %",
    open: "Domaines ouverts", openN: (n, t) => `${n} domaine${n > 1 ? "s" : ""} sur ${t}`, best: (h) => `Meilleure < ${h}h`, none: "Aucune · 0",
    updated: "Mise à jour", refresh: "Actualiser", station: "Station", travel: "Trajet", trails: "Pistes", vb: "%V+B",
    vbTip: "Part des pistes vertes et bleues", status: "Statut", lifts: "Remontées", km: "Km ouverts", pct: "% ouvert",
    snow: "Neige 72h", wx: "Météo", score: "Note", isOpen: "Ouverte", partial: "Partiellement", walk: "Ouverte (piéton)",
    closed: "Fermée", noMatch: "Aucune station ne correspond.", loading: "Chargement…",
    noEntry: "Aucune entrée Magic Pass chargée. Ajoute l'intégration dans Paramètres → Appareils et services.",
    now: "à l'instant", ago: (v, u) => `il y a ${v} ${u}`, units: ["min", "h", "j"],
    foot: (src) => `Sources : magicpass.ch · ${src === "osrm" ? "trajets en voiture (OSRM, sans trafic)" : "trajets estimés à vol d'oiseau"} · neige et météo Open-Meteo. Note /10 : 40 % ouverture, 30 % neige fraîche, 20 % météo, 10 % trajet.`,
  },
  en: {
    title: "Resorts by travel time", search: "Search a resort, canton, country…", onlyOpen: "Open only", onlyFav: "Favourites only", kmTip: "Colour: red < 20 % of the area open, orange 20–66 %, green > 66 %",
    open: "Open resorts", openN: (n, t) => `${n} of ${t} resorts`, best: (h) => `Best < ${h}h`, none: "None · 0",
    updated: "Updated", refresh: "Refresh", station: "Resort", travel: "Travel", trails: "Runs", vb: "%G+B",
    vbTip: "Share of green and blue runs", status: "Status", lifts: "Lifts", km: "Km open", pct: "% open",
    snow: "Snow 72h", wx: "Weather", score: "Score", isOpen: "Open", partial: "Partly open", walk: "Open (walking)",
    closed: "Closed", noMatch: "No resort matches.", loading: "Loading…",
    noEntry: "No Magic Pass entry is loaded. Add the integration under Settings → Devices & services.",
    now: "just now", ago: (v, u) => `${v} ${u} ago`, units: ["min", "h", "d"],
    foot: (src) => `Sources: magicpass.ch · ${src === "osrm" ? "driving times (OSRM, no traffic)" : "estimated straight-line travel times"} · snow and weather by Open-Meteo. Score /10: 40 % opening, 30 % fresh snow, 20 % weather, 10 % travel.`,
  },
  de: {
    title: "Skigebiete nach Fahrzeit", search: "Skigebiet, Kanton, Land suchen…", onlyOpen: "Nur offene", onlyFav: "Nur Favoriten", kmTip: "Farbe: rot < 20 % offen, orange 20–66 %, grün > 66 %",
    open: "Offene Skigebiete", openN: (n, t) => `${n} von ${t} Skigebieten`, best: (h) => `Bestes < ${h} h`, none: "Keines · 0",
    updated: "Aktualisiert", refresh: "Aktualisieren", station: "Skigebiet", travel: "Fahrzeit", trails: "Pisten", vb: "%G+B",
    vbTip: "Anteil grüne und blaue Pisten", status: "Status", lifts: "Anlagen", km: "Km offen", pct: "% offen",
    snow: "Schnee 72h", wx: "Wetter", score: "Note", isOpen: "Offen", partial: "Teilweise", walk: "Offen (Fussgänger)",
    closed: "Geschlossen", noMatch: "Kein Skigebiet gefunden.", loading: "Laden…",
    noEntry: "Keine Magic-Pass-Integration geladen. Unter Einstellungen → Geräte & Dienste hinzufügen.",
    now: "gerade eben", ago: (v, u) => `vor ${v} ${u}`, units: ["Min.", "Std.", "T."],
    foot: (src) => `Quellen: magicpass.ch · ${src === "osrm" ? "Autofahrzeiten (OSRM, ohne Verkehr)" : "geschätzte Fahrzeiten (Luftlinie)"} · Schnee und Wetter von Open-Meteo. Note /10: 40 % Öffnung, 30 % Neuschnee, 20 % Wetter, 10 % Fahrzeit.`,
  },
};

const mpEsc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const mpTravel = (m) => (m == null ? "–" : m < 60 ? `${m} min` : `${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}`);
const mpKm = (v) => (Number.isInteger(v) ? v : Number(v).toFixed(1));

class MagicPassCard extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = { favorites: [], ...config };
    this._sort = { k: "travel", dir: 1 };
    this._q = "";
    this._onlyOpen = !!this._config.only_open;
    this._onlyFav = !!this._config.only_favorites;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  get _t() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "fr").slice(0, 2);
    return MP_I18N[lang] || MP_I18N.en;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._render();
      this._subscribe();
    }
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._subscribe();
    this._tick = setInterval(() => this._renderHeader(), 60000);
  }

  disconnectedCallback() {
    clearInterval(this._tick);
    if (this._unsub) {
      this._unsub.then((u) => u && u()).catch(() => {});
      this._unsub = null;
    }
  }

  getCardSize() {
    return 12;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }

  _subscribe() {
    if (!this._hass || this._unsub) return;
    const msg = { type: "magic_pass/subscribe" };
    if (this._config.entry_id) msg.entry_id = this._config.entry_id;
    this._unsub = this._hass.connection
      .subscribeMessage((data) => {
        this._data = data;
        this._err = null;
        this._spinning = false;
        this._render();
      }, msg)
      .catch((e) => {
        this._err = e?.code === "not_found" ? this._t.noEntry : e?.message || String(e);
        this._unsub = null;
        this._render();
      });
  }

  async _refresh() {
    this._spinning = true;
    this.shadowRoot.querySelector("#refresh")?.classList.add("spin");
    const msg = { type: "magic_pass/refresh" };
    if (this._config.entry_id) msg.entry_id = this._config.entry_id;
    try {
      await this._hass.callWS(msg);
    } finally {
      this._spinning = false;
      this.shadowRoot.querySelector("#refresh")?.classList.remove("spin");
    }
  }

  _rel(iso) {
    const t = this._t;
    if (!iso) return "–";
    const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (m < 1) return t.now;
    if (m < 60) return t.ago(m, t.units[0]);
    const h = Math.round(m / 60);
    return h < 24 ? t.ago(h, t.units[1]) : t.ago(Math.round(h / 24), t.units[2]);
  }

  get _cols() {
    const t = this._t;
    return [
      { k: "name", l: t.station, s: (a) => a.name.toLowerCase() },
      { k: "travel", l: t.travel, s: (a) => a.travel ?? 1e9 },
      { k: "trails", l: t.trails, s: (a) => a.trails || 0, d: -1 },
      { k: "vb", l: t.vb, s: (a) => a.vb ?? -1, d: -1, tip: t.vbTip },
      { k: "state", l: t.status, s: (a) => (a.open ? 0 : 1) },
      { k: "lifts", l: t.lifts, s: (a) => a.lifts_open, d: -1 },
      { k: "km", l: t.km, s: (a) => a.km_open, d: -1, tip: t.kmTip },
      { k: "pct", l: t.pct, s: (a) => a.pct_open, d: -1 },
      { k: "snow", l: t.snow, s: (a) => a.weather?.snow72 ?? -1, d: -1 },
      { k: "wx", l: t.wx, s: (a) => a.weather?.tmax ?? -99, d: -1 },
      { k: "score", l: t.score, s: (a) => a.score, d: -1 },
    ];
  }

  _rows() {
    const d = this._data;
    if (!d) return [];
    const q = this._q.trim().toLowerCase();
    const col = this._cols.find((c) => c.k === this._sort.k) || this._cols[1];
    return d.stations
      .filter((s) => (!this._onlyOpen || s.open) && (!this._onlyFav || (this._config.favorites || []).includes(s.name)) && (!q || [s.name, s.region, s.state].join(" ").toLowerCase().includes(q)))
      .sort((a, b) => {
        const x = col.s(a), y = col.s(b);
        return (x < y ? -1 : x > y ? 1 : 0) * this._sort.dir || (a.travel ?? 1e9) - (b.travel ?? 1e9);
      });
  }

  _status(s) {
    const t = this._t;
    if (s.open) {
      const label = s.state.toLowerCase().startsWith("partiel") ? t.partial : /walk|pieton|pedestrian/.test(s.kind) ? t.walk : t.isOpen;
      return `<span class="st ok"><i class="dot g"></i>${label}</span>`;
    }
    return `<span class="st ko"><i class="dot r"></i>${t.closed}${s.opening ? ` · ${s.opening}` : ""}</span>`;
  }

  _lvl(s) {
    if (!s.open) return "r";
    const r = s.km_total ? s.km_open / s.km_total : s.lifts_total ? s.lifts_open / s.lifts_total : 1;
    return r > 0.66 ? "g" : r >= 0.2 ? "o" : "r";
  }

  _row(s) {
    const fav = (this._config.favorites || []).includes(s.name);
    const w = s.weather;
    const sc = s.score;
    const cls = sc >= 7 ? "g" : sc >= 4 ? "y" : sc > 0 ? "o" : "r";
    return `<tr data-url="${mpEsc(s.url)}" title="${mpEsc(s.info || "")}">
      <td class="name${fav ? " fav" : ""}">${mpEsc(s.name)}${s.region ? `<small>${mpEsc(s.region)}</small>` : ""}</td>
      <td>${mpTravel(s.travel)}${s.travel != null && this._data.travel_source !== "osrm" ? " ≈" : ""}</td>
      <td>${s.trails || "–"}</td>
      <td>${s.vb != null ? s.vb + " %" : "–"}</td>
      <td>${this._status(s)}</td>
      <td>${s.lifts_open}/${s.lifts_total}</td>
      <td><span class="lvl ${this._lvl(s)}">${mpKm(s.km_open)}/${mpKm(s.km_total)}</span></td>
      <td>${s.pct_open} %</td>
      <td>${w ? (w.snow72 > 0 ? `<b>${w.snow72} cm</b>` : "0 cm") : "–"}</td>
      <td>${w ? `${w.icon} ${Math.round(w.tmax)}°` : "–"}</td>
      <td><span class="sc ${cls}">${sc}</span></td>
    </tr>`;
  }

  _renderHeader() {
    const d = this._data;
    const el = this.shadowRoot?.querySelector(".tiles");
    if (!el) return;
    if (this._config.hide_tiles || !d) {
      el.innerHTML = "";
      return;
    }
    const t = this._t;
    const b = d.best;
    el.innerHTML = `
      <div class="tile"><ha-icon icon="mdi:ski"></ha-icon><div><b>${t.open}</b><span>${t.openN(d.open, d.count)}</span></div></div>
      <div class="tile" ${b ? `data-url="${mpEsc(b.url)}"` : ""}><ha-icon icon="mdi:trophy-outline"></ha-icon><div><b>${t.best(Math.round(d.max_travel / 60))}</b><span>${b ? `${mpEsc(b.name)} · ${b.score} · ${mpTravel(b.travel)}` : t.none}</span></div></div>
      <div class="tile"><ha-icon icon="mdi:update"></ha-icon><div><b>${t.updated}</b><span>${this._rel(d.updated)}</span></div></div>`;
    el.querySelectorAll("[data-url]").forEach((x) => (x.onclick = () => window.open(x.dataset.url, "_blank", "noopener")));
  }

  _render() {
    const root = this.shadowRoot;
    if (!root) return;
    const t = this._t;
    if (!root.querySelector("ha-card")) {
      root.innerHTML = `<style>${MagicPassCard.css}</style>
        <div class="tiles"></div>
        <ha-card>
          <div class="bar">
            <div class="title">${mpEsc(this._config.title || t.title)}</div>
            <div class="search"><ha-icon icon="mdi:magnify"></ha-icon><input id="q" placeholder="${mpEsc(t.search)}"></div>
            <label class="chk"><input type="checkbox" id="open" ${this._onlyOpen ? "checked" : ""}> ${t.onlyOpen}</label>
            ${(this._config.favorites || []).length ? `<label class="chk"><input type="checkbox" id="fav" ${this._onlyFav ? "checked" : ""}> ${t.onlyFav}</label>` : ""}
            <span class="count" id="count"></span>
            <ha-icon-button id="refresh" label="${t.refresh}"><ha-icon icon="mdi:refresh"></ha-icon></ha-icon-button>
          </div>
          <div class="wrap"><table><thead><tr></tr></thead><tbody></tbody></table></div>
          <div class="foot" id="foot"></div>
        </ha-card>`;
      root.querySelector("#q").addEventListener("input", (e) => { this._q = e.target.value; this._renderBody(); });
      root.querySelector("#open").addEventListener("change", (e) => { this._onlyOpen = e.target.checked; this._renderBody(); });
      root.querySelector("#fav")?.addEventListener("change", (e) => { this._onlyFav = e.target.checked; this._renderBody(); });
      root.querySelector("#refresh").addEventListener("click", () => this._refresh());
    }
    this._renderHeader();
    this._renderBody();
  }

  _renderBody() {
    const root = this.shadowRoot;
    const t = this._t;
    const head = root.querySelector("thead tr");
    head.innerHTML = this._cols
      .map((c) => `<th data-k="${c.k}" ${c.tip ? `title="${mpEsc(c.tip)}"` : ""}>${c.l}${this._sort.k === c.k ? (this._sort.dir > 0 ? " ▲" : " ▼") : ""}</th>`)
      .join("");
    head.querySelectorAll("th").forEach((th) => (th.onclick = () => {
      const col = this._cols.find((c) => c.k === th.dataset.k);
      this._sort = { k: col.k, dir: this._sort.k === col.k ? -this._sort.dir : col.d || 1 };
      this._renderBody();
    }));
    const body = root.querySelector("tbody");
    if (!this._data) {
      body.innerHTML = `<tr><td colspan="11" class="empty">${mpEsc(this._err || t.loading)}</td></tr>`;
      root.querySelector("#count").textContent = "";
      root.querySelector("#foot").textContent = "";
      return;
    }
    const rows = this._rows();
    body.innerHTML = rows.length ? rows.map((s) => this._row(s)).join("") : `<tr><td colspan="11" class="empty">${t.noMatch}</td></tr>`;
    body.querySelectorAll("tr[data-url]").forEach((r) => (r.onclick = () => window.open(r.dataset.url, "_blank", "noopener")));
    root.querySelector("#count").textContent = `${rows.length} / ${this._data.count}`;
    root.querySelector("#foot").textContent = t.foot(this._data.travel_source);
  }
}

MagicPassCard.css = `
  :host { display:block; }
  .tiles { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:8px; }
  .tiles:empty { display:none; }
  .tile { display:flex; gap:12px; align-items:center; padding:12px 16px; border-radius:var(--ha-card-border-radius,12px);
    background:var(--ha-card-background,var(--card-background-color)); border:1px solid var(--divider-color); }
  .tile[data-url] { cursor:pointer; }
  .tile ha-icon { color:var(--primary-color); --mdc-icon-size:22px; }
  .tile b { display:block; font-weight:500; }
  .tile span { font-size:12px; color:var(--secondary-text-color); }
  ha-card { overflow:hidden; }
  .bar { display:flex; flex-wrap:wrap; gap:12px; align-items:center; padding:12px 16px; }
  .title { font-size:18px; font-weight:500; flex:1 1 auto; }
  .search { display:flex; align-items:center; gap:6px; border:1px solid var(--divider-color); border-radius:20px; padding:4px 12px; min-width:260px; }
  .search ha-icon { --mdc-icon-size:18px; color:var(--secondary-text-color); }
  .search input { border:none; outline:none; background:transparent; color:var(--primary-text-color); font:inherit; width:100%; }
  .chk { display:flex; gap:6px; align-items:center; font-size:14px; cursor:pointer; }
  .count { font-size:12px; color:var(--secondary-text-color); }
  #refresh.spin ha-icon { animation:spin 1s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .wrap { overflow-x:auto; }
  table { width:100%; border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; }
  th { text-align:left; font-weight:500; color:var(--secondary-text-color); padding:8px 10px; border-bottom:1px solid var(--divider-color);
    cursor:pointer; white-space:nowrap; user-select:none; }
  td { padding:7px 10px; border-bottom:1px solid var(--divider-color); white-space:nowrap; }
  tbody tr { cursor:pointer; }
  tbody tr:hover { background:var(--secondary-background-color); }
  .name small { display:block; font-size:11px; color:var(--secondary-text-color); }
  .name.fav { font-weight:600; }
  .st.ok { color:var(--success-color,#43a047); font-weight:500; }
  .st { display:inline-flex; align-items:center; gap:6px; }
  .dot { display:inline-block; width:10px; height:10px; border-radius:50%; flex:none; }
  .dot.g { background:var(--success-color,#43a047); }
  .dot.r { background:var(--error-color,#db4437); }
  .lvl { display:inline-block; border-radius:10px; padding:2px 8px; font-weight:600; font-size:12px; color:#fff; }
  .lvl.r { background:var(--error-color,#db4437); }
  .lvl.o { background:#f57c00; }
  .lvl.g { background:var(--success-color,#43a047); }
  .sc { display:inline-block; min-width:26px; text-align:center; border-radius:10px; padding:2px 8px; color:#fff; font-weight:600; font-size:12px; }
  .sc.r { background:var(--error-color,#db4437); }
  .sc.o { background:#f57c00; }
  .sc.y { background:#f9a825; }
  .sc.g { background:var(--success-color,#43a047); }
  .empty { text-align:center; color:var(--secondary-text-color); padding:24px; white-space:normal; }
  .foot { font-size:11px; color:var(--secondary-text-color); padding:8px 16px 12px; }
  @media (max-width:700px) { .tiles { grid-template-columns:1fr; } .search { min-width:0; flex:1 1 100%; } }
`;

if (!customElements.get("magic-pass-card")) customElements.define("magic-pass-card", MagicPassCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "magic-pass-card")) {
  window.customCards.push({
    type: "magic-pass-card",
    name: "Magic Pass",
    description: "Magic Pass resorts sorted by travel time, with snow, weather and a score.",
    preview: false,
    documentationURL: "https://github.com/Buthus-HA/ha-magic-pass",
  });
}
