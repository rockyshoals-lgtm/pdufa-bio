/**
 * FlavorBank — Ozark folk-gothic lines keyed by game event (Fable Brief §8; Story
 * Bible §3, §14). Pulls are seeded via the run RNG so a replay reads identically.
 * Old Gnaw's whispers escalate with the Rot: the closer the thing gets, the less it
 * bothers to stay quiet.
 */
import type { Rng } from '../rng';
import { pick } from '../rng';
import type { LifeStage } from '../state';

export const STAGE_FLAVOR: Record<Exclude<LifeStage, 'child'>, string> = {
  youth:
    "You're old enough now for the yarb-work and the forge. Old enough to wonder what the salt is really for.",
  grown:
    "Grown, and the cave-mouth on Bald Knob won't leave your dreams. You can go down now, if you dare.",
  keeper:
    'Your hands have gone to knots and your hair to salt-white. Time, soon, to teach a child the rhyme.',
};

export const FLAVOR = {
  boot: [
    'Grandma salted the sills every night of her life and never told us why. We thought it was for luck.',
  ],
  newBloodline: [
    'A new family comes up the hollow road, not knowing what waits under the mountain.',
  ],
  chosenPass: [
    'You fold a child\'s hands over the tin and tip it — a finger\'s width, all the way \'round — the way it was done for you.',
    'The rhyme passes to smaller hands. You are the granny now, and you still won\'t say what the salt is for.',
  ],
  expeditionWin: [
    'You push the Rot back a depth and come up with lore for it.',
    'Hard ground gained. You climb toward the light with the dark a little farther below.',
  ],
  expeditionRune: [
    'Down in the dark you pried loose a rune-shard — a piece of the binding, warm and wrong in your hand.',
  ],
  expeditionLoss: [
    'The blighted were thick in the dark. You barely made the surface, and the Rot followed you up.',
    "A wrong turn, a cold breath, a voice that wasn't the cave's. You fled with nothing but scars.",
  ],
  deepPatrol: [
    'You walk the deep dark end to end, holding the line, prying loose what shards the stone still hides.',
    'No new ground down here — only the old ground held, and the Rot leaning on the door.',
  ],
  wardBreak: [
    'The last of the salt line goes gray and scatters. For the first time, there is nothing at the sill but dark.',
    'The iron rusts through in a night. The ward is down, and the hollow knows it.',
  ],
  hollowFell: [
    "The wards failed. Old Gnaw came up through the well in the night, and the hollow was emptied. What lore you'd gathered, the next child half-remembers.",
  ],
} as const;

export type FlavorKey = keyof typeof FLAVOR;

/** Pick a flavor line for an event using the seeded RNG. */
export function flavor(rng: Rng, key: FlavorKey): string {
  return pick(rng, FLAVOR[key]);
}

/**
 * Old Gnaw's whispers, tiered by how far the Rot has risen. Higher Rot = closer,
 * bolder, less patient. Returns a line to log at high Rot (see Game.maybeWhisper).
 */
export const WHISPERS = {
  low: [
    '"You salt your doors, child. I have all the time under the mountain. Salt runs out."',
  ],
  mid: [
    '"They bound me with borrowed words. Borrowed things get returned."',
    '"Every winter the wards get thinner and the graves get shallower."',
  ],
  high: [
    '"I am very patient. I am the shape patience takes. And you are nearly done being patient with me."',
    '"Lay it in the daytime, then. Lay it twice. I am already inside the walls of the well."',
  ],
} as const;

export function whisperByRot(rng: Rng, rot: number): string {
  const tier = rot >= 85 ? WHISPERS.high : rot >= 70 ? WHISPERS.mid : WHISPERS.low;
  return pick(rng, tier);
}
