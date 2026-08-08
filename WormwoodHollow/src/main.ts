/**
 * Boot. Wires the Game controller to the DOM view and starts the real-time tick.
 * The meta/idle layer is fully playable here without Phaser (Fable Brief §2).
 */
import { CONFIG } from './config';
import { Game } from './core/game';
import { SaveManager } from './save/SaveManager';
import { mount, renderState, bindGame, maybeShowPrologue } from './ui/view';

const game = new Game(new SaveManager());

mount(game); // installs hooks (onChange / onComeMorning) before init fires them
bindGame(game); // lets action buttons dispatch
game.init(); // seed opening line + run offline catch-up
renderState(game.state);
maybeShowPrologue(); // Salt Line opening on a fresh bloodline

const timer = window.setInterval(() => game.tick(), CONFIG.TICK_MS);

window.addEventListener('beforeunload', () => {
  window.clearInterval(timer);
  game.tick(); // stamp lastSeen + final save
});
