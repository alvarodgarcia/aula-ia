(() => {
  const board = document.querySelector(".math-board");
  if (!board) return;
  const result = board.querySelector("[data-result]");

  function tiles(container, count, className) {
    const contents = Array.from({ length: count }, () => {
      const tile = document.createElement("span");
      tile.className = className;
      return tile;
    });
    container.replaceChildren(...contents);
  }

  if (board.dataset.kind === "fractions") {
    const fractions = Array.from(board.querySelectorAll("[data-fraction]"));
    function showFractions() {
      const values = fractions.map(fraction => {
        const denominator = fraction.querySelector("[data-denominator]");
        const numerator = fraction.querySelector("[data-numerator]");
        const parts = Math.max(1, Math.min(12, Math.trunc(Number(denominator.value)) || 1));
        const taken = Math.max(0, Math.min(parts, Math.trunc(Number(numerator.value)) || 0));
        denominator.value = parts;
        numerator.max = parts;
        numerator.value = taken;
        const bar = fraction.querySelector("[data-fraction-bar]");
        tiles(bar, parts, "fraction-part");
        Array.from(bar.children).slice(0, taken).forEach(tile => tile.classList.add("is-taken"));
        return [taken, parts];
      });
      const [[a, b], [c, d]] = values;
      result.textContent = `${a}/${b} ${a * d === c * b ? "es igual a" : (a * d > c * b ? "es mayor que" : "es menor que")} ${c}/${d}.`;
    }
    board.addEventListener("change", showFractions);
    showFractions();
    return;
  }

  const initial = Number(board.dataset.start);
  let tens, units;
  const buttons = Array.from(board.querySelectorAll("[data-move]"));
  const allowed = {
    "plus-one": () => units < 30 && (tens * 10 + units) < 200,
    "minus-one": () => units > 0,
    "plus-ten": () => (tens * 10 + units) <= 190,
    "minus-ten": () => tens > 0,
    "group": () => units >= 10,
    "split": () => tens > 0 && units <= 20,
    reset: () => true,
  };
  const moves = {
    "plus-one": () => { units += 1; },
    "minus-one": () => { units -= 1; },
    "plus-ten": () => { tens += 1; },
    "minus-ten": () => { tens -= 1; },
    "group": () => { units -= 10; tens += 1; },
    "split": () => { tens -= 1; units += 10; },
    reset: () => {
      tens = Math.floor(initial / 10);
      units = initial % 10;
    },
  };
  function showBlocks() {
    tiles(board.querySelector("[data-tens]"), tens, "math-ten");
    tiles(board.querySelector("[data-units]"), units, "math-unit");
    result.textContent = `${tens} ${tens === 1 ? "decena" : "decenas"} y ${units} ${units === 1 ? "unidad" : "unidades"}. Total: ${tens * 10 + units}.`;
    buttons.forEach(button => {
      button.disabled = !allowed[button.dataset.move]();
    });
  }
  buttons.forEach(button => {
    button.addEventListener("click", () => {
      moves[button.dataset.move]();
      showBlocks();
    });
  });
  moves.reset();
  showBlocks();
})();
