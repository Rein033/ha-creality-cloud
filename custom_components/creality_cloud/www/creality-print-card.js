/* Creality Print Card and Creality Print Group Card, for the Creality Cloud integration. They also understand the
 * Anycubic Cloud integration (anycubic_cloud).
 *
 *   type: custom:creality-print-card
 *   entity: sensor.k1_max_status        # any entity of the printer; the card finds the others through the device
 *   name: K1 Max                        # optional
 *   view: printer                       # printer (drawing, default) or preview (progress ring); can be switched on the card
 *   show_slicer: true                   # slicer info chips (material, layers, filament, ...)
 *   show_temperatures: true
 *   show_controls: true                 # pause / resume / cancel and the light button
 *   show_view_switch: true              # the printer / preview switch on the card
 *   show_history: true                  # history button: recent prints, timelapse and print again (Creality Cloud)
 *
 *   type: custom:creality-print-group-card
 *   title: Printers                     # optional
 *   entities: [sensor.k1_max_status, sensor.kobra_s1_job_progress]   # optional, default: every printer
 *
 * Both cards have a visual editor. Entities are matched on their translation_key, so renaming them does not break
 * anything. The printer drawings are original artwork. Served by the integration itself (see __init__.py). */

/* role -> translation_key per integration */
const ADAPTERS = {
  creality_cloud: {
    drawing: 'k1',
    roles: {
      status: 'status', progress: 'progress', remaining: 'time_remaining', ends: 'print_end', job: 'job_name',
      nozzle: 'nozzle_temperature', nozzle_target: 'nozzle_target', bed: 'bed_temperature', bed_target: 'bed_target',
      extra: 'chamber_temperature', online: 'online', pause: 'pause', resume: 'resume', cancel: 'cancel', light: 'light',
      thumbnail: 'thumbnail', error: 'error_code', history: 'last_print', reprint: 'reprint_last', firmware: 'firmware',
    },
    extraLabel: 'chamber',
    anchor: 'status',
    state(c) { return c.str('status'); },
  },
  anycubic_cloud: {
    drawing: 'kobra',
    roles: {
      progress: 'job_progress', remaining: 'job_time_remaining', ends: 'job_eta', job: 'job_name',
      nozzle: 'curr_nozzle_temp', nozzle_target: 'target_nozzle_temp', bed: 'curr_hotbed_temp', bed_target: 'target_hotbed_temp',
      extra: 'ace_current_temperature', online: 'printer_online', busy: 'job_in_progress', paused: 'job_is_paused',
      complete: 'job_complete', failed: 'job_failed', pause: 'pause_print', resume: 'resume_print', cancel: 'cancel_print',
      light: 'printer_light', thumbnail: 'job_image_url', layer: 'job_current_layer', layers: 'job_total_layers',
      filament: 'job_filament_used', loaded_slot: 'ace_loaded_slot', slot1: 'ace_slot_1', slot2: 'ace_slot_2',
      slot3: 'ace_slot_3', slot4: 'ace_slot_4', error: 'last_error',
    },
    extraLabel: 'ace',
    anchor: 'job_progress',
    state(c) {
      if (c.on('paused')) return 'paused';
      if (c.on('busy')) return 'printing';
      if (c.on('failed')) return 'failed';
      if (c.on('complete')) return 'finished';
      return 'idle';
    },
  },
};

const STATUS = {
  printing: { color: 'var(--cpc-accent, var(--primary-color))', icon: 'mdi:printer-3d-nozzle' },
  paused: { color: 'var(--warning-color, #f59e0b)', icon: 'mdi:pause-circle' },
  finished: { color: 'var(--success-color, #22c55e)', icon: 'mdi:check-circle' },
  failed: { color: 'var(--error-color, #ef4444)', icon: 'mdi:alert-circle' },
  stopped: { color: 'var(--error-color, #ef4444)', icon: 'mdi:stop-circle' },
  waiting: { color: 'var(--secondary-text-color)', icon: 'mdi:timer-sand' },
  idle: { color: 'var(--secondary-text-color)', icon: 'mdi:printer-3d' },
  offline: { color: 'var(--disabled-text-color, #888)', icon: 'mdi:cloud-off-outline' },
};

const TEXT = {
  en: { printing: 'Printing', paused: 'Paused', finished: 'Finished', failed: 'Failed', stopped: 'Cancelled', idle: 'Idle',
    waiting: 'Waiting', offline: 'Offline', unknown: 'Unknown', remaining: 'Remaining', ends: 'Ready at', nozzle: 'Nozzle', bed: 'Bed',
    chamber: 'Chamber', ace: 'ACE', pause: 'Pause', resume: 'Resume', cancel: 'Cancel', light: 'Light', noJob: 'No print running',
    confirm: 'Cancel the print on %s? This cannot be undone.', notFound: 'Printer not found. Pick an entity of the Creality Cloud or Anycubic Cloud integration.',
    error: 'Error', material: 'Material', layerHeight: 'Layer', layers: 'Layers', filament: 'Filament', slicer: 'Slicer',
    estimate: 'Estimate', viewPrinter: 'Printer', viewPreview: 'Preview', history: 'Print history', noHistory: 'No prints yet.',
    timelapse: 'Timelapse', reprint: 'Print again', reprintConfirm: 'Print "%s" again on %s?', reprintBusy: 'Possible when the printer is online and idle',
    reprintNotOnPrinter: 'This file is not on the printer', close: 'Close', update: 'Update', updateTitle: 'Firmware %s is available',
    groupTitle: 'Printers', noPrinters: 'No printers found.', sent: 'Sent to the printer',
    e_entity: 'Printer (any entity of it)', e_name: 'Name (optional)', e_view: 'Start view', e_show_slicer: 'Show slicer info',
    e_show_temperatures: 'Show temperatures', e_show_controls: 'Show buttons (pause, cancel, light)', e_show_view_switch: 'Show printer / preview switch',
    e_show_history: 'Show history button (timelapse, print again)', e_title: 'Title', e_entities: 'Printers (empty = all printers)',
    e_show_idle: 'Also show idle and offline printers' },
  nl: { printing: 'Printen', paused: 'Gepauzeerd', finished: 'Klaar', failed: 'Mislukt', stopped: 'Geannuleerd', idle: 'Vrij',
    waiting: 'Wachten', offline: 'Offline', unknown: 'Onbekend', remaining: 'Nog', ends: 'Klaar om', nozzle: 'Nozzle', bed: 'Bed',
    chamber: 'Kast', ace: 'ACE', pause: 'Pauzeren', resume: 'Hervatten', cancel: 'Annuleren', light: 'Licht', noJob: 'Er loopt geen print',
    confirm: 'De print op %s echt annuleren? Dit kun je niet terugdraaien.', notFound: 'Printer niet gevonden. Kies een entiteit van de Creality Cloud- of Anycubic Cloud-integratie.',
    error: 'Fout', material: 'Materiaal', layerHeight: 'Laag', layers: 'Lagen', filament: 'Filament', slicer: 'Slicer',
    estimate: 'Schatting', viewPrinter: 'Printer', viewPreview: 'Voorbeeld', history: 'Printgeschiedenis', noHistory: 'Nog geen prints.',
    timelapse: 'Timelapse', reprint: 'Opnieuw printen', reprintConfirm: '"%s" opnieuw printen op %s?', reprintBusy: 'Kan als de printer online en vrij is',
    reprintNotOnPrinter: 'Dit bestand staat niet op de printer', close: 'Sluiten', update: 'Update', updateTitle: 'Firmware %s is beschikbaar',
    groupTitle: 'Printers', noPrinters: 'Geen printers gevonden.', sent: 'Verstuurd naar de printer',
    e_entity: 'Printer (een willekeurige entiteit ervan)', e_name: 'Naam (optioneel)', e_view: 'Startweergave', e_show_slicer: 'Slicer-info tonen',
    e_show_temperatures: 'Temperaturen tonen', e_show_controls: 'Knoppen tonen (pauzeren, annuleren, licht)', e_show_view_switch: 'Wisselknop printer / voorbeeld tonen',
    e_show_history: 'Geschiedenisknop tonen (timelapse, opnieuw printen)', e_title: 'Titel', e_entities: 'Printers (leeg = alle printers)',
    e_show_idle: 'Ook vrije en offline printers tonen' },
};

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SECONDS = { s: 1, min: 60, h: 3600, d: 86400 };
const isHex = (c) => /^#[0-9a-f]{6}$/i.test(c || '');
let uid = 0;

function tr(hass, k) {
  const lang = (hass && hass.locale && hass.locale.language || 'en').split('-')[0];
  return (TEXT[lang] || TEXT.en)[k] ?? TEXT.en[k] ?? k;
}

function cleanJob(name) {
  return String(name || '').split('/').pop().replace(/\.gcode$/i, '')
    .replace(/(\.stl)?_[A-Z][A-Z0-9+-]*(_0\.\d+)?_(\d+d)?(\d+h)?(\d+m)?(\d+s)?$/, '').replace(/^\d{4}-\d{4}-/, '');
}

function dur(sec) {
  if (sec == null) return '–';
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m` : `${m}m`;
}

function fmtLength(v, unit) {
  if (isNaN(v)) return null;
  if (unit === 'g') return `${Math.round(v)} g`;
  const mm = unit === 'm' ? v * 1000 : unit === 'cm' ? v * 10 : v;
  return mm >= 1000 ? `${(mm / 1000).toFixed(1)} m` : `${Math.round(mm)} mm`;
}

/* All printers of both integrations: [{entity, platform, device_id}] (one anchor entity per device). */
function allPrinters(hass) {
  const out = [];
  for (const e of Object.values(hass.entities || {})) {
    const A = ADAPTERS[e.platform];
    if (A && e.translation_key === A.anchor && e.device_id) out.push({ entity: e.entity_id, platform: e.platform, device_id: e.device_id });
  }
  return out;
}

/* Everything the cards show about one printer, in one shape for both integrations. */
function snapshot(hass, entityId, name) {
  const first = (hass.entities || {})[entityId];
  const A = first && ADAPTERS[first.platform];
  if (!first || !first.device_id || !A) return null;
  const wanted = Object.fromEntries(Object.entries(A.roles).map(([role, tk]) => [tk, role]));
  const ids = {};
  for (const e of Object.values(hass.entities)) {
    if (e.device_id === first.device_id && e.platform === first.platform && wanted[e.translation_key]) ids[wanted[e.translation_key]] = e.entity_id;
  }
  if (!Object.keys(ids).length) return null;

  const st = (r) => { const s = ids[r] && hass.states[ids[r]]; return s && !['unavailable', 'unknown'].includes(s.state) ? s : null; };
  const c = {
    str: (r) => (st(r) ? st(r).state : null),
    num: (r) => { const s = st(r); const n = s ? parseFloat(s.state) : NaN; return isNaN(n) ? null : n; },
    on: (r) => (ids[r] && hass.states[ids[r]] || {}).state === 'on',
    secs: (r) => { const s = st(r); const n = s ? parseFloat(s.state) : NaN; return isNaN(n) ? null : n * (SECONDS[s.attributes.unit_of_measurement] || 1); },
  };
  const online = !ids.online || c.on('online');
  const state = !online ? 'offline' : (A.state(c) || 'unknown');
  const active = state === 'printing' || state === 'paused';
  const done = state === 'finished';
  const jobState = st('job');
  const jobAttr = jobState ? jobState.attributes : {};
  const remaining = active ? c.secs('remaining') : null;
  const endsState = st('ends');
  const thumbState = ids.thumbnail && hass.states[ids.thumbnail];
  const dev = (hass.devices || {})[first.device_id] || {};
  const errS = st('error');
  const loaded = c.str('loaded_slot');
  const spools = [1, 2, 3, 4].map((n) => {
    const s = st('slot' + n);
    return s ? { n, mat: s.state, color: s.attributes.color_hex, loaded: s.attributes.spool_loaded !== false, active: String(n) === String(loaded) } : null;
  }).filter(Boolean);
  const activeSpool = spools.find((s) => s.active);
  const fw = ids.firmware && hass.states[ids.firmware];
  const hist = ids.history && hass.states[ids.history];
  const filament = st('filament');
  return {
    A, ids, c, online, state, active, done, look: STATUS[state] || STATUS.idle, device_id: first.device_id, platform: first.platform,
    name: name || dev.name_by_user || dev.name || 'Printer',
    progress: active ? Math.max(0, Math.min(100, c.num('progress') ?? 0)) : done ? 100 : 0,
    job: jobState ? cleanJob(jobAttr.file_name || jobState.state) : '',
    jobAttr, remaining,
    ends: active ? (endsState && !isNaN(Date.parse(endsState.state)) ? new Date(endsState.state)
      : remaining != null ? new Date(Date.now() + remaining * 1000) : null) : null,
    // the image entity's state is a timestamp; Anycubic keeps it "unknown" but still serves the picture
    thumb: (active || done) && thumbState && thumbState.state !== 'unavailable' && thumbState.attributes.entity_picture ? thumbState.attributes.entity_picture : null,
    lightOn: ids.light && (hass.states[ids.light] || {}).state === 'on',
    err: errS && !['0', 'none', ''].includes(String(errS.state).toLowerCase()) ? errS.state : null,
    spools, tint: (active || done) && activeSpool && isHex(activeSpool.color) ? activeSpool.color : null,
    layer: c.num('layer'), layers: c.num('layers'),
    filamentTxt: filament ? fmtLength(parseFloat(filament.state), filament.attributes.unit_of_measurement) : null,
    update: fw && fw.state === 'on' ? fw.attributes.latest_version : null,
    history: hist && Array.isArray(hist.attributes.history) ? hist.attributes.history : null,
  };
}

/* One key per printer that changes when anything the cards show changes. */
function snapKey(hass, ids) {
  return JSON.stringify(Object.values(ids || {}).map((id) => { const s = hass.states[id]; return s && [s.state, s.last_updated]; }));
}

function moreInfo(el, entityId) {
  if (entityId) el.dispatchEvent(new CustomEvent('hass-more-info', { detail: { entityId }, bubbles: true, composed: true }));
}

class CrealityPrintCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error('Set "entity" to any entity of a Creality Cloud or Anycubic Cloud printer');
    this._config = config;
    this._view = config.view === 'preview' ? 'preview' : 'printer';
    this._key = null;
    this._uid = 'cpc' + (++uid);
  }

  static getConfigElement() { return document.createElement('creality-print-card-editor'); }

  static getStubConfig(hass) {
    // prefer a printer that is online, and Creality Cloud before other integrations
    const rank = (p) => { const s = snapshot(hass, p.entity); return (s && s.online ? 0 : 2) + (p.platform === 'creality_cloud' ? 0 : 1); };
    const p = allPrinters(hass).sort((a, b) => rank(a) - rank(b))[0];
    return { entity: p ? p.entity : 'sensor.k1_max_status' };
  }

  getCardSize() { return 7; }

  getGridOptions() { return { columns: 12, min_columns: 6, rows: 'auto' }; }

  set hass(hass) {
    this._hass = hass;
    const s = snapshot(hass, this._config.entity, this._config.name);
    const key = this._view + (s ? snapKey(hass, s.ids) : 'none');
    if (key === this._key) return;
    this._key = key;
    this._snap = s;
    this._render(s);
    if (this._dialog) this._dialog.update(hass, s);
  }

  _t(k) { return tr(this._hass, k); }

  _render(s) {
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    const root = this.shadowRoot;
    if (!s) { root.innerHTML = `<ha-card><div class="msg">${esc(this._t('notFound'))}</div></ha-card>${CSS}`; return; }
    const hass = this._hass, cfg = this._config, show = (k) => cfg[k] !== false;
    const { A, ids, c, active, done, state, online } = s;

    const types = [...new Set(Array.isArray(s.jobAttr.filament_types) ? s.jobAttr.filament_types : [])];
    const slicer = [
      types.length ? [this._t('material'), types.join(' + ')] : null,
      s.jobAttr.layer_height ? [this._t('layerHeight'), `${s.jobAttr.layer_height} mm`] : null,
      s.layers ? [this._t('layers'), `${s.layer != null ? Math.round(s.layer) : '–'} / ${Math.round(s.layers)}`] : null,
      s.filamentTxt ? [this._t('filament'), s.filamentTxt] : null,
      s.jobAttr.slicer_estimate ? [this._t('estimate'), dur(s.jobAttr.slicer_estimate)] : null,
      s.jobAttr.slicer ? [this._t('slicer'), String(s.jobAttr.slicer)] : null,
    ].filter(Boolean);

    const lang = hass.locale ? hass.locale.language : undefined;
    const endTime = s.ends ? s.ends.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' }) : '–';
    const temp = (k, tk, icon, label) => {
      const now = c.num(k), target = tk ? c.num(tk) : null;
      if (now == null && !ids[k]) return '';
      const heating = target != null && target > 0;
      return `<div class="temp ${heating ? 'hot' : ''}" data-more="${esc(ids[k])}">
        <ha-icon icon="${icon}"></ha-icon>
        <div><span class="label">${esc(label)}</span><span class="val">${now == null ? '–' : Math.round(now)}°${heating ? `<small> / ${Math.round(target)}°</small>` : ''}</span></div></div>`;
    };
    const btn = (k, icon, cls = '') => (ids[k] && (hass.states[ids[k]] || {}).state !== 'unavailable'
      ? `<button class="act ${cls}" data-press="${k}"><ha-icon icon="${icon}"></ha-icon>${esc(this._t(k))}</button>` : '');

    const C = 2 * Math.PI * 52;
    const ring = `<div class="ring" data-more="${esc(ids.progress || ids.status)}">
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle class="track" cx="60" cy="60" r="52"></circle>
          <circle class="bar" cx="60" cy="60" r="52" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - s.progress / 100)}"></circle>
        </svg>
        ${s.thumb ? `<img src="${esc(s.thumb)}" alt="">` : `<ha-icon class="ph" icon="mdi:printer-3d"></ha-icon>`}
        ${active ? `<div class="pct">${Math.round(s.progress)}<small>%</small></div>` : ''}
      </div>`;
    const o = { progress: s.progress, thumb: s.thumb, tint: s.tint, active, printing: state === 'printing', lightOn: s.lightOn, spools: s.spools };
    const drawing = `<div class="draw" data-more="${esc(ids.progress || ids.status)}">
        ${A.drawing === 'kobra' ? kobraSvg(this._uid, o) : k1Svg(this._uid, o)}
        ${active ? `<div class="pct float">${Math.round(s.progress)}<small>%</small></div>` : ''}
      </div>`;
    const times = active ? `<div class="stats">
        <div class="stat"><span class="label">${esc(this._t('remaining'))}</span><span class="big">${dur(s.remaining)}</span></div>
        <div class="stat"><span class="label">${esc(this._t('ends'))}</span><span class="big">${esc(endTime)}</span></div>
      </div>` : '';
    const viewBtns = !show('show_view_switch') ? '' : `<div class="views" role="group">
        <button class="${this._view === 'printer' ? 'sel' : ''}" data-view="printer" title="${esc(this._t('viewPrinter'))}"><ha-icon icon="mdi:printer-3d"></ha-icon></button>
        <button class="${this._view === 'preview' ? 'sel' : ''}" data-view="preview" title="${esc(this._t('viewPreview'))}"><ha-icon icon="mdi:image-outline"></ha-icon></button>
      </div>`;
    const historyBtn = show('show_history') && ids.history
      ? `<button class="icon" data-history title="${esc(this._t('history'))}"><ha-icon icon="mdi:history"></ha-icon></button>` : '';
    const updateChip = s.update ? `<button class="icon upd" data-more="${esc(ids.firmware)}" title="${esc(this._t('updateTitle').replace('%s', s.update))}"><ha-icon icon="mdi:package-up"></ha-icon></button>` : '';

    root.innerHTML = `<ha-card style="--cpc-status:${s.look.color}">
      <div class="head">
        <ha-icon class="logo" icon="${s.look.icon}"></ha-icon>
        <div class="title"><div class="name">${esc(s.name)}</div><div class="sub">${esc(s.job && (active || done) ? s.job : this._t('noJob'))}</div></div>
        <div class="tools">
          ${updateChip}
          <span class="chip" data-more="${esc(ids.status || ids.busy || ids.online)}"><span class="dot"></span>${esc(this._t(state))}</span>
          ${historyBtn}
          ${ids.light && show('show_controls') ? `<button class="icon ${s.lightOn ? 'on' : ''}" data-light title="${esc(this._t('light'))}" ${online ? '' : 'disabled'}><ha-icon icon="${s.lightOn ? 'mdi:lightbulb-on' : 'mdi:lightbulb-outline'}"></ha-icon></button>` : ''}
        </div>
      </div>
      ${this._view === 'printer'
        ? `<div class="stage">${drawing}${viewBtns}</div>${times ? `<div class="under">${times}</div>` : ''}`
        : `<div class="body ${active ? '' : 'idle'}">${ring}${times}</div>${viewBtns ? `<div class="viewrow">${viewBtns}</div>` : ''}`}
      ${(active || done) && slicer.length && show('show_slicer') ? `<div class="slicer">${slicer.map(([l, v]) => `<span><b>${esc(v)}</b>${esc(l)}</span>`).join('')}</div>` : ''}
      ${!show('show_temperatures') ? '' : `<div class="temps">
        ${temp('nozzle', 'nozzle_target', 'mdi:printer-3d-nozzle-heat', this._t('nozzle'))}
        ${temp('bed', 'bed_target', 'mdi:radiator', this._t('bed'))}
        ${temp('extra', null, A.extraLabel === 'ace' ? 'mdi:printer-3d-nozzle-outline' : 'mdi:thermometer', this._t(A.extraLabel))}
      </div>`}
      ${s.err ? `<div class="err"><ha-icon icon="mdi:alert"></ha-icon>${esc(this._t('error'))}: ${esc(s.err)}</div>` : ''}
      ${active && online && show('show_controls') ? `<div class="actions">
        ${state === 'printing' ? btn('pause', 'mdi:pause') : btn('resume', 'mdi:play')}
        ${btn('cancel', 'mdi:stop', 'danger')}
      </div>` : ''}
    </ha-card>${CSS}`;

    root.querySelectorAll('[data-more]').forEach((el) => el.addEventListener('click', () => moreInfo(this, el.dataset.more)));
    root.querySelectorAll('[data-view]').forEach((el) => el.addEventListener('click', (ev) => {
      ev.stopPropagation();
      this._view = el.dataset.view;
      this._key = null;
      this.hass = this._hass;
    }));
    root.querySelectorAll('[data-press]').forEach((el) => el.addEventListener('click', () => {
      const k = el.dataset.press;
      if (k === 'cancel' && !confirm(this._t('confirm').replace('%s', s.name))) return;
      el.disabled = true;
      hass.callService('button', 'press', { entity_id: ids[k] }).catch(() => { el.disabled = false; });
    }));
    const l = root.querySelector('[data-light]');
    if (l) l.addEventListener('click', () => hass.callService('light', 'toggle', { entity_id: ids.light }));
    const h = root.querySelector('[data-history]');
    if (h) h.addEventListener('click', () => this._openHistory());
  }

  _openHistory() {
    if (!this._dialog) {
      this._dialog = document.createElement('creality-print-dialog');
      this._dialog.addEventListener('closed', () => { this._dialog.remove(); this._dialog = null; });
    }
    document.body.append(this._dialog);
    this._dialog.update(this._hass, this._snap);
  }

  disconnectedCallback() { if (this._dialog) { this._dialog.remove(); this._dialog = null; } }
}


/* The print inside the drawing: the preview image, revealed from the bottom up to the progress, the rest as a ghost.
   With a filament colour the image is tinted in that colour. */
function printPart(id, { x, y, w, h, progress, thumb, tint }) {
  if (!thumb) return '';
  const top = y + h * (1 - progress / 100);
  const filter = tint ? `filter="url(#${id}-tint)"` : '';
  return `<defs>
      <clipPath id="${id}-done"><rect x="${x}" y="${top}" width="${w}" height="${y + h - top}"/></clipPath>
      ${tint ? `<filter id="${id}-tint" color-interpolation-filters="sRGB">
        <feColorMatrix type="saturate" values="0"/>
        <feComponentTransfer result="grey"><feFuncR type="linear" slope=".55" intercept=".5"/><feFuncG type="linear" slope=".55" intercept=".5"/><feFuncB type="linear" slope=".55" intercept=".5"/></feComponentTransfer>
        <feFlood flood-color="${tint}" result="col"/>
        <feBlend in="col" in2="grey" mode="multiply" result="mix"/>
        <feComposite in="mix" in2="SourceAlpha" operator="in"/></filter>` : ''}
    </defs>
    <image href="${esc(thumb)}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMax meet" opacity=".22" ${filter}/>
    <image href="${esc(thumb)}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMax meet" clip-path="url(#${id}-done)" ${filter}/>`;
}

/* Creality K1 Max style: dark cube, glass door, CoreXY toolhead above the print. Original artwork. */
function k1Svg(id, o) {
  const pTop = 92 + 104 * (1 - o.progress / 100);   // top of the printed part
  const headY = o.thumb ? Math.min(178, Math.max(80, pTop - 22)) : 86;
  return `<svg viewBox="0 0 300 260" class="printer ${o.printing ? 'printing' : ''}" aria-hidden="true">
    <defs>
      <linearGradient id="${id}-body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2b2b2e"/><stop offset="1" stop-color="#17171a"/></linearGradient>
      <linearGradient id="${id}-glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfe6f7" stop-opacity=".10"/><stop offset="1" stop-color="#cfe6f7" stop-opacity=".03"/></linearGradient>
      <radialGradient id="${id}-led" cx=".5" cy="0" r=".9"><stop offset="0" stop-color="#fff2c4" stop-opacity="${o.lightOn ? '.22' : '0'}"/><stop offset="1" stop-color="#fff7d6" stop-opacity="0"/></radialGradient>
    </defs>
    <ellipse cx="150" cy="248" rx="104" ry="7" fill="#000" opacity=".18"/>
    <rect x="56" y="22" width="188" height="222" rx="12" fill="url(#${id}-body)"/>
    <rect x="56" y="22" width="188" height="12" rx="6" fill="#3a3a3e"/>
    <rect x="68" y="44" width="164" height="168" rx="6" fill="#26272c"/>
    <rect x="68" y="44" width="164" height="168" rx="6" fill="url(#${id}-led)"/>
    <rect x="76" y="198" width="148" height="7" rx="2" fill="#4a4a50"/>
    <rect x="80" y="196" width="140" height="3" rx="1.5" fill="#6d6d75"/>
    <g>${printPart(id, { x: 98, y: 92, w: 104, h: 104, progress: o.progress, thumb: o.thumb, tint: o.tint })}</g>
    <g class="gantry" style="transform: translateY(${headY - 86}px)">
      <rect x="72" y="78" width="156" height="5" rx="2.5" fill="#55555c"/>
      <g class="head">
        <rect x="134" y="70" width="32" height="20" rx="4" fill="#d7d7dc"/>
        <rect x="138" y="74" width="24" height="3" rx="1.5" fill="#9a9aa2"/>
        <path d="M144 90h12l-3 7h-6z" fill="#e8a33a"/>
      </g>
    </g>
    <rect x="68" y="44" width="164" height="168" rx="6" fill="url(#${id}-glass)" stroke="#3b3b40" stroke-width="2"/>
    <path d="M92 52l-16 40M108 52l-26 62" stroke="#fff" stroke-opacity=".07" stroke-width="5" stroke-linecap="round"/>
    <rect x="226" y="120" width="4" height="34" rx="2" fill="#4a4a50"/>
    <rect x="70" y="220" width="62" height="16" rx="3" fill="#0e0e10" stroke="#38383d"/>
    <rect x="73" y="223" width="22" height="10" rx="1.5" fill="${o.active ? '#1e88e5' : '#2a2a2e'}" opacity=".9"/>
    <rect x="62" y="243" width="20" height="6" rx="2" fill="#2a2a2e"/><rect x="218" y="243" width="20" height="6" rx="2" fill="#2a2a2e"/>
  </svg>`;
}

/* Anycubic Kobra S1 style with ACE Pro on top: four spools in their real colours, active slot outlined. Original artwork. */
function kobraSvg(id, o) {
  const pTop = 132 + 92 * (1 - o.progress / 100);
  const headY = o.thumb ? Math.min(206, Math.max(120, pTop - 20)) : 126;
  const slots = [0, 1, 2, 3].map((i) => {
    const s = o.spools.find((x) => x.n === i + 1);
    const col = s && isHex(s.color) ? s.color : '#3a3a3e';
    const x = 92 + i * 30;
    return `<g>
      <rect x="${x}" y="22" width="26" height="40" rx="4" fill="#26262a" ${s && s.active ? 'stroke="#e53935" stroke-width="2.5"' : 'stroke="#3d3d42"'}/>
      <rect x="${x + 4}" y="27" width="4" height="30" rx="2" fill="#3f3f45"/><rect x="${x + 18}" y="27" width="4" height="30" rx="2" fill="#3f3f45"/>
      ${s && s.loaded !== false ? `<rect x="${x + 8}" y="36" width="10" height="12" rx="2" fill="${col}"/><rect x="${x + 8}" y="36" width="10" height="3" rx="1.5" fill="#fff" opacity=".25"/>` : ''}
    </g>`;
  }).join('');
  const active = o.spools.find((s) => s.active);
  const tube = active && isHex(active.color) ? active.color : '#d84b3e';
  return `<svg viewBox="0 0 300 300" class="printer ${o.printing ? 'printing' : ''}" aria-hidden="true">
    <defs>
      <linearGradient id="${id}-body" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a2a2d"/><stop offset="1" stop-color="#161618"/></linearGradient>
      <linearGradient id="${id}-glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e6f0f7" stop-opacity=".16"/><stop offset="1" stop-color="#e6f0f7" stop-opacity=".05"/></linearGradient>
      <radialGradient id="${id}-led" cx=".5" cy="0" r=".9"><stop offset="0" stop-color="#fff2c4" stop-opacity="${o.lightOn ? '.35' : '0'}"/><stop offset="1" stop-color="#fff7d6" stop-opacity="0"/></radialGradient>
    </defs>
    <ellipse cx="150" cy="290" rx="100" ry="6" fill="#000" opacity=".18"/>
    ${o.spools.length ? `<rect x="80" y="10" width="140" height="62" rx="8" fill="#1b1b1e"/>
      <rect x="92" y="13" width="116" height="4" rx="2" fill="#3a3a40"/>${slots}
      <rect x="92" y="64" width="116" height="4" rx="2" fill="#2f2f34"/>
      <circle cx="212" cy="18" r="2" fill="${o.active ? '#29b6f6' : '#555'}"/>
      <path d="M220 52 C 250 52, 252 84, 228 96" stroke="${tube}" stroke-width="3.5" fill="none" stroke-linecap="round"/>` : ''}
    <rect x="60" y="86" width="180" height="198" rx="10" fill="url(#${id}-body)"/>
    <rect x="196" y="90" width="34" height="18" rx="3" fill="#2f3440"/><rect x="204" y="95" width="10" height="9" rx="1.5" fill="#3d4a66"/>
    <rect x="70" y="112" width="160" height="150" rx="5" fill="#f3f4f6" opacity=".96"/>
    <rect x="70" y="112" width="160" height="150" rx="5" fill="url(#${id}-led)"/>
    <rect x="80" y="244" width="140" height="7" rx="2" fill="#c9ccd2"/>
    <g>${printPart(id, { x: 104, y: 132, w: 92, h: 112, progress: o.progress, thumb: o.thumb, tint: o.tint })}</g>
    <g class="gantry" style="transform: translateY(${headY - 126}px)">
      <rect x="74" y="120" width="152" height="6" rx="3" fill="#b8bcc4"/>
      <rect x="74" y="118" width="10" height="10" rx="2" fill="#3a3a40"/><rect x="216" y="118" width="10" height="10" rx="2" fill="#3a3a40"/>
      <g class="head">
        <rect x="132" y="110" width="36" height="22" rx="4" fill="#26272b"/>
        <rect x="150" y="114" width="4" height="12" rx="2" fill="#4fc3f7"/>
        <path d="M144 132h12l-3 7h-6z" fill="#e0e0e0"/><path d="M148 139h4l-2 3z" fill="#e8a33a"/>
      </g>
    </g>
    <rect x="70" y="112" width="160" height="150" rx="5" fill="url(#${id}-glass)" stroke="#2f2f34" stroke-width="2"/>
    <path d="M96 120l-18 44M112 120l-24 58" stroke="#fff" stroke-opacity=".35" stroke-width="4" stroke-linecap="round"/>
    <rect x="60" y="264" width="180" height="20" rx="6" fill="#1c1c1f"/>
    <rect x="72" y="284" width="22" height="6" rx="2" fill="#38383d"/><rect x="206" y="284" width="22" height="6" rx="2" fill="#38383d"/>
  </svg>`;
}

const CSS = `<style>
  ha-card { --cpc-accent: var(--primary-color); padding: 16px; overflow: hidden; position: relative; container-type: inline-size; }
  ha-card::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--cpc-status); opacity: .85; }
  .msg { padding: 8px 0; color: var(--secondary-text-color); }
  .head { display: flex; align-items: center; gap: 8px 12px; flex-wrap: wrap; }
  .logo { --mdc-icon-size: 28px; color: var(--cpc-status); background: color-mix(in srgb, var(--cpc-status) 14%, transparent);
    border-radius: 12px; padding: 8px; flex: none; }
  .title { flex: 1 1 120px; min-width: 0; }
  .name { font-size: 1.1rem; font-weight: 600; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sub { color: var(--secondary-text-color); font-size: .85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: .8rem; font-weight: 500;
    background: color-mix(in srgb, var(--cpc-status) 16%, transparent); color: var(--primary-text-color); cursor: pointer; white-space: nowrap; }
  .tools { display: flex; align-items: center; gap: 2px; margin-left: auto; }
  .tools .chip { margin-right: 2px; }
  .icon.upd { color: var(--primary-color); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--cpc-status); }
  button { font: inherit; cursor: pointer; }
  .icon { border: none; background: none; color: var(--secondary-text-color); border-radius: 50%; padding: 6px; display: flex; }
  .icon.on { color: var(--state-light-on-color, #f5b301); }
  .icon:disabled { opacity: .4; cursor: default; }

  .stage { position: relative; margin: 8px 0 4px; }
  .draw { position: relative; max-width: 300px; margin: 0 auto; cursor: pointer; }
  .printer { display: block; width: 100%; height: auto; }
  .gantry { transition: transform 1s ease; }
  .printing .head { animation: cpc-move 2.6s ease-in-out infinite alternate; }
  @keyframes cpc-move { from { transform: translateX(-34px); } to { transform: translateX(34px); } }
  @media (prefers-reduced-motion: reduce) { .printing .head { animation: none; } }
  .pct.float { right: 4%; bottom: 12%; }
  .under .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 4px 0; text-align: center; }
  .views { position: absolute; left: 0; bottom: 6px; display: flex; gap: 4px; padding: 4px; border-radius: 999px;
    background: color-mix(in srgb, var(--primary-text-color) 70%, transparent); }
  .viewrow { display: flex; }
  .viewrow .views { position: static; }
  .views button { border: none; background: none; color: var(--card-background-color, #fff); border-radius: 50%; width: 34px; height: 34px;
    display: flex; align-items: center; justify-content: center; }
  .views button ha-icon { --mdc-icon-size: 20px; }
  .views button.sel { background: var(--card-background-color, #fff); color: var(--primary-text-color); }

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
    border-radius: 999px; padding: 1px 8px; font-weight: 700; font-size: .95rem; color: var(--primary-text-color); }
  .pct small { font-size: .7rem; font-weight: 500; }
  .stats { display: grid; gap: 12px; flex: 1; }
  .stat { display: flex; flex-direction: column; }
  .label { color: var(--secondary-text-color); font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; }
  .big { font-size: 1.5rem; font-weight: 600; line-height: 1.2; }

  .slicer { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .slicer span { display: inline-flex; flex-direction: column; padding: 6px 10px; border-radius: 10px; font-size: .72rem;
    color: var(--secondary-text-color); border: 1px solid var(--divider-color, rgba(127,127,127,.25)); line-height: 1.25; }
  .slicer b { color: var(--primary-text-color); font-size: .9rem; font-weight: 600; }

  .temps { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px; margin-top: 10px; }
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
  @container (max-width: 300px) { .big { font-size: 1.1rem; white-space: nowrap; } .label { font-size: .68rem; } }
  @container (max-width: 400px) { .temp { padding: 8px; gap: 6px; } .temp ha-icon { display: none !important; } .temp .val small { font-size: .75rem; } }
  @media (max-width: 420px) { .body { gap: 14px; } .ring { width: 112px; height: 112px; } .ring img { inset: 14px; width: 84px; height: 84px; } .big { font-size: 1.25rem; } }
</style>`;


/* Popup with the print history: timelapse playback and "print again". Lives on document.body so it covers the
   whole screen, whatever dashboard layout the card is in. */
class CrealityPrintDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._video = null;
    this._onKey = (ev) => { if (ev.key === 'Escape') this._close(); };
  }

  connectedCallback() { document.addEventListener('keydown', this._onKey); }

  disconnectedCallback() { document.removeEventListener('keydown', this._onKey); }

  update(hass, snap) {
    this._hass = hass;
    this._snap = snap;
    if (!this._video) this._render();   // don't rebuild while a video plays
  }

  _t(k) { return tr(this._hass, k); }

  _close() { this.dispatchEvent(new CustomEvent('closed')); }

  _render() {
    const s = this._snap, hass = this._hass;
    if (!s) return;
    const lang = hass.locale ? hass.locale.language : undefined;
    const items = s.history || [];
    const canPrint = s.online && !s.active;
    const row = (r, i) => {
      const look = STATUS[r.state] || STATUS.idle;
      const when = r.start ? new Date(r.start * 1000).toLocaleString(lang, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
      const reprintTitle = !r.on_printer ? this._t('reprintNotOnPrinter') : !canPrint ? this._t('reprintBusy') : this._t('reprint');
      return `<li>
        <div class="thumb ${r.timelapse ? 'play' : ''}" ${r.timelapse ? `data-play="${i}" title="${esc(this._t('timelapse'))}"` : ''}>
          ${r.thumbnail || r.timelapse_cover ? `<img src="${esc(r.timelapse_cover || r.thumbnail)}" alt="" loading="lazy">` : '<ha-icon icon="mdi:cube-outline"></ha-icon>'}
          ${r.timelapse ? '<span class="playicon"><ha-icon icon="mdi:play"></ha-icon></span>' : ''}
        </div>
        <div class="info">
          <div class="nm">${esc(cleanJob(r.name))}</div>
          <div class="meta"><span class="st" style="--c:${look.color}">${esc(this._t(r.state))}</span>${esc(when)}${r.duration ? ' · ' + dur(r.duration) : ''}</div>
        </div>
        <div class="btns">
          ${r.timelapse ? `<button data-play="${i}" title="${esc(this._t('timelapse'))}"><ha-icon icon="mdi:play-circle-outline"></ha-icon></button>` : ''}
          ${s.platform === 'creality_cloud' ? `<button data-reprint="${i}" title="${esc(reprintTitle)}" ${r.on_printer && canPrint ? '' : 'disabled'}><ha-icon icon="mdi:restart"></ha-icon></button>` : ''}
        </div>
      </li>`;
    };
    this.shadowRoot.innerHTML = `<div class="backdrop" data-close></div>
      <div class="dlg" role="dialog" aria-modal="true" aria-label="${esc(this._t('history'))}">
        <header><div><h2>${esc(this._t('history'))}</h2><div class="sub">${esc(s.name)}</div></div>
          <button class="x" data-close title="${esc(this._t('close'))}"><ha-icon icon="mdi:close"></ha-icon></button></header>
        ${this._video != null ? '' : items.length ? `<ul>${items.map(row).join('')}</ul>` : `<p class="empty">${esc(this._t('noHistory'))}</p>`}
      </div>${DIALOG_CSS}`;
    this.shadowRoot.querySelectorAll('[data-close]').forEach((el) => el.addEventListener('click', () => this._close()));
    this.shadowRoot.querySelectorAll('[data-play]').forEach((el) => el.addEventListener('click', () => this._play(items[+el.dataset.play])));
    this.shadowRoot.querySelectorAll('[data-reprint]').forEach((el) => el.addEventListener('click', async () => {
      const r = items[+el.dataset.reprint];
      if (!confirm(this._t('reprintConfirm').replace('%s', cleanJob(r.name)).replace('%s', s.name))) return;
      el.disabled = true;
      try {
        await hass.callService('creality_cloud', 'reprint', { device_id: s.device_id, file_name: r.name.split('/').pop() });
        this._close();
      } catch (e) { el.disabled = false; alert(e.message || e); }
    }));
  }

  _play(r) {
    this._video = r;
    this._render();
    const dlg = this.shadowRoot.querySelector('.dlg');
    const box = document.createElement('div');
    box.className = 'player';
    box.innerHTML = `<button class="back" title="${esc(this._t('history'))}"><ha-icon icon="mdi:arrow-left"></ha-icon>${esc(cleanJob(r.name))}</button>`;
    const v = document.createElement('video');
    v.src = r.timelapse;   // only Creality CDN URLs reach this point (checked by the integration)
    v.controls = true; v.autoplay = true; v.playsInline = true; v.loop = true;
    if (r.timelapse_cover || r.thumbnail) v.poster = r.timelapse_cover || r.thumbnail;
    box.append(v);
    dlg.append(box);
    box.querySelector('.back').addEventListener('click', () => { this._video = null; this._render(); });
  }
}

const DIALOG_CSS = `<style>
  :host { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; font-family: var(--paper-font-body1_-_font-family, inherit); }
  .backdrop { position: absolute; inset: 0; background: rgba(0,0,0,.5); }
  .dlg { position: relative; width: min(560px, calc(100vw - 24px)); max-height: calc(100vh - 48px); overflow: auto; border-radius: 20px;
    background: var(--card-background-color, #fff); color: var(--primary-text-color); box-shadow: 0 12px 40px rgba(0,0,0,.35); padding: 16px 16px 20px; }
  header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
  h2 { margin: 0; font-size: 1.2rem; font-weight: 600; }
  .sub { color: var(--secondary-text-color); font-size: .85rem; }
  button { font: inherit; cursor: pointer; border: none; background: none; color: inherit; }
  .x { border-radius: 50%; padding: 8px; display: flex; }
  ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  li { display: flex; align-items: center; gap: 12px; padding: 8px; border-radius: 12px; background: var(--secondary-background-color, rgba(127,127,127,.08)); }
  .thumb { position: relative; width: 56px; height: 56px; flex: none; border-radius: 10px; overflow: hidden; display: flex; align-items: center; justify-content: center;
    background: var(--card-background-color, #fff); color: var(--secondary-text-color); }
  .thumb img { width: 100%; height: 100%; object-fit: contain; }
  .thumb.play { cursor: pointer; }
  .playicon { position: absolute; inset: auto 4px 4px auto; background: rgba(0,0,0,.6); color: #fff; border-radius: 50%; display: flex; padding: 2px; --mdc-icon-size: 16px; }
  .info { flex: 1; min-width: 0; }
  .nm { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .meta { color: var(--secondary-text-color); font-size: .8rem; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .st { color: var(--c); font-weight: 600; }
  .btns { display: flex; gap: 2px; }
  .btns button { border-radius: 50%; padding: 8px; display: flex; color: var(--primary-color); }
  .btns button:disabled { color: var(--disabled-text-color, #999); cursor: default; }
  .empty { color: var(--secondary-text-color); }
  .player { display: grid; gap: 10px; }
  .back { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; justify-self: start; padding: 4px 0; }
  video { width: 100%; max-height: 70vh; border-radius: 12px; background: #000; }
</style>`;

/* Visual editor for the single card, built on Home Assistant's own ha-form. */
class CrealityPrintCardEditor extends HTMLElement {
  setConfig(config) { this._config = { ...config }; this._render(); }

  set hass(hass) { this._hass = hass; if (this._form) this._form.hass = hass; else this._render(); }

  _t(k) { return tr(this._hass, k); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.computeLabel = (s) => this._t('e_' + s.name);
      this._form.addEventListener('value-changed', (ev) => {
        const cfg = { ...ev.detail.value };
        for (const k of ['show_slicer', 'show_temperatures', 'show_controls', 'show_view_switch', 'show_history']) if (cfg[k] === true) delete cfg[k];   // defaults stay out of the YAML
        if (cfg.view === 'printer') delete cfg.view;
        if (!cfg.name) delete cfg.name;
        this._config = cfg;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: cfg }, bubbles: true, composed: true }));
      });
      this.append(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = [
      { name: 'entity', required: true, selector: { entity: { filter: [{ integration: 'creality_cloud' }, { integration: 'anycubic_cloud' }] } } },
      { name: 'name', selector: { text: {} } },
      { name: 'view', selector: { select: { mode: 'dropdown', options: [
        { value: 'printer', label: this._t('viewPrinter') }, { value: 'preview', label: this._t('viewPreview') }] } } },
      { name: 'show_slicer', selector: { boolean: {} } },
      { name: 'show_temperatures', selector: { boolean: {} } },
      { name: 'show_controls', selector: { boolean: {} } },
      { name: 'show_view_switch', selector: { boolean: {} } },
      { name: 'show_history', selector: { boolean: {} } },
    ];
    this._form.data = { view: 'printer', show_slicer: true, show_temperatures: true, show_controls: true, show_view_switch: true,
      show_history: true, ...this._config };
  }
}

/* Printer group: every printer in one compact list. */
class CrealityPrintGroupCard extends HTMLElement {
  setConfig(config) { this._config = { ...(config || {}) }; this._key = null; }

  static getConfigElement() { return document.createElement('creality-print-group-card-editor'); }

  static getStubConfig() { return {}; }

  getCardSize() { return 1 + (this._rows || 2) * 2; }

  getGridOptions() { return { columns: 12, min_columns: 6, rows: 'auto' }; }

  set hass(hass) {
    this._hass = hass;
    const list = (this._config.entities && this._config.entities.length ? this._config.entities.map((e) => ({ entity: e })) : allPrinters(hass));
    const snaps = list.map((p) => snapshot(hass, p.entity)).filter(Boolean)
      .filter((s) => this._config.show_idle !== false || s.active || s.done);
    const key = JSON.stringify(snaps.map((s) => snapKey(hass, s.ids)));
    if (key === this._key) return;
    this._key = key;
    this._rows = snaps.length;
    this._render(snaps);
  }

  _t(k) { return tr(this._hass, k); }

  _render(snaps) {
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    const hass = this._hass;
    const lang = hass.locale ? hass.locale.language : undefined;
    const title = this._config.title ?? this._t('groupTitle');
    const active = snaps.filter((s) => s.active).length;
    const row = (s, i) => {
      const nozzle = s.c.num('nozzle'), bed = s.c.num('bed');
      const end = s.ends ? s.ends.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' }) : null;
      return `<div class="row" data-i="${i}" style="--cpc-status:${s.look.color}">
        <div class="pic">${s.thumb ? `<img src="${esc(s.thumb)}" alt="">` : `<ha-icon icon="${s.look.icon}"></ha-icon>`}</div>
        <div class="main">
          <div class="top"><span class="nm">${esc(s.name)}</span><span class="chip"><span class="dot"></span>${esc(this._t(s.state))}</span></div>
          <div class="job">${esc(s.active || s.done ? s.job : this._t('noJob'))}</div>
          ${s.active ? `<div class="bar"><i style="width:${s.progress}%"></i></div>
            <div class="meta"><b>${Math.round(s.progress)}%</b><span>${esc(this._t('remaining'))} ${dur(s.remaining)}</span>${end ? `<span>${esc(this._t('ends'))} ${esc(end)}</span>` : ''}</div>`
          : `<div class="meta">${nozzle != null ? `<span><ha-icon icon="mdi:printer-3d-nozzle-heat"></ha-icon>${Math.round(nozzle)}°</span>` : ''}${bed != null ? `<span><ha-icon icon="mdi:radiator"></ha-icon>${Math.round(bed)}°</span>` : ''}${s.update ? `<span class="upd"><ha-icon icon="mdi:package-up"></ha-icon>${esc(this._t('update'))}</span>` : ''}</div>`}
        </div>
      </div>`;
    };
    this.shadowRoot.innerHTML = `<ha-card>
      ${title ? `<div class="head"><span>${esc(title)}</span>${active ? `<span class="count">${active} ${esc(this._t('printing').toLowerCase())}</span>` : ''}</div>` : ''}
      ${snaps.length ? snaps.map(row).join('') : `<div class="empty">${esc(this._t('noPrinters'))}</div>`}
    </ha-card>${GROUP_CSS}`;
    this.shadowRoot.querySelectorAll('[data-i]').forEach((el) => el.addEventListener('click', () => {
      const s = snaps[+el.dataset.i];
      moreInfo(this, s.ids.status || s.ids.progress || s.ids.busy);
    }));
  }
}

const GROUP_CSS = `<style>
  ha-card { padding: 12px 16px 8px; }
  .head { display: flex; align-items: baseline; justify-content: space-between; font-size: 1.1rem; font-weight: 600; padding: 4px 0 8px; }
  .count { font-size: .8rem; font-weight: 500; color: var(--primary-color); }
  .row { display: flex; gap: 12px; align-items: center; padding: 10px 0; border-top: 1px solid var(--divider-color, rgba(127,127,127,.2)); cursor: pointer; }
  .row:first-of-type { border-top: none; }
  .head + .row { border-top: none; }
  .pic { width: 52px; height: 52px; flex: none; border-radius: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden;
    background: color-mix(in srgb, var(--cpc-status) 14%, transparent); color: var(--cpc-status); --mdc-icon-size: 26px; }
  .pic img { width: 100%; height: 100%; object-fit: contain; }
  .main { flex: 1; min-width: 0; }
  .top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .nm { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 999px; font-size: .75rem; font-weight: 500; flex: none;
    background: color-mix(in srgb, var(--cpc-status) 16%, transparent); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--cpc-status); }
  .job { color: var(--secondary-text-color); font-size: .85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bar { height: 6px; border-radius: 999px; background: var(--divider-color, rgba(127,127,127,.25)); overflow: hidden; margin: 6px 0 4px; }
  .bar i { display: block; height: 100%; background: var(--cpc-status); border-radius: 999px; transition: width .8s ease; }
  .meta { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: .8rem; color: var(--secondary-text-color); align-items: center; }
  .meta b { color: var(--primary-text-color); }
  .meta span { display: inline-flex; align-items: center; gap: 3px; }
  .meta ha-icon { --mdc-icon-size: 15px; }
  .upd { color: var(--primary-color); }
  .empty { color: var(--secondary-text-color); padding: 8px 0 12px; }
</style>`;

class CrealityPrintGroupCardEditor extends HTMLElement {
  setConfig(config) { this._config = { ...config }; this._render(); }

  set hass(hass) { this._hass = hass; if (this._form) this._form.hass = hass; else this._render(); }

  _t(k) { return tr(this._hass, k); }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.computeLabel = (s) => this._t('e_' + s.name);
      this._form.addEventListener('value-changed', (ev) => {
        const cfg = { ...ev.detail.value };
        if (cfg.show_idle === true) delete cfg.show_idle;
        if (!cfg.entities || !cfg.entities.length) delete cfg.entities;
        this._config = cfg;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: cfg }, bubbles: true, composed: true }));
      });
      this.append(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = [
      { name: 'title', selector: { text: {} } },
      { name: 'entities', selector: { entity: { multiple: true, filter: [
        { integration: 'creality_cloud', domain: 'sensor' }, { integration: 'anycubic_cloud', domain: 'sensor' }] } } },
      { name: 'show_idle', selector: { boolean: {} } },
    ];
    this._form.data = { show_idle: true, ...this._config };
  }
}

const define = (name, cls) => { if (!customElements.get(name)) customElements.define(name, cls); };
define('creality-print-dialog', CrealityPrintDialog);
define('creality-print-card-editor', CrealityPrintCardEditor);
define('creality-print-group-card-editor', CrealityPrintGroupCardEditor);
if (!customElements.get('creality-print-card')) {
  define('creality-print-card', CrealityPrintCard);
  define('creality-print-group-card', CrealityPrintGroupCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'creality-print-card',
    name: 'Creality Print Card',
    description: 'Printer drawing with live progress, slicer info, temperatures, history with timelapse, and controls. Works with Creality Cloud and Anycubic Cloud.',
    preview: true,
    documentationURL: 'https://github.com/Rein033/ha-creality-cloud',
  }, {
    type: 'creality-print-group-card',
    name: 'Creality Print Group',
    description: 'All your 3D printers in one compact list: status, progress and finish time.',
    preview: true,
    documentationURL: 'https://github.com/Rein033/ha-creality-cloud',
  });
}
