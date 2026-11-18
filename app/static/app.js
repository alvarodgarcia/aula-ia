const COURSE_MAP = {
  "Infantil": {"Segundo ciclo": ["3 años", "4 años", "5 años"]},
  "Primaria": {"1.º ciclo": ["1.º", "2.º"], "2.º ciclo": ["3.º", "4.º"], "3.º ciclo": ["5.º", "6.º"]},
  "ESO": {"1.º ciclo": ["1.º", "2.º", "3.º"], "2.º ciclo": ["4.º"]},
  "Bachillerato": {"Bachillerato": ["1.º", "2.º"]}
};
function fillSelect(select, values) {
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}
function connectCourseSelectors(prefix) {
  const stage = document.getElementById(prefix + "-stage");
  const cycle = document.getElementById(prefix + "-cycle");
  const course = document.getElementById(prefix + "-course");
  if (!stage || !cycle || !course) return;
  const updateCourses = () => fillSelect(course, (COURSE_MAP[stage.value] || {})[cycle.value] || []);
  const updateCycles = () => {
    fillSelect(cycle, Object.keys(COURSE_MAP[stage.value] || {}));
    updateCourses();
  };
  stage.addEventListener("change", updateCycles);
  cycle.addEventListener("change", updateCourses);
  updateCycles();
}
function connectMaterialChoices(group) {
  if (!("FormDataEvent" in window)) return;
  const form = group.closest("form");
  const inputs = [...group.querySelectorAll('input[type="file"]')];
  const status = group.querySelector("[data-material-selection]");
  const list = group.querySelector("[data-material-queue]");
  const limit = Number(group.dataset.maxFiles);
  const pending = [];
  group.classList.add("material-choices--buttons");

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function renderQueue() {
    list.replaceChildren();
    list.hidden = !pending.length;
    if (!pending.length) showStatus("");
    else showStatus(pending.length === 1 ? "1 archivo listo para subir." : `${pending.length} archivos listos para subir.`);
    pending.forEach((file, index) => {
      const item = document.createElement("li");
      const name = document.createElement("span");
      name.textContent = file.name;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "text-button danger";
      remove.textContent = "Quitar";
      remove.setAttribute("aria-label", `Quitar ${file.name}`);
      remove.addEventListener("click", () => {
        pending.splice(index, 1);
        renderQueue();
        (list.querySelectorAll("button")[Math.min(index, pending.length - 1)] || inputs[0]).focus();
      });
      item.append(name, remove);
      list.append(item);
    });
  }

  for (const input of inputs) {
    input.addEventListener("change", () => {
      const picked = [...input.files];
      if (pending.length + picked.length > limit) {
        showStatus(`El paquete admite hasta ${limit} archivos. Quita alguno o elige menos para añadir.`);
      } else if (picked.length) {
        pending.push(...picked);
        renderQueue();
      }
      input.value = "";
    });
  }

  form.addEventListener("formdata", ({ formData }) => {
    for (const input of inputs) formData.delete(input.name);
    for (const file of pending) formData.append("material_files", file, file.name);
  });

  form.addEventListener("submit", event => {
    if (pending.length) {
      showStatus("Subiendo archivos y leyendo el texto. Esto puede tardar unos minutos.");
      return;
    }
    event.preventDefault();
    showStatus("Haz una foto o elige un archivo antes de continuar.");
    inputs[0].focus();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  connectCourseSelectors("profile");
  document.querySelectorAll("[data-material-choices]").forEach(connectMaterialChoices);
  document.querySelectorAll("[data-voice-preview]").forEach(form => {
    const audio = form.querySelector("[data-voice-preview-audio]");
    const status = form.querySelector("[data-voice-preview-status]");
    let url;
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const character = event.submitter?.value;
      if (!character) return;
      const buttons = [...form.querySelectorAll("button")];
      buttons.forEach(button => { button.disabled = true; });
      audio.pause();
      status.textContent = "Preparando la muestra de voz…";
      try {
        const body = new FormData(form);
        body.set("character", character);
        const response = await fetch(form.action, { method: "POST", body });
        if (!response.ok || !response.headers.get("content-type")?.startsWith("audio/")) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.error || "No se pudo generar la muestra. Revisa la configuración de voz.");
        }
        const clip = await response.blob();
        if (url) URL.revokeObjectURL(url);
        url = URL.createObjectURL(clip);
        audio.src = url;
        audio.hidden = false;
        const label = response.headers.get("X-Aula-Voice-Provider") === "azure" ? "Azure Speech · España" : "OpenAI";
        status.textContent = `Muestra de ${character[0].toUpperCase() + character.slice(1)} · ${label}.`;
        await audio.play().catch(() => { status.textContent += " Pulsa reproducir para escucharla."; });
      } catch (error) {
        status.textContent = error.message;
      } finally {
        buttons.forEach(button => { button.disabled = false; });
      }
    });
    window.addEventListener("pagehide", () => { audio.pause(); if (url) URL.revokeObjectURL(url); });
  });
});
