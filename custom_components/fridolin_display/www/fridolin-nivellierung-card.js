/**
 * Fridolin Nivellierung - Lovelace-Karte
 *
 * Zeigt dieselbe Kreuzlibelle wie die Nivellierungs-Seite auf dem
 * Wohnwagen-Display, aber auf einem Fahrzeug-Grundriss mit der Front
 * NACH OBEN (statt nach rechts wie im Display) - passend zur klassischen
 * "Draufsicht von vorne" auf einem Dashboard. Wahlweise als Wohnwagen
 * (Deichsel) oder Wohnmobil (Frontscheibe) darstellbar, einstellbar im
 * Karteneditor (vehicle_type).
 *
 * Bindet an zwei bestehende ESPHome-Sensoren (Neigung links/rechts,
 * Neigung vorne/hinten) und einen "Neigung nullen"-Knopf - alle drei
 * werden von der ESPHome-Firmware selbst bereitgestellt (siehe
 * esphome/wohnwagen-display.yaml bzw. test-esp32-ohne-display.yaml).
 * Ein Druck auf "Nullen" ruft button.press auf genau dieser Entity auf,
 * der Nullpunkt wird also - wie beim Knopf auf dem Display selbst - lokal
 * auf dem ESP gespeichert (übersteht auch einen Neustart von Home
 * Assistant, weil er nicht in HA, sondern im Flash des ESP liegt).
 *
 * Einbindung (siehe README.md):
 *   1. Einstellungen -> Dashboards -> Ressourcen -> Ressource hinzufügen
 *      URL: /fridolin_display/fridolin-nivellierung-card.js
 *      Typ: JavaScript-Modul
 *   2. Karte hinzufügen:
 *        type: custom:fridolin-nivellierung-card
 *        vehicle_type: caravan   # oder: motorhome
 *        # Optional, falls deine Entity-IDs abweichen:
 *        entity_lr: sensor.fridolin_display_neigung_links_rechts
 *        entity_vh: sensor.fridolin_display_neigung_vorne_hinten
 *        entity_zero_button: button.fridolin_display_neigung_nullen
 */

const CARAVAN_SVG_BODY = `
  <defs>
    <linearGradient id="fwGradV" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#D7EA82"/><stop offset="1" stop-color="#7FA119"/>
    </linearGradient>
    <linearGradient id="fwGradH" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#D7EA82"/><stop offset="1" stop-color="#7FA119"/>
    </linearGradient>
  </defs>
  <rect x="30" y="55" width="350" height="170" rx="45" fill="#17212C" stroke="#3A4250" stroke-width="4"/>
  <path d="M380,120 L432,140 L380,160 Z" fill="#55606F"/>
  <circle cx="432" cy="140" r="7" fill="#C9D2DC" stroke="#3A4250" stroke-width="2"/>
  <line x1="150" y1="65" x2="150" y2="215" stroke="#202836" stroke-width="2" opacity="0.6"/>
  <line x1="260" y1="65" x2="260" y2="215" stroke="#202836" stroke-width="2" opacity="0.6"/>

  <circle cx="58" cy="92" r="11" fill="#2B3542" stroke="#55606F" stroke-width="2"/>
  <line x1="49" y1="88" x2="67" y2="88" stroke="#55606F" stroke-width="1.5"/>
  <line x1="49" y1="96" x2="67" y2="96" stroke="#55606F" stroke-width="1.5"/>
  <circle cx="58" cy="196" r="11" fill="#2B3542" stroke="#55606F" stroke-width="2"/>
  <line x1="49" y1="192" x2="67" y2="192" stroke="#55606F" stroke-width="1.5"/>
  <line x1="49" y1="200" x2="67" y2="200" stroke="#55606F" stroke-width="1.5"/>
  <rect x="130" y="188" width="50" height="24" rx="6" fill="#2B3542" stroke="#55606F" stroke-width="2"/>
  <line x1="155" y1="196" x2="155" y2="204" stroke="#55606F" stroke-width="2"/>

  <rect x="80" y="113" width="150" height="54" rx="27" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <rect x="86" y="119" width="138" height="42" rx="21" fill="url(#fwGradV)"/>
  <line x1="136" y1="129" x2="136" y2="151" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <line x1="174" y1="129" x2="174" y2="151" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <rect x="270" y="65" width="54" height="150" rx="27" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <rect x="276" y="71" width="42" height="138" rx="21" fill="url(#fwGradH)"/>
  <line x1="286" y1="121" x2="308" y2="121" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <line x1="286" y1="159" x2="308" y2="159" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
`;

const MOTORHOME_SVG_BODY = `
  <defs>
    <linearGradient id="fwGradV" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#D7EA82"/><stop offset="1" stop-color="#7FA119"/>
    </linearGradient>
    <linearGradient id="fwGradH" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#D7EA82"/><stop offset="1" stop-color="#7FA119"/>
    </linearGradient>
    <linearGradient id="fwGradGlass" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#8FD6F2"/><stop offset="1" stop-color="#3FA8DC"/>
    </linearGradient>
  </defs>
  <rect x="10" y="10" width="360" height="150" rx="26" fill="#17212C" stroke="#3A4250" stroke-width="4"/>

  <path d="M322,18 L364,42 L364,128 L322,150 Z" fill="url(#fwGradGlass)" stroke="#17212C" stroke-width="3"/>
  <line x1="343" y1="22" x2="343" y2="148" stroke="#17212C" stroke-width="2" opacity="0.7"/>
  <rect x="364" y="30" width="6" height="10" rx="3" fill="#55606F"/>
  <rect x="364" y="110" width="6" height="10" rx="3" fill="#55606F"/>

  <rect x="30" y="16" width="90" height="32" rx="8" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <circle cx="55" cy="32" r="7" fill="#17212C" stroke="#55606F" stroke-width="2"/>
  <circle cx="80" cy="32" r="7" fill="#17212C" stroke="#55606F" stroke-width="2"/>
  <rect x="95" y="22" width="18" height="18" rx="4" fill="#17212C" stroke="#55606F" stroke-width="2"/>

  <rect x="70" y="63" width="150" height="44" rx="22" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <rect x="76" y="69" width="138" height="32" rx="16" fill="url(#fwGradV)"/>
  <line x1="126" y1="74" x2="126" y2="96" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <line x1="164" y1="74" x2="164" y2="96" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>

  <rect x="255" y="20" width="44" height="130" rx="22" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <rect x="261" y="26" width="32" height="118" rx="16" fill="url(#fwGradH)"/>
  <line x1="266" y1="66" x2="288" y2="66" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <line x1="266" y1="104" x2="288" y2="104" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
`;

const RANGE_DEG = 8;

// Pro Fahrzeugtyp: eigenes SVG, sein viewBox (für die Prozent-Positionierung
// der Blasen) und die Bewegungsbereiche der beiden Röhren in SVG-Einheiten.
const VEHICLE_ART = {
  caravan: {
    svg: CARAVAN_SVG_BODY,
    viewBox: { x: 10, y: 35, w: 449, h: 210 },
    hCenter: { x: 155, y: 140 },
    hRange: [118, 192], // Vorne/Hinten-Röhre, Blase bewegt sich in X
    vCenter: { x: 297, y: 140 },
    vRange: [103, 177], // Links/Rechts-Röhre, Blase bewegt sich in Y
  },
  motorhome: {
    svg: MOTORHOME_SVG_BODY,
    viewBox: { x: -10, y: -10, w: 400, h: 190 },
    hCenter: { x: 145, y: 85 },
    hRange: [108, 182],
    vCenter: { x: 277, y: 85 },
    vRange: [58, 112],
  },
};

const CARD_STYLE = `
  :host { display: block; }
  ha-card { padding: 14px 16px 16px; }
  .fw-title { font-size: 1.5em; font-weight: 600; text-align: center; margin: 2px 0 6px; }
  .fw-outer {
    position: relative;
    width: 100%;
    /* Höhe wird passend zum Seitenverhältnis pro Fahrzeugtyp in _layout()
       direkt in Pixeln gesetzt (nicht per padding-top-Prozent-Trick: der
       bezieht sich auf die Breite des Elternelements, nicht auf die per
       max-width begrenzte eigene Breite - würde hier zu hoch ausfallen). */
    max-width: 260px;
    margin: 0 auto;
  }
  .fw-inner {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-90deg);
  }
  .fw-inner svg { display: block; }
  .fw-bubble {
    position: absolute;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #fffef2, #e6dfa0 75%);
    border: 1px solid #b9ae63;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    translate: -50% -50%;
    transition: border-color 150ms ease, border-width 150ms ease, left 200ms ease, top 200ms ease;
  }
  .fw-bubble.level { border-color: #3fa34d; border-width: 3px; }
  .fw-values {
    display: flex;
    justify-content: center;
    gap: 28px;
    margin-top: 8px;
    font-size: 0.9em;
    color: var(--secondary-text-color);
  }
  .fw-values b {
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
    margin-left: 4px;
  }
  .fw-footer {
    display: flex;
    justify-content: center;
    margin-top: 8px;
  }
  .fw-zero-btn {
    appearance: none;
    border: none;
    border-radius: 20px;
    padding: 10px 32px;
    font-size: 0.95em;
    font-weight: 600;
    font-family: inherit;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: #fff;
    background: var(--primary-color, #3fa8dc);
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    cursor: pointer;
    transition: filter 150ms ease, box-shadow 150ms ease, transform 100ms ease;
  }
  .fw-zero-btn:hover { filter: brightness(1.08); box-shadow: 0 3px 8px rgba(0,0,0,0.3); }
  .fw-zero-btn:active { filter: brightness(0.95); transform: translateY(1px); box-shadow: 0 1px 3px rgba(0,0,0,0.25); }
  .fw-unavailable {
    text-align: center;
    color: var(--secondary-text-color);
    padding: 24px 0;
  }
`;

// Editor für die Karten-Konfiguration im UI-Karteneditor ("Karte bearbeiten"),
// statt die Entity-IDs und den Titel nur per YAML setzen zu können. Nutzt
// <ha-form>, das im Home-Assistant-Frontend bereits global registriert ist
// (kein eigener Import nötig) - derselbe Ansatz wie bei den meisten anderen
// Custom Cards.
class FridolinNivellierungCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get _schema() {
    return [
      { name: "title", selector: { text: {} } },
      {
        name: "vehicle_type",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "caravan", label: "Wohnwagen" },
              { value: "motorhome", label: "Wohnmobil" },
            ],
          },
        },
      },
      { name: "entity_lr", selector: { entity: { domain: "sensor" } } },
      { name: "entity_vh", selector: { entity: { domain: "sensor" } } },
      { name: "entity_zero_button", selector: { entity: { domain: "button" } } },
    ];
  }

  _computeLabel(schema) {
    const labels = {
      title: "Titel",
      vehicle_type: "Fahrzeugtyp",
      entity_lr: "Sensor Links/Rechts",
      entity_vh: "Sensor Vorne/Hinten",
      entity_zero_button: "Nullen-Button",
    };
    return labels[schema.name] || schema.name;
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = this._schema;
    this._form.computeLabel = this._computeLabel;
  }
}

customElements.define("fridolin-nivellierung-card-editor", FridolinNivellierungCardEditor);

class FridolinNivellierungCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("fridolin-nivellierung-card-editor");
  }

  static getStubConfig() {
    return {
      title: "Nivellierung",
      vehicle_type: "caravan",
      entity_lr: "sensor.fridolin_display_neigung_links_rechts",
      entity_vh: "sensor.fridolin_display_neigung_vorne_hinten",
      entity_zero_button: "button.fridolin_display_neigung_nullen",
    };
  }

  setConfig(config) {
    this._config = {
      entity_lr: "sensor.fridolin_display_neigung_links_rechts",
      entity_vh: "sensor.fridolin_display_neigung_vorne_hinten",
      entity_zero_button: "button.fridolin_display_neigung_nullen",
      title: "Nivellierung",
      vehicle_type: "caravan",
      ...config,
    };
    if (this._built) this._render();
    else this._build();
  }

  getCardSize() {
    return 4;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._render();
  }

  _art() {
    return VEHICLE_ART[this._config.vehicle_type] || VEHICLE_ART.caravan;
  }

  _build() {
    if (this._built || !this._config) return;
    this._built = true;

    const style = document.createElement("style");
    style.textContent = CARD_STYLE;

    const art = this._art();
    const vb = art.viewBox;

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <div class="fw-title">${this._config.title}</div>
      <div class="fw-outer">
        <div class="fw-inner">
          <svg id="fwSvg" viewBox="${vb.x} ${vb.y} ${vb.w} ${vb.h}" xmlns="http://www.w3.org/2000/svg">
            ${art.svg}
          </svg>
          <div class="fw-bubble" id="fwBubbleVh" style="width:34px;height:18px;"></div>
          <div class="fw-bubble" id="fwBubbleLr" style="width:18px;height:34px;"></div>
        </div>
      </div>
      <div class="fw-values">
        <span>Links/Rechts:<b id="fwValLr">--</b></span>
        <span>Vorne/Hinten:<b id="fwValVh">--</b></span>
      </div>
      <div class="fw-footer">
        <button class="fw-zero-btn" id="fwZeroBtn">Nullen</button>
      </div>
    `;

    this.innerHTML = "";
    this.appendChild(style);
    this.appendChild(card);

    this._els = {
      title: card.querySelector(".fw-title"),
      svg: card.querySelector("#fwSvg"),
      inner: card.querySelector(".fw-inner"),
      outer: card.querySelector(".fw-outer"),
      bubbleVh: card.querySelector("#fwBubbleVh"),
      bubbleLr: card.querySelector("#fwBubbleLr"),
      valLr: card.querySelector("#fwValLr"),
      valVh: card.querySelector("#fwValVh"),
      zeroBtn: card.querySelector("#fwZeroBtn"),
    };

    this._currentVehicleType = this._config.vehicle_type;
    this._els.zeroBtn.addEventListener("click", () => this._pressZero());

    // Größe des gedrehten Grundrisses an die tatsächliche Kartenbreite anpassen
    this._resizeObserver = new ResizeObserver(() => this._layout());
    this._resizeObserver.observe(this._els.outer);
    this._layout();
  }

  // Wechselt SVG-Grafik + viewBox, falls der Fahrzeugtyp im Editor geändert wurde
  _syncVehicleArt() {
    if (!this._els || this._currentVehicleType === this._config.vehicle_type) return;
    this._currentVehicleType = this._config.vehicle_type;
    const art = this._art();
    const vb = art.viewBox;
    this._els.svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    this._els.svg.innerHTML = art.svg;
    this._layout();
  }

  _layout() {
    if (!this._els) return;
    const vb = this._art().viewBox;
    const outerWidth = this._els.outer.clientWidth;
    if (!outerWidth) return;
    // Nach der Drehung um 90° wird aus der Breite des Grundrisses die Höhe
    // im Kartenlayout, und umgekehrt - daher hier getauscht: die
    // "unrotierte" Breite richtet sich nach der Kartenhöhe. Höhe direkt in
    // Pixeln setzen (nicht per padding-top-Prozent, siehe CSS-Kommentar).
    const outerHeight = outerWidth * (vb.w / vb.h);
    this._els.outer.style.height = outerHeight + "px";
    const innerWidth = outerHeight;
    const innerHeight = outerWidth;
    this._els.inner.style.width = innerWidth + "px";
    this._els.inner.style.height = innerHeight + "px";
    this._els.svg.setAttribute("width", innerWidth);
    this._els.svg.setAttribute("height", innerHeight);
    this._positionBubbles();
  }

  _pressZero() {
    if (!this._hass || !this._config.entity_zero_button) return;
    this._hass.callService("button", "press", {
      entity_id: this._config.entity_zero_button,
    });
  }

  _render() {
    if (!this._hass || !this._els) return;
    this._els.title.textContent = this._config.title;
    this._syncVehicleArt();

    const lrState = this._hass.states[this._config.entity_lr];
    const vhState = this._hass.states[this._config.entity_vh];

    const lr = lrState ? parseFloat(lrState.state) : NaN;
    const vh = vhState ? parseFloat(vhState.state) : NaN;

    this._els.valLr.textContent = Number.isFinite(lr) ? lr.toFixed(1).replace(".", ",") + "°" : "--";
    this._els.valVh.textContent = Number.isFinite(vh) ? vh.toFixed(1).replace(".", ",") + "°" : "--";

    this._angleLr = Number.isFinite(lr) ? lr : 0;
    this._angleVh = Number.isFinite(vh) ? vh : 0;
    this._positionBubbles();
  }

  _positionBubbles() {
    if (!this._els || this._angleLr === undefined) return;
    const art = this._art();
    const vb = art.viewBox;

    const place = (el, center, range, axis, angle) => {
      const clamped = Math.max(-RANGE_DEG, Math.min(RANGE_DEG, angle));
      const frac = (clamped + RANGE_DEG) / (2 * RANGE_DEG);
      const moving = range[0] + frac * (range[1] - range[0]);
      const svgX = axis === "x" ? moving : center.x;
      const svgY = axis === "y" ? moving : center.y;
      // Prozentwerte relativ zum viewBox-Ursprung: bleiben korrekt, egal wie
      // groß .fw-inner gerade skaliert ist (siehe _layout()).
      el.style.left = ((svgX - vb.x) / vb.w * 100) + "%";
      el.style.top = ((svgY - vb.y) / vb.h * 100) + "%";
      el.classList.toggle("level", Math.abs(angle) < 1);
    };

    place(this._els.bubbleVh, art.hCenter, art.hRange, "x", this._angleVh);
    place(this._els.bubbleLr, art.vCenter, art.vRange, "y", this._angleLr);
  }

  disconnectedCallback() {
    if (this._resizeObserver) this._resizeObserver.disconnect();
  }
}

customElements.define("fridolin-nivellierung-card", FridolinNivellierungCard);

// Damit die Karte im UI-Karteneditor unter "Benutzerdefiniert" auftaucht
window.customCards = window.customCards || [];
window.customCards.push({
  type: "fridolin-nivellierung-card",
  name: "Fridolin Nivellierung",
  description: "Kreuzlibelle auf dem Fahrzeug-Grundriss (Wohnwagen oder Wohnmobil, Front oben), wie auf dem Display.",
});
