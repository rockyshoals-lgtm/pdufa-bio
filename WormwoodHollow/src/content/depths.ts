/**
 * The Nine Depths under Bald Knob — the difficulty ladder (Story Bible §11, §7).
 * Deeper is older and worse; the master-rune (the binding stone) lies at Depth 9.
 * Four of the depths are guarded by a Lord (see bosses.ts). Each depth carries a
 * hazard line used as expedition flavor.
 */
import { bossAtDepth, type Boss } from './bosses';

export interface Depth {
  level: number; // 1..9
  name: string;
  hazard: string;
}

export const DEPTHS: readonly Depth[] = [
  { level: 1, name: 'The Root Cellar', hazard: 'Cold seep-damp and a smell of turned earth. The roots down here move when the lamp is elsewhere.' },
  { level: 2, name: 'The Sinkhole Stair', hazard: 'A throat of broken limestone dropping into dark. Every step is loose; the walls sweat black.' },
  { level: 3, name: 'The Drowned Church', hazard: 'A chapel sunk to its rafters in still black water. Pews stand in rows beneath the surface, and they are not empty.' },
  { level: 4, name: 'The Grist Below', hazard: 'The lost mill, its wheel still turning in a current that has no source. The dust here is flour, and worse.' },
  { level: 5, name: "Bledsoe's Warren", hazard: 'A granny\'s cabin folded impossibly into the rock, apron on the peg, kettle warm, no one home.' },
  { level: 6, name: 'The Black Spring', hazard: 'The wellhead of the Rot itself — Wormwood water rising from a crack older than the county.' },
  { level: 7, name: "The Gowrow's Den", hazard: 'A gallery of shed hide and cracked bone, ceiling scored by tusks. Something vast breathes in the dark ahead.' },
  { level: 8, name: 'The Whispering Dark', hazard: 'No floor you can trust, no silence you can keep. Old Gnaw is close here; the stone remembers your name.' },
  { level: 9, name: 'The Bottom of the World', hazard: 'The binding stone. The true name, half-scoured, cut into living rock by hands a thousand years gone.' },
];

export function depthAt(level: number): Depth | undefined {
  return DEPTHS.find((d) => d.level === level);
}

/** The boss guarding a given depth, if any. */
export function bossForDepth(level: number): Boss | undefined {
  return bossAtDepth(level);
}
