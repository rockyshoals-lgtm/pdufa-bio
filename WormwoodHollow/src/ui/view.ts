/**
 * The meta/idle DOM view. Framework-free: builds a static layout once, then reads
 * GameState on every change and updates the dynamic bits. Views never mutate state —
 * they dispatch through the Game controller.
 */
import { CONFIG } from '../config';
import { loreMult, round1, RESOURCES, type GameState } from '../state';
import { availableActions } from '../content/actions';
import { depthAt } from '../content/depths';
import { ENDINGS, endingById } from '../content/endings';
import { PROLOGUE } from '../content/prologue';
import type { Game, ComeMorningInfo } from '../core/game';
import { byId, setText, setBar } from './dom';

const LAYOUT = `
  <div class="wrap">
    <h1>Wormwood Hollow</h1>
    <div class="tag">The salt is not for luck.</div>

    <div class="row">
      <div class="panel grow">
        <div class="hd">The Keeper</div>
        <div class="keeper">
          <div><span class="kn" id="kname">—</span><span class="stage" id="kstage">child</span></div>
          <div class="kmeta" id="kmeta">—</div>
        </div>
        <div class="meter">
          <div class="ml"><span>The Rot</span><b><span id="rotv">0</span>%</b></div>
          <div class="bar"><i id="rotbar" style="width:0%;background:var(--rot)"></i></div>
        </div>
        <div class="meter">
          <div class="ml"><span>Ward (salt &amp; iron)</span><b><span id="wardv">0</span>%</b></div>
          <div class="bar"><i id="wardbar" style="width:0%;background:var(--ward)"></i></div>
        </div>
        <div class="meter">
          <div class="ml"><span>Depths pushed back</span><b><span id="depthv">0</span> / ${CONFIG.DEPTHS}</b></div>
          <div class="bar"><i id="depthbar" style="width:0%;background:#5a6b8a"></i></div>
        </div>
        <div class="depthname" id="depthname"></div>
        <div class="kmeta" style="margin-top:6px">Binding runes recovered: <b id="runev" style="color:var(--gold)">0</b> / ${CONFIG.DEPTHS}</div>
        <div class="wonbanner" id="wonbanner" style="display:none"></div>
      </div>

      <div class="panel grow">
        <div class="hd">Stores</div>
        <div class="res">
          <div class="r"><div class="n">Salt</div><div class="v" id="r_salt">0</div><div class="p" id="p_salt"></div></div>
          <div class="r"><div class="n">Iron</div><div class="v" id="r_iron">0</div><div class="p" id="p_iron"></div></div>
          <div class="r"><div class="n">Herbs</div><div class="v" id="r_herbs">0</div><div class="p" id="p_herbs"></div></div>
          <div class="r"><div class="n">Lore</div><div class="v" id="r_lore">0</div><div class="p" id="p_lore"></div></div>
        </div>
        <div class="hd" style="margin-top:16px">Ways &amp; Works</div>
        <div class="acts" id="acts"></div>
      </div>
    </div>

    <div class="panel" style="margin-top:14px">
      <div class="hd">The Hollow Speaks</div>
      <div class="log" id="log"></div>
    </div>

    <div class="foot">
      <span>The salt holds only so long as salt does. Time is demo-accelerated.</span>
      <button id="btnAway">Simulate: away a while ⏾</button>
      <button id="btnReset">New bloodline ⟲</button>
      <span id="genlbl"></span>
    </div>
  </div>
`;

let GAME: Game | null = null;

/** Build layout, wire controls + hooks. Call once at boot. */
export function mount(game: Game): void {
  GAME = game;
  byId('app').innerHTML = LAYOUT;

  game.hooks = {
    onChange: (s) => renderState(s),
    onComeMorning: (info) => showComeMorning(info),
  };

  byId('btnAway').onclick = () => game.simulateAway(8);
  byId('btnReset').onclick = () => {
    if (confirm('Abandon this bloodline and begin a new one? All inherited lore is lost.')) {
      game.reset();
      maybeShowPrologue();
    }
  };
  byId('cmClose').onclick = () => byId('veil').classList.remove('on');
  byId('endCancel').onclick = () => byId('endVeil').classList.remove('on');
  byId('plNext').onclick = () => advancePrologue();
}

/** Show the Salt Line prologue if this life warrants it (fresh Gen-1). */
export function maybeShowPrologue(): void {
  if (GAME?.needsPrologue()) startPrologue();
}

export function renderState(s: GameState): void {
  setText('kname', `${s.keeperName} ${s.bloodlineName}`);
  setText('kstage', s.stage);
  setText('kmeta', `Age ${Math.floor(s.ageDays)} · Generation ${s.generation}`);
  setText('genlbl', `Gen ${s.generation} · inherited lore ${Math.floor(s.inheritedLore)}`);

  const rotColor = s.rot > 66 ? 'var(--rothi)' : s.rot > 33 ? '#b58a2a' : 'var(--rot)';
  setBar('rotbar', s.rot, rotColor);
  setText('rotv', Math.floor(s.rot));
  setBar('wardbar', s.wardStrength, 'var(--ward)');
  setText('wardv', Math.floor(s.wardStrength));
  setBar('depthbar', (s.depthCleared / CONFIG.DEPTHS) * 100, '#5a6b8a');
  setText('depthv', s.depthCleared);
  setText('runev', s.runesRecovered);

  byId('depthname').textContent =
    s.depthCleared <= 0
      ? 'At the surface. The cave-mouth waits on Bald Knob.'
      : s.depthCleared >= CONFIG.DEPTHS
        ? 'The bottom is reached — the binding stone lies before you.'
        : `Cleared to: ${depthAt(s.depthCleared)?.name ?? ''}`;

  const banner = byId('wonbanner');
  if (s.ending) {
    banner.style.display = '';
    banner.textContent = `The line ends here: ${endingById(s.ending)?.name ?? s.ending}.`;
  } else {
    banner.style.display = 'none';
  }

  const m = loreMult(s);
  for (const k of RESOURCES) {
    setText('r_' + k, Math.floor(s.resources[k]));
    const p = s.production[k] * m;
    byId('p_' + k).textContent = p > 0.001 ? `+${round1(p)}/day` : '';
  }

  renderActions(s);
  renderLog(s);
}

function atMasterRune(s: GameState): boolean {
  return s.runesRecovered >= CONFIG.DEPTHS && s.depthCleared >= CONFIG.DEPTHS;
}

function renderActions(s: GameState): void {
  const host = byId('acts');
  host.innerHTML = '';
  for (const a of availableActions(s)) {
    const b = document.createElement('button');
    b.className = 'act' + (a.danger ? ' danger' : '') + (a.rite ? ' rite' : '');
    const label = document.createElement('span');
    label.textContent = a.label;
    const cost = document.createElement('span');
    cost.className = 'c';
    cost.textContent = a.cost;
    b.append(label, cost);
    b.disabled = !a.can(s);
    b.onclick = () => GAME?.doAction(a.id);
    host.appendChild(b);
  }

  // The endgame rite: available at the master-rune, before an ending is chosen.
  if (atMasterRune(s) && !s.ending) {
    const b = document.createElement('button');
    b.className = 'act rite';
    const label = document.createElement('span');
    label.textContent = 'Approach the master-rune';
    const cost = document.createElement('span');
    cost.className = 'c';
    cost.textContent = 'the ending';
    b.append(label, cost);
    b.onclick = () => openEndings(s);
    host.appendChild(b);
  }
}

function renderLog(s: GameState): void {
  const host = byId('log');
  host.innerHTML = '';
  for (const e of s.log) {
    const div = document.createElement('div');
    div.className = 'e' + (e.c ? ' ' + e.c : '');
    div.textContent = e.t;
    host.appendChild(div);
  }
}

function showComeMorning(info: ComeMorningInfo): void {
  byId('cmSub').textContent = info.capped
    ? 'You were gone too long. The salt held only so long as salt does.'
    : 'You were away. The hollow did not rest.';

  const lines: [string, string, string?][] = [];
  lines.push(['Days turned', round1(info.days) + (info.capped ? ' (capped)' : '')]);
  lines.push(['The Rot', '+' + round1(info.report.rotGain) + '%', 'down']);
  lines.push(['Ward decayed', '-' + round1(info.report.wardLoss) + '%', 'down']);
  const h = info.report.harvest;
  const harv = RESOURCES.filter((k) => h[k] > 0.05)
    .map((k) => `+${round1(h[k])} ${k}`)
    .join('  ');
  if (harv) lines.push(['Gathered while gone', harv, 'up']);
  if (info.fell) lines.push(['The hollow', 'fell — the salt passed', 'down']);

  const host = byId('cmLines');
  host.innerHTML = '';
  for (const [k, v, cls] of lines) {
    const row = document.createElement('div');
    row.className = 'line';
    const ks = document.createElement('span');
    ks.className = 'k';
    ks.textContent = k;
    const vs = document.createElement('span');
    vs.className = 'v' + (cls ? ' ' + cls : '');
    vs.textContent = v;
    row.append(ks, vs);
    host.appendChild(row);
  }
  byId('veil').classList.add('on');
}

// --- Endings modal ---------------------------------------------------------

function openEndings(s: GameState): void {
  const host = byId('endList');
  host.innerHTML = '';
  for (const e of ENDINGS) {
    const ok = e.available(s);
    const b = document.createElement('button');
    b.className = 'endopt' + (e.id === 'unmake' ? ' unmake' : '');
    b.disabled = !ok;

    const name = document.createElement('span');
    name.className = 'en';
    name.textContent = e.name;
    const blurb = document.createElement('span');
    blurb.className = 'eb';
    blurb.textContent = e.blurb;
    b.append(name, blurb);
    if (!ok) {
      const lock = document.createElement('div');
      lock.className = 'lock';
      lock.textContent = 'Locked — ' + e.requirement;
      b.append(lock);
    }
    b.onclick = () => {
      if (!ok) return;
      GAME?.chooseEnding(e.id);
      byId('endVeil').classList.remove('on');
    };
    host.appendChild(b);
  }
  byId('endVeil').classList.add('on');
}

// --- Prologue sequence -----------------------------------------------------

let plIndex = 0;

function startPrologue(): void {
  plIndex = 0;
  renderPrologueBeat();
  byId('prologueVeil').classList.add('on');
}

function renderPrologueBeat(): void {
  const beat = PROLOGUE[plIndex];
  const body = byId('plBody');
  const isFinal = plIndex === PROLOGUE.length - 1;
  body.className = 'prologue' + (isFinal ? ' final' : '');
  body.innerHTML = '';
  if (beat.speaker) {
    const who = document.createElement('span');
    who.className = 'who';
    who.textContent = beat.speaker;
    body.appendChild(who);
  }
  const p = document.createElement('span');
  p.textContent = beat.text;
  body.appendChild(p);

  const dots = document.createElement('div');
  dots.className = 'pldot';
  dots.textContent = PROLOGUE.map((_, i) => (i === plIndex ? '●' : '·')).join(' ');
  body.appendChild(dots);

  byId('plNext').textContent = isFinal ? 'Lay the salt' : 'Go on';
}

function advancePrologue(): void {
  if (plIndex < PROLOGUE.length - 1) {
    plIndex++;
    renderPrologueBeat();
  } else {
    byId('prologueVeil').classList.remove('on');
    GAME?.markPrologueSeen();
  }
}

/** Set by main so action buttons can dispatch. */
export function bindGame(g: Game): void {
  GAME = g;
}
