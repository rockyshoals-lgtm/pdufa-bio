/**
 * The Opening — "The Salt Line" (Story Bible §14). Shown once at the start of a
 * fresh bloodline (Generation 1). A sequence of beats the UI renders as a prologue
 * card; the last beat lands the premise: the salt is not for luck.
 */
export interface PrologueBeat {
  speaker?: string;
  text: string;
}

export const PROLOGUE: readonly PrologueBeat[] = [
  {
    text: 'Low lamplight. Granny\'s hands are folded over yours, tipping the tin.',
  },
  {
    speaker: 'Granny',
    text: "Not too much, now. A finger's width, all the way 'round. Doorsill first, then the sills, then the corners. Corners is where they get in.",
  },
  {
    text: 'You ask her what gets in. She doesn\'t answer. She never answers that. She hums the little rhyme instead — the one that isn\'t quite a hymn and isn\'t quite a song — and waits till you hum it back.',
  },
  {
    speaker: 'Granny',
    text: "Now you never sleep without it laid. Not one night. Not when I'm gone, not when you're grown — not one night in all your life. Promise me on it.",
  },
  {
    text: 'You\'re six years old. You promise. You think it\'s a game.',
  },
  {
    text: 'You learn every rule but the one that matters — the one Granny never says aloud:',
  },
  {
    text: 'The salt is not for luck.',
  },
];
