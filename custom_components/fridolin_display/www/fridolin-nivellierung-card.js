/**
 * Fridolin Nivellierung - Lovelace-Karte
 *
 * Zeigt dieselbe Kreuzlibelle wie die Nivellierungs-Seite auf dem
 * Wohnwagen-Display, aber auf einem Wohnwagen-Grundriss mit der Deichsel
 * NACH OBEN (statt nach rechts wie im Display) - passend zur klassischen
 * "Draufsicht von vorne" auf einem Dashboard.
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
 *        # Optional, falls deine Entity-IDs abweichen:
 *        entity_lr: sensor.fridolin_display_neigung_links_rechts
 *        entity_vh: sensor.fridolin_display_neigung_vorne_hinten
 *        entity_zero_button: button.fridolin_display_neigung_nullen
 */

const WASSERWAAGE_SVG_BODY = `
  <defs>
    <linearGradient id="fwGradV" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#D7EA82"/>
      <stop offset="1" stop-color="#7FA119"/>
    </linearGradient>
    <linearGradient id="fwGradH" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#D7EA82"/>
      <stop offset="1" stop-color="#7FA119"/>
    </linearGradient>
  </defs>
  <rect x="30" y="55" width="350" height="170" rx="45" fill="#17212C" stroke="#3A4250" stroke-width="4"/>
  <path d="M380,120 L432,140 L380,160 Z" fill="#55606F"/>
  <path d="M100,225 q20,16 40,0" fill="none" stroke="#0D141C" stroke-width="3"/>
  <path d="M300,225 q20,16 40,0" fill="none" stroke="#0D141C" stroke-width="3"/>
  <line x1="150" y1="65" x2="150" y2="215" stroke="#202836" stroke-width="2" opacity="0.6"/>
  <line x1="260" y1="65" x2="260" y2="215" stroke="#202836" stroke-width="2" opacity="0.6"/>
  <rect x="80" y="113" width="150" height="54" rx="27" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <rect x="86" y="119" width="138" height="42" rx="21" fill="url(#fwGradV)"/>
  <line x1="134" y1="129" x2="134" y2="151" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <line x1="176" y1="129" x2="176" y2="151" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <rect x="270" y="65" width="54" height="150" rx="27" fill="#3A4250" stroke="#55606F" stroke-width="2"/>
  <rect x="276" y="71" width="42" height="138" rx="21" fill="url(#fwGradH)"/>
  <line x1="286" y1="119" x2="308" y2="119" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
  <line x1="286" y1="161" x2="308" y2="161" stroke="#101a05" stroke-width="3" stroke-linecap="round"/>
`;

// Bewegungsbereich in SVG-Einheiten (0..460 x 0..300), identisch zum Display
// und zur Vorschau (esphome/wohnwagen-display.yaml bzw. fridolin-vorschau.html).
const RANGE_DEG = 8;
const H_CENTER = { x: 155, y: 140 };
const H_RANGE = [118, 192]; // Vorne/Hinten-Röhre, Blase bewegt sich in X
const V_CENTER = { x: 297, y: 140 };
const V_RANGE = [103, 177]; // Links/Rechts-Röhre, Blase bewegt sich in Y

const CARD_STYLE = `
  :host { display: block; }
  ha-card { padding: 16px 16px 20px; }
  .fw-title { font-size: 1.1em; font-weight: 500; margin: 0 0 10px; }
  .fw-outer {
    position: relative;
    width: 100%;
    /* Grundriss ist 460x300 (Querformat); um 90° gedreht wird daraus 300x460
       (Hochformat) - das Padding hält genau dieses Seitenverhältnis frei. */
    padding-top: 153.33%;
    max-width: 340px;
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
    margin-top: 14px;
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
    margin-top: 14px;
  }
  .fw-unavailable {
    text-align: center;
    color: var(--secondary-text-color);
    padding: 24px 0;
  }
`;

class FridolinNivellierungCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      entity_lr: "sensor.fridolin_display_neigung_links_rechts",
      entity_vh: "sensor.fridolin_display_neigung_vorne_hinten",
      entity_zero_button: "button.fridolin_display_neigung_nullen",
      title: "Nivellierung",
      ...config,
    };
    this._build();
  }

  getCardSize() {
    return 4;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._render();
  }

  _build() {
    if (this._built || !this._config) return;
    this._built = true;

    const style = document.createElement("style");
    style.textContent = CARD_STYLE;

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <div class="fw-title">${this._config.title}</div>
      <div class="fw-outer">
        <div class="fw-inner">
          <svg id="fwSvg" viewBox="0 0 460 300" width="300" height="196" xmlns="http://www.w3.org/2000/svg">
            ${WASSERWAAGE_SVG_BODY}
          </svg>
          <div class="fw-bubble" id="fwBubbleVh" style="width:30px;height:22px;"></div>
          <div class="fw-bubble" id="fwBubbleLr" style="width:22px;height:30px;"></div>
        </div>
      </div>
      <div class="fw-values">
        <span>Links/Rechts:<b id="fwValLr">--</b></span>
        <span>Vorne/Hinten:<b id="fwValVh">--</b></span>
      </div>
      <div class="fw-footer">
        <mwc-button id="fwZeroBtn" raised>Nullen</mwc-button>
      </div>
    `;

    this.innerHTML = "";
    this.appendChild(style);
    this.appendChild(card);

    this._els = {
      svg: card.querySelector("#fwSvg"),
      inner: card.querySelector(".fw-inner"),
      outer: card.querySelector(".fw-outer"),
      bubbleVh: card.querySelector("#fwBubbleVh"),
      bubbleLr: card.querySelector("#fwBubbleLr"),
      valLr: card.querySelector("#fwValLr"),
      valVh: card.querySelector("#fwValVh"),
      zeroBtn: card.querySelector("#fwZeroBtn"),
    };

    this._els.zeroBtn.addEventListener("click", () => this._pressZero());

    // Größe des gedrehten Grundrisses an die tatsächliche Kartenbreite anpassen
    this._resizeObserver = new ResizeObserver(() => this._layout());
    this._resizeObserver.observe(this._els.outer);
    this._layout();
  }

  _layout() {
    if (!this._els) return;
    const outerWidth = this._els.outer.clientWidth;
    if (!outerWidth) return;
    // Nach der Drehung um 90° wird aus der Breite des Grundrisses (460 SVG-
    // Einheiten) die Höhe im Kartenlayout, und umgekehrt - daher hier
    // getauscht: die "unrotierte" Breite richtet sich nach der Kartenhöhe.
    const outerHeight = outerWidth * (460 / 300);
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

    const place = (el, center, range, axis, angle) => {
      const clamped = Math.max(-RANGE_DEG, Math.min(RANGE_DEG, angle));
      const frac = (clamped + RANGE_DEG) / (2 * RANGE_DEG);
      const moving = range[0] + frac * (range[1] - range[0]);
      const svgX = axis === "x" ? moving : center.x;
      const svgY = axis === "y" ? moving : center.y;
      // Prozentwerte statt Pixel: bleiben korrekt, egal wie groß .fw-inner
      // gerade skaliert ist (siehe _layout()).
      el.style.left = (svgX / 460 * 100) + "%";
      el.style.top = (svgY / 300 * 100) + "%";
      el.classList.toggle("level", Math.abs(angle) < 1);
    };

    place(this._els.bubbleVh, H_CENTER, H_RANGE, "x", this._angleVh);
    place(this._els.bubbleLr, V_CENTER, V_RANGE, "y", this._angleLr);
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
  description: "Kreuzlibelle auf dem Wohnwagen-Grundriss (Deichsel oben), wie auf dem Display.",
});
