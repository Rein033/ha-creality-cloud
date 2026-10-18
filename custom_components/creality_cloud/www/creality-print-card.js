/* Creality Print Card: one card per printer of the Creality Cloud integration.
 *
 *   type: custom:creality-print-card
 *   entity: sensor.k1_max_status        # any entity of the printer; the card finds the others through the device
 *   name: K1 Max                        # optional
 *
 * Entities are matched on their translation_key, so renaming them in Home Assistant does not break the card.
 * Served by the integration itself (see __init__.py); no separate install needed. */
const KEYS = ['status', 'progress', 'time_remaining', 'print_end', 'job_name', 'nozzle_temperature', 'nozzle_target',
  'bed_temperature', 'bed_target', 'chamber_temperature', 'online', 'printing', 'pause', 'resume', 'cancel', 'light',
  'thumbnail', 'error_code'];

const STATUS = {
  printing: { color: 'var(--cpc-accent)', icon: 'mdi:printer-3d-nozzle' },
  paused: { color: 'var(--warning-color, #f59e0b)', icon: 'mdi:pause-circle' },
  finished: { color: 'var(--success-color, #22c55e)', icon: 'mdi:check-circle' },
  failed: { color: 'var(--error-color, #ef4444)', icon: 'mdi:alert-circle' },
  stopped: { color: 'var(--error-color, #ef4444)', icon: 'mdi:stop-circle' },
  idle: { color: 'var(--secondary-text-color)', icon: 'mdi:printer-3d' },
  offline: { color: 'var(--disabled-text-color, #888)', icon: 'mdi:cloud-off-outline' },
};

const TEXT = {
  en: { printing: 'Printing', paused: 'Paused', finished: 'Finished', failed: 'Failed', stopped: 'Stopped', idle: 'Idle',
    offline: 'Offline', unknown: 'Unknown', remaining: 'Remaining', ends: 'Ready at', nozzle: 'Nozzle', bed: 'Bed',
    chamber: 'Chamber', pause: 'Pause', resume: 'Resume', cancel: 'Cancel', light: 'Light', noJob: 'No print running',
    confirm: 'Cancel the print on %s? This cannot be undone.', notFound: 'Printer not found. Pick an entity of the Creality Cloud integration.',
    error: 'Error code' },
  nl: { printing: 'Printen', paused: 'Gepauzeerd', finished: 'Klaar', failed: 'Mislukt', stopped: 'Gestopt', idle: 'Vrij',
    offline: 'Offline', unknown: 'Onbekend', remaining: 'Nog', ends: 'Klaar om', nozzle: 'Nozzle', bed: 'Bed',
    chamber: 'Kast', pause: 'Pauzeren', resume: 'Hervatten', cancel: 'Annuleren', light: 'Licht', noJob: 'Er loopt geen print',
    confirm: 'De print op %s echt annuleren? Dit kun je niet terugdraaien.', notFound: 'Printer niet gevonden. Kies een entiteit van de Creality Cloud-integratie.',
    error: 'Foutcode' },
};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

class CrealityPrintCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error('Set "entity" to any entity of a Creality Cloud printer');
    this._config = config;
    this._key = null;
  }

  static getStubConfig(hass) {
    const e = Object.values(hass.entities || {}).find((x) => x.platform === 'creality_cloud' && x.translation_key === 'status');
    return { entity: e ? e.entity_id : 'sensor.k1_max_status' };
  }

  getCardSize() { return 5; }

  getGridOptions() { return { columns: 12, min_columns: 6, rows: 'auto' }; }

  set hass(hass) {
    this._hass = hass;
    const ids = this._entities();
    // only redraw when something the card shows actually changed
    const key = JSON.stringify(Object.values(ids).map((id) => { const s = hass.states[id]; return s && [s.state, s.attributes.entity_picture]; }));
    if (key === this._key) return;
    this._key = key;
    this._render(ids);
  }

  _t(k) {
    const lang = (this._hass && this._hass.locale && this._hass.locale.language || 'en').split('-')[0];
    return (TEXT[lang] || TEXT.en)[k] ?? TEXT.en[k] ?? k;
  }

  _entities() {
    const all = this._hass.entities || {};
    const first = all[this._config.entity];
    if (!first || !first.device_id) return {};
    const ids = {};
    for (const e of Object.values(all)) {
      if (e.device_id === first.device_id && e.platform === 'creality_cloud' && KEYS.includes(e.translation_key)) ids[e.translation_key] = e.entity_id;
    }
    return ids;
  }

  _s(ids, k) { const s = ids[k] && this._hass.states[ids[k]]; return s && !['unavailable', 'unknown'].includes(s.state) ? s : null; }

  _num(ids, k) { const s = this._s(ids, k); const n = s ? parseFloat(s.state) : NaN; return isNaN(n) ? null : n; }

  _render(ids) {
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    const root = this.shadowRoot;
    if (!ids.status) { root.innerHTML = `<ha-card><div class="msg">${esc(this._t('notFound'))}</div></ha-card>${CSS}`; return; }

    const online = !ids.online || (this._hass.states[ids.online] || {}).state === 'on';
    const statusState = this._s(ids, 'status');
    const state = !online ? 'offline' : statusState ? statusState.state : 'unknown';
    const look = STATUS[state] || STATUS.idle;
    const active = state === 'printing' || state === 'paused';
    const progress = active ? Math.max(0, Math.min(100, this._num(ids, 'progress') ?? 0)) : 0;
    const job = active && this._s(ids, 'job_name') ? this._s(ids, 'job_name').state.split('/').pop().replace(/\.gcode$/i, '').replace(/(\.stl)?_[A-Z]+_\d+h\d+m\d+s$/, '') : '';
    const remaining = this._num(ids, 'time_remaining');   // seconds
    const ends = this._s(ids, 'print_end');
    const thumb = active && this._s(ids, 'thumbnail') ? this._hass.states[ids.thumbnail].attributes.entity_picture : null;
    const lightOn = ids.light && (this._hass.states[ids.light] || {}).state === 'on';
    const deviceName = this._config.name || ((this._hass.devices || {})[(this._hass.entities[this._config.entity] || {}).device_id] || {}).name_by_user
      || ((this._hass.devices || {})[(this._hass.entities[this._config.entity] || {}).device_id] || {}).name || 'Creality';
    const err = this._num(ids, 'error_code');

    const dur = (sec) => {
      if (sec == null) return '–';
      const m = Math.round(sec / 60);
      return m >= 60 ? `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m` : `${m}m`;
    };
    const endTime = ends ? new Date(ends.state).toLocaleTimeString(this._hass.locale ? this._hass.locale.language : undefined, { hour: '2-digit', minute: '2-digit' }) : '–';
    const temp = (k, tk, icon, label) => {
      const now = this._num(ids, k), target = tk ? this._num(ids, tk) : null;
      if (now == null && !ids[k]) return '';
      const heating = target != null && target > 0;
      return `<div class="temp ${heating ? 'hot' : ''}" data-more="${esc(ids[k])}">
        <ha-icon icon="${icon}"></ha-icon>
        <div><span class="label">${esc(label)}</span><span class="val">${now == null ? '–' : Math.round(now)}°${heating ? `<small> / ${Math.round(target)}°</small>` : ''}</span></div></div>`;
    };
    const btn = (k, icon, cls = '') => (ids[k] && this._s(ids, k)
      ? `<button class="act ${cls}" data-press="${k}"><ha-icon icon="${icon}"></ha-icon>${esc(this._t(k))}</button>` : '');

    // progress ring: r = 52, circumference ≈ 326.7
    const C = 2 * Math.PI * 52;
    root.innerHTML = `<ha-card style="--cpc-status:${look.color}">
      <div class="head">
        <ha-icon class="logo" icon="${look.icon}"></ha-icon>
        <div class="title"><div class="name">${esc(deviceName)}</div><div class="sub">${esc(job || this._t(active ? state : 'noJob'))}</div></div>
        <span class="chip" data-more="${esc(ids.status)}"><span class="dot"></span>${esc(this._t(state))}</span>
        ${ids.light ? `<button class="icon ${lightOn ? 'on' : ''}" data-light title="${esc(this._t('light'))}" ${online ? '' : 'disabled'}><ha-icon icon="${lightOn ? 'mdi:lightbulb-on' : 'mdi:lightbulb-outline'}"></ha-icon></button>` : ''}
      </div>
      <div class="body ${active ? '' : 'idle'}">
        <div class="ring" data-more="${esc(ids.progress || ids.status)}">
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <circle class="track" cx="60" cy="60" r="52"></circle>
            <circle class="bar" cx="60" cy="60" r="52" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - progress / 100)}"></circle>
          </svg>
          ${thumb ? `<img src="${esc(thumb)}" alt="">` : `<ha-icon class="ph" icon="mdi:printer-3d"></ha-icon>`}
          ${active ? `<div class="pct">${Math.round(progress)}<small>%</small></div>` : ''}
        </div>
        ${active ? `<div class="stats">
          <div class="stat"><span class="label">${esc(this._t('remaining'))}</span><span class="big">${dur(remaining)}</span></div>
          <div class="stat"><span class="label">${esc(this._t('ends'))}</span><span class="big">${esc(endTime)}</span></div>
        </div>` : ''}
      </div>
      <div class="temps">
        ${temp('nozzle_temperature', 'nozzle_target', 'mdi:printer-3d-nozzle-heat', this._t('nozzle'))}
        ${temp('bed_temperature', 'bed_target', 'mdi:radiator', this._t('bed'))}
        ${temp('chamber_temperature', null, 'mdi:thermometer', this._t('chamber'))}
      </div>
      ${err ? `<div class="err"><ha-icon icon="mdi:alert"></ha-icon>${esc(this._t('error'))} ${err}</div>` : ''}
      ${active && online ? `<div class="actions">
        ${state === 'printing' ? btn('pause', 'mdi:pause') : btn('resume', 'mdi:play')}
        ${btn('cancel', 'mdi:stop', 'danger')}
      </div>` : ''}
    </ha-card>${CSS}`;

    root.querySelectorAll('[data-more]').forEach((el) => el.addEventListener('click', () => this._more(el.dataset.more)));
    root.querySelectorAll('[data-press]').forEach((el) => el.addEventListener('click', () => {
      const k = el.dataset.press;
      if (k === 'cancel' && !confirm(this._t('confirm').replace('%s', deviceName))) return;
      el.disabled = true;
      this._hass.callService('button', 'press', { entity_id: ids[k] }).catch(() => { el.disabled = false; });
    }));
    const l = root.querySelector('[data-light]');
    if (l) l.addEventListener('click', () => this._hass.callService('light', 'toggle', { entity_id: ids.light }));
  }

  _more(entityId) {
    if (!entityId) return;
    this.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId }, bubbles: true, composed: true }));
  }
}

const CSS = `<style>
  ha-card { --cpc-accent: var(--primary-color); padding: 16px; overflow: hidden; position: relative; container-type: inline-size; }
  ha-card::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--cpc-status); opacity: .85; }
  .msg { padding: 8px 0; color: var(--secondary-text-color); }
  .head { display: flex; align-items: center; gap: 12px; }
  .logo { --mdc-icon-size: 28px; color: var(--cpc-status); background: color-mix(in srgb, var(--cpc-status) 14%, transparent);
    border-radius: 12px; padding: 8px; flex: none; }
  .title { flex: 1; min-width: 0; }
  .name { font-size: 1.1rem; font-weight: 600; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sub { color: var(--secondary-text-color); font-size: .85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: .8rem; font-weight: 500;
    background: color-mix(in srgb, var(--cpc-status) 16%, transparent); color: var(--primary-text-color); cursor: pointer; white-space: nowrap; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--cpc-status); }
  button { font: inherit; cursor: pointer; }
  .icon { border: none; background: none; color: var(--secondary-text-color); border-radius: 50%; padding: 6px; display: flex; }
  .icon.on { color: var(--state-light-on-color, #f5b301); }
  .icon:disabled { opacity: .4; cursor: default; }
  .body { display: flex; align-items: center; gap: 20px; margin: 16px 0 8px; }
  .body.idle { justify-content: center; }
  .ring { position: relative; width: 132px; height: 132px; flex: none; cursor: pointer; }
  .ring svg { position: absolute; inset: 0; transform: rotate(-90deg); }
  .ring circle { fill: none; stroke-width: 8; }
  .track { stroke: var(--divider-color, rgba(127,127,127,.25)); }
  .bar { stroke: var(--cpc-status); stroke-linecap: round; transition: stroke-dashoffset .8s ease; }
  .ring img { position: absolute; inset: 18px; width: 96px; height: 96px; object-fit: contain; border-radius: 50%;
    background: color-mix(in srgb, var(--cpc-status) 8%, transparent); }
  .ring .ph { position: absolute; inset: 0; margin: auto; width: 48px; height: 48px; --mdc-icon-size: 48px; color: var(--secondary-text-color); opacity: .5; }
  .pct { position: absolute; right: -6px; bottom: -2px; background: var(--card-background-color, #fff); border: 2px solid var(--cpc-status);
    border-radius: 999px; padding: 1px 8px; font-weight: 700; font-size: .95rem; }
  .pct small { font-size: .7rem; font-weight: 500; }
  .stats { display: grid; gap: 12px; flex: 1; }
  .stat { display: flex; flex-direction: column; }
  .label { color: var(--secondary-text-color); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; }
  .big { font-size: 1.5rem; font-weight: 600; line-height: 1.2; }
  .temps { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px; margin-top: 8px; }
  .temp { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 12px; cursor: pointer;
    background: var(--secondary-background-color, rgba(127,127,127,.08)); }
  .temp ha-icon { color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  .temp.hot ha-icon { color: var(--state-climate-heat-color, #ff8100); }
  .temp div { display: flex; flex-direction: column; }
  .temp .val { font-weight: 600; white-space: nowrap; }
  .temp .val small { font-weight: 400; color: var(--secondary-text-color); }
  .err { display: flex; align-items: center; gap: 6px; margin-top: 10px; color: var(--error-color, #ef4444); font-size: .85rem; }
  .actions { display: flex; gap: 8px; margin-top: 12px; }
  .act { flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 8px 12px; border-radius: 12px;
    border: 1px solid var(--divider-color, rgba(127,127,127,.3)); background: none; color: var(--primary-text-color); }
  .act ha-icon { --mdc-icon-size: 18px; }
  .act.danger { color: var(--error-color, #ef4444); border-color: color-mix(in srgb, var(--error-color, #ef4444) 40%, transparent); }
  .act:disabled { opacity: .5; cursor: default; }
  @container (max-width: 400px) { .temp { padding: 8px; gap: 6px; } .temp ha-icon { display: none !important; } .temp .val small { font-size: .75rem; } }
  @media (max-width: 420px) { .body { gap: 14px; } .ring { width: 112px; height: 112px; } .ring img { inset: 14px; width: 84px; height: 84px; } .big { font-size: 1.25rem; } }
</style>`;

if (!customElements.get('creality-print-card')) {
  customElements.define('creality-print-card', CrealityPrintCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'creality-print-card',
    name: 'Creality Print Card',
    description: 'Progress, preview, temperatures and controls for a Creality Cloud printer.',
    preview: true,
    documentationURL: 'https://github.com/Rein033/ha-creality-cloud',
  });
}
