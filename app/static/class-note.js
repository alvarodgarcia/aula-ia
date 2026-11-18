(() => {
  const controls = document.querySelector("[data-class-dictation]");
  if (!controls) return;
  const form = controls.closest("form");
  const notes = form.elements.notes;
  const record = controls.querySelector("[data-record-note]");
  const upload = controls.querySelector("[data-upload-note]");
  const input = controls.querySelector("[data-note-audio]");
  const status = controls.querySelector("[data-dictation-status]");
  const canRecord = Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
  const fileTypes = { "audio/webm": "webm", "video/webm": "webm", "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/wav": "wav" };
  let recorder, stream, cutoff;
  let departed = false;

  function releaseMicrophone() {
    clearTimeout(cutoff);
    stream?.getTracks().forEach(track => track.stop());
    stream = undefined;
  }

  function stopRecording() {
    if (recorder?.state === "recording") recorder.stop();
    releaseMicrophone();
  }

  async function transcribe(audio, name) {
    record.disabled = true;
    upload.disabled = true;
    status.textContent = "Transcribiendo la grabación…";
    const data = new FormData();
    data.set("audio", audio, name);
    data.set("csrf_token", form.elements.csrf_token.value);
    try {
      const response = await fetch("/mis-tareas/clase/transcribir", { method: "POST", body: data });
      const message = await response.json();
      if (!response.ok) {
        status.textContent = message.error ?? "No se pudo transcribir la grabación.";
        return;
      }
      const text = [notes.value.trim(), message.text].filter(Boolean).join("\n");
      notes.value = text.slice(0, notes.maxLength);
      status.textContent = message.truncated || text.length > notes.maxLength
        ? "La nota llegó al límite de texto. Revísala antes de guardarla."
        : "Texto listo. Puedes corregirlo antes de guardar la nota.";
      notes.focus();
    } catch {
      status.textContent = "No se pudo transcribir la grabación. Puedes probar otra vez o escribir tu nota.";
    } finally {
      record.disabled = false;
      upload.disabled = false;
    }
  }

  upload.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    const file = input.files[0];
    input.value = "";
    if (file) transcribe(file, file.name);
  });

  record.addEventListener("click", async () => {
    if (recorder?.state === "recording") {
      stopRecording();
      return;
    }
    record.disabled = true;
    upload.disabled = true;
    status.textContent = "Esperando permiso para el micrófono…";
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (departed) {
        releaseMicrophone();
        return;
      }
      const preferred = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"]
        .find(type => MediaRecorder.isTypeSupported(type));
      const active = new MediaRecorder(stream, preferred ? { mimeType: preferred } : undefined);
      recorder = active;
      const chunks = [];
      let recordingError = false;
      active.ondataavailable = event => {
        if (event.data.size) chunks.push(event.data);
      };
      active.onerror = () => {
        recordingError = true;
        stopRecording();
        record.textContent = "Dictar nota";
        record.disabled = upload.disabled = false;
        status.textContent = "La grabación se interrumpió. Puedes intentarlo otra vez.";
      };
      active.onstop = () => {
        if (recorder !== active) return;
        const type = active.mimeType || chunks[0]?.type || "";
        recorder = undefined;
        releaseMicrophone();
        record.textContent = "Dictar nota";
        record.disabled = upload.disabled = false;
        if (departed || recordingError) return;
        const extension = fileTypes[type.split(";")[0]];
        if (!chunks.length || !extension) {
          status.textContent = "No se obtuvo una grabación. Puedes adjuntar un audio o escribir la nota.";
          return;
        }
        transcribe(new Blob(chunks, { type }), `nota.${extension}`);
      };
      active.start();
      record.textContent = "Terminar grabación";
      record.disabled = false;
      status.textContent = "Grabando. Tienes hasta 45 segundos.";
      cutoff = setTimeout(stopRecording, 45000);
    } catch {
      releaseMicrophone();
      record.disabled = upload.disabled = false;
      status.textContent = "El micrófono no está disponible. Puedes adjuntar una grabación o escribir.";
    }
  });

  window.addEventListener("pagehide", () => {
    departed = true;
    stopRecording();
  });
  window.addEventListener("pageshow", () => { departed = false; });
  record.hidden = !canRecord;
  controls.hidden = false;
})();
