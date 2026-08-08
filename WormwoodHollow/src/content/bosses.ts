/**
 * The Lords — four pillars of the community twisted by the Rot (Story Bible §9).
 * Each guards a fragment of the binding and dens at a fixed Depth. Descending onto
 * a boss's depth is a resolved boss encounter (harder odds, unique flavor, a
 * guaranteed rune-shard on victory). M3 replaces the resolution with a Phaser fight.
 */
export interface Boss {
  id: string;
  name: string;
  /** Depth level (1..9) this Lord dens at / guards. */
  depth: number;
  /** Who they were, in a breath. */
  epithet: string;
  /** Folk-taunt on encounter. */
  taunt: string;
  /** Line on defeat (rune won). */
  defeat: string;
  /** Line on a failed descent against them. */
  repel: string;
}

export const BOSSES: readonly Boss[] = [
  {
    id: 'ezekiel',
    name: 'Brother Ezekiel',
    depth: 3,
    epithet: 'the Blighted Preacher, who took the black water for baptism',
    taunt: '"Come down to the water, child. The whole congregation\'s waitin\', and none of \'em have left in years."',
    defeat: 'You break the drowned hymn and take the rune-shard from the pulpit stone. The standing dead sit down at last.',
    repel: 'The black-water baptism nearly took you under. You climbed out of the drowned church with your ears full of his sermon.',
  },
  {
    id: 'miller',
    name: 'The Miller',
    depth: 4,
    epithet: 'whose wheel grinds something other than corn now',
    taunt: '"Ever\'body\'s got to eat, and ever\'thing gets ground down. Step up to the stone. Your turn\'s come round."',
    defeat: 'You jam the wheel with iron and pull the shard from the millrace. The grinding stops. The flour goes still and white.',
    repel: 'The wheel caught your coat and near pulled you into the stones. You fled the grist-dark with flour-rot in your lungs.',
  },
  {
    id: 'bledsoe',
    name: 'Granny-Witch Bledsoe',
    depth: 5,
    epithet: 'the eldest ward-keeper, who chose to feed the thing rather than bury her kin',
    taunt: '"I salted these doors sixty year, same as you. Then I got tired, same as you will. Sit. Let Granny fix it."',
    defeat: 'You speak the true rhyme back at her — the one she taught and then forgot — and something lets go of her apron. The shard is cold in her folded hands.',
    repel: 'She wore your grandmother\'s voice and it nearly worked. You ran before the apron-thing finished standing up.',
  },
  {
    id: 'gowrow',
    name: 'The Gowrow',
    depth: 7,
    epithet: 'the folk-cryptid made flesh — the worm\'s largest limb',
    taunt: 'A sound like a barn falling. Twenty feet of tusk and root-slick hide unwinds from the dark, and it knows your name without a mouth to say it.',
    defeat: 'You drive iron behind its foreleg and it recoils down the shaft, shrieking. The rune-shard is lodged in the meat of its den like a tooth.',
    repel: 'It took the whole passage and most of your lamp-oil. You crawled out over your own dropped supplies, alive by inches.',
  },
];

export function bossAtDepth(depth: number): Boss | undefined {
  return BOSSES.find((b) => b.depth === depth);
}

export function bossById(id: string): Boss | undefined {
  return BOSSES.find((b) => b.id === id);
}
