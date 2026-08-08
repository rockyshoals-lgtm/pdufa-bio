/**
 * The three endings (Story Bible §11). All are reached at the master-rune (Depth 9,
 * nine shards in hand); they differ in what the keeper chooses to do with the name.
 *
 *  - Re-bind : salt the door for another century. The cycle continues, but the
 *              bloodline inherits everything you learned — the strongest legacy.
 *  - Unmake  : destroy the binding AND the thing. True victory, at terrible cost —
 *              and only possible with deep knowledge of the true name (lore gate).
 *  - Inherit : take the worm's place at the bottom. The tragic mirror; the hollow
 *              is saved because you become its warden.
 */
import { CONFIG } from '../config';
import { clamp, logLine, type GameState } from '../state';

export interface Ending {
  id: 'rebind' | 'unmake' | 'inherit';
  name: string;
  /** short menu blurb */
  blurb: string;
  /** requirement text shown when locked */
  requirement: string;
  available(s: GameState): boolean;
  /** apply the ending: mutate the (working-copy) state and log. */
  apply(s: GameState): void;
}

function atMasterRune(s: GameState): boolean {
  return s.runesRecovered >= CONFIG.DEPTHS && s.depthCleared >= CONFIG.DEPTHS;
}

export const ENDINGS: readonly Ending[] = [
  {
    id: 'rebind',
    name: 'Re-bind the Name',
    blurb: 'Salt the door for another hundred years. The line holds. The thing sleeps. Your kin inherit all you know.',
    requirement: 'Nine shards, and the bottom reached.',
    available: atMasterRune,
    apply: (s) => {
      s.ending = 'rebind';
      s.flags.won = true;
      s.rot = clamp(s.rot - 40, 0, 100);
      // The strongest legacy: what you learned floods down the bloodline.
      s.inheritedLore += Math.floor(s.resources.lore * 0.5) + s.runesRecovered * 5;
      logLine(
        s,
        'You set iron to the first stone and cut the name anew. The mountain goes quiet — for a hundred years, if the next hands are steady. You have bought time. It was always only ever time.',
        'good',
      );
    },
  },
  {
    id: 'unmake',
    name: 'Unmake the Name',
    blurb: 'Not re-bind — erase. Scour the true name from the rock and end Old Gnaw forever. Requires deep knowledge of the name.',
    requirement: `Nine shards, the bottom reached, and ${CONFIG.ENDING_UNMAKE_LORE} lore — the whole true name.`,
    available: (s) => atMasterRune(s) && s.resources.lore >= CONFIG.ENDING_UNMAKE_LORE,
    apply: (s) => {
      s.ending = 'unmake';
      s.flags.won = true;
      s.rot = 0;
      logLine(
        s,
        'You do not re-cut the name. You unspeak it — letter by letter, the way it was spoken to bind, run backward to loose and end. The Rot draws down out of the wells and the roots and the graves. Bald Knob settles. There is nothing under the mountain anymore. The salt, at last, is just salt.',
        'good',
      );
    },
  },
  {
    id: 'inherit',
    name: 'Become the Warden',
    blurb: 'The binding needs a keeper on the inside. Take the worm\'s place. The hollow lives because you do not.',
    requirement: 'Nine shards, and the bottom reached.',
    available: atMasterRune,
    apply: (s) => {
      s.ending = 'inherit';
      s.flags.won = true;
      s.rot = clamp(s.rot - 60, 0, 100);
      logLine(
        s,
        'The binding was never words alone. It was always someone, down here, holding. You lie down against the cold stone and take up the weight, and above you the hollow greens again and forgets your name. You are the thing the salt keeps in, now. You are very patient. You will have to be.',
        'good',
      );
    },
  },
];

export function endingById(id: string): Ending | undefined {
  return ENDINGS.find((e) => e.id === id);
}
