/** Tiny typed DOM helpers. Views are plain TS — no framework (Fable Brief §2). */

export function byId<T extends HTMLElement = HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Missing #${id} in DOM`);
  return el as T;
}

export function setText(id: string, text: string | number): void {
  byId(id).textContent = String(text);
}

/** Set a meter bar's fill width (0..100) and color. */
export function setBar(id: string, pct: number, color: string): void {
  const el = byId(id);
  el.style.width = Math.max(0, Math.min(100, pct)) + '%';
  el.style.background = color;
}
