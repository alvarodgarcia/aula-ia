(() => {
  const tutor = document.querySelector("#student-tutor");
  const controls = tutor?.querySelector("[data-tutor-conversation]");
  if (!controls) return;

  const toggle = controls.querySelector("[data-conversation-toggle]");
  const status = controls.querySelector("[data-conversation-status]");
  const result = controls.querySelector("[data-conversation-result]");
  const transcript = controls.querySelector("[data-conversation-transcript]");
  const reply = controls.querySelector("[data-conversation-reply]");
  const link = controls.querySelector("[data-conversation-link]");
  const question = tutor.querySelector("#tutor-question");
  const AudioEngine = window.AudioContext || window.webkitAudioContext;
  const extensions = { "audio/webm": "webm", "video/webm": "webm", "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/wav": "wav" };
  const maxTurnLength = 90000;
  const idleLimit = 120000;
  let session;

  controls.hidden = false;
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !AudioEngine) {
    toggle.disabled = true;
    status.textContent = window.isSecureContext
      ? "Este navegador no permite conversar con el micrófono. Puedes escribir en el chat."
      : "Abre Aula IA con HTTPS para usar el micrófono.";
    return;
  }

  function stopReading() {
    tutor.dispatchEvent(new Event("tutor:stop-reading"));
  }

  function phase(active, value, message) {
    active.phase = value;
    controls.dataset.phase = value;
    status.textContent = message;
  }

  function discardRecording(active) {
    const recording = active.recording;
    active.recording = undefined;
    if (recording?.recorder.state === "recording") recording.recorder.stop();
  }

  function stop(message = "Conversación por voz finalizada.") {
    const ended = session;
    if (!ended) return;
    session = undefined;
    delete tutor.dataset.conversation;
    phase(ended, "idle", message);
    cancelAnimationFrame(ended.frame);
    ended.request?.abort();
    discardRecording(ended);
    ended.stream?.getTracks().forEach(track => track.stop());
    stopReading();
    ended.context?.close().catch(() => {});
    toggle.textContent = "Conversar por voz";
  }

  function startRecording(active) {
    const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"]
      .find(type => MediaRecorder.isTypeSupported(type));
    try {
      const recorder = new MediaRecorder(active.stream, { ...(mimeType && { mimeType }), audioBitsPerSecond: 48000 });
      const recording = { recorder, chunks: [], submit: false };
      active.recording = recording;
      recorder.ondataavailable = event => {
        if (event.data.size) recording.chunks.push(event.data);
      };
      recorder.onerror = () => {
        if (session === active && active.recording === recording) stop("Se interrumpió la grabación. Vuelve a abrir el micrófono.");
      };
      recorder.onstop = () => {
        if (session !== active || active.recording !== recording) return;
        active.recording = undefined;
        if (!recording.submit) return;
        const type = recorder.mimeType || recording.chunks[0]?.type || "";
        const extension = extensions[type.split(";")[0]];
        if (!recording.chunks.length || !extension) {
          stop("El navegador no pudo guardar el audio. Puedes seguir escribiendo.");
          return;
        }
        submitTurn(active, new Blob(recording.chunks, { type }), extension);
      };
      recorder.start();
      return true;
    } catch {
      stop("No se pudo iniciar la grabación. Puedes volver a intentarlo o escribir.");
      return false;
    }
  }

  function listen(active, message = "Te escucho.") {
    if (session !== active) return;
    discardRecording(active);
    active.listeningAt = performance.now();
    active.speechAt = active.lastVoice = active.aboveSince = null;
    phase(active, "listening", message);
    startRecording(active);
  }

  function finishTurn(active) {
    const recording = active.recording;
    if (recording?.recorder.state !== "recording") return;
    phase(active, "processing", "El tutor está pensando…");
    recording.submit = true;
    recording.recorder.stop();
  }

  function microphoneLevel(active) {
    const samples = active.samples;
    active.analyser.getFloatTimeDomainData(samples);
    let sum = 0;
    let squares = 0;
    for (const sample of samples) {
      sum += sample;
      squares += sample * sample;
    }
    return Math.sqrt(Math.max(0, squares / samples.length - (sum / samples.length) ** 2));
  }

  function detectTurn(active, now) {
    if (active.phase !== "listening" && active.phase !== "replying") return;
    const level = microphoneLevel(active);
    if (active.phase === "replying") {
      const threshold = Math.max(active.echoCancellation ? 0.018 : 0.035, active.noiseFloor * 4);
      if (now - active.replyAt < 300 || level < threshold) {
        if (active.aboveSince !== null) discardRecording(active);
        active.aboveSince = null;
        return;
      }
      if (active.aboveSince === null) {
        active.aboveSince = now;
        if (!startRecording(active)) return;
      }
      if (now - active.aboveSince >= 210) {
        active.listeningAt = active.speechAt = active.aboveSince;
        active.lastVoice = now;
        active.aboveSince = null;
        phase(active, "listening", "Te escucho.");
        stopReading();
      }
      return;
    }

    const onset = Math.max(0.005, active.noiseFloor * 2.4 + 0.0015);
    const sustain = Math.max(0.0035, active.noiseFloor * 1.7 + 0.001);
    if (level >= (active.speechAt === null ? onset : sustain)) {
      active.aboveSince ??= now;
      if (active.speechAt !== null || now - active.aboveSince >= 100) {
        active.speechAt ??= active.aboveSince;
        active.lastVoice = now;
        if (status.textContent !== "Te escucho.") status.textContent = "Te escucho.";
      }
    } else {
      active.aboveSince = null;
      active.noiseFloor = active.noiseFloor * 0.97 + level * 0.03;
    }

    if (active.speechAt !== null) {
      const speakingLength = active.lastVoice - active.speechAt;
      const silence = speakingLength > 3500 ? 1750 : 1250;
      if (now - active.lastVoice >= silence || now - active.speechAt >= maxTurnLength) finishTurn(active);
    } else if (now - active.listeningAt >= idleLimit) {
      stop("El micrófono se ha cerrado por inactividad. Puedes reanudar cuando quieras.");
    }
  }

  function monitor(active) {
    function measure(now) {
      if (session !== active) return;
      detectTurn(active, now);
      if (session === active) active.frame = requestAnimationFrame(measure);
    }
    active.frame = requestAnimationFrame(measure);
  }

  async function submitTurn(active, audio, extension) {
    const body = new FormData();
    const character = question.elements.character.value;
    body.set("audio", audio, `turno.${extension}`);
    body.set("character", character);
    body.set("csrf_token", question.elements.csrf_token.value);
    if (controls.dataset.exerciseId) body.set("exercise_id", controls.dataset.exerciseId);
    const controller = new AbortController();
    active.request = controller;
    try {
      const response = await fetch("/tutor/conversacion", { method: "POST", body, signal: controller.signal });
      const data = await response.json().catch(() => ({}));
      if (session !== active) return;
      if (!response.ok) {
        const message = data.error || "No se pudo entender este turno. Puedes repetirlo.";
        if ([403, 404, 409, 429, 503].includes(response.status)) stop(message);
        else listen(active, message);
        return;
      }

      transcript.textContent = data.transcript + (data.truncated ? " [Texto recortado]" : "");
      reply.textContent = data.reply;
      link.hidden = !data.link;
      if (data.link) {
        link.setAttribute("href", data.link);
        link.textContent = data.link.startsWith("/packs/") ? "Abrir repaso" : "Abrir ejercicio";
      } else {
        link.removeAttribute("href");
      }
      result.hidden = false;
      active.replyAt = performance.now();
      active.aboveSince = null;
      phase(active, "replying", "Puedes interrumpirme hablando.");
      tutor.dispatchEvent(new CustomEvent("tutor:read-conversation", { detail: {
        text: data.reply, signature: data.signature, character, audioContext: active.context,
        done: message => {
          if (session !== active || active.phase !== "replying") return;
          if (active.aboveSince !== null && active.recording) {
            active.listeningAt = active.speechAt = active.aboveSince;
            active.lastVoice = performance.now();
            active.aboveSince = null;
            phase(active, "listening", "Te escucho.");
          } else {
            listen(active, message ? `${message} Puedes leer la respuesta y seguir hablando.` : undefined);
          }
        },
      } }));
    } catch {
      if (session === active) listen(active, "Se interrumpió la conexión. Puedes repetir tu turno.");
    } finally {
      if (active.request === controller) active.request = undefined;
    }
  }

  toggle.addEventListener("click", async () => {
    if (session) {
      stop();
      return;
    }
    const active = { noiseFloor: 0.002, aboveSince: null };
    session = active;
    stopReading();
    tutor.dataset.conversation = "on";
    toggle.textContent = "Finalizar conversación";
    phase(active, "starting", "Esperando permiso para el micrófono…");
    try {
      active.context = new AudioEngine();
      const resumed = active.context.resume().catch(() => {});
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      if (session !== active) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      active.stream = stream;
      const tracks = stream.getAudioTracks();
      active.echoCancellation = tracks[0]?.getSettings?.().echoCancellation === true;
      tracks.forEach(track => track.addEventListener("ended", () => {
        if (session === active) stop("El micrófono se ha desconectado.");
      }));
      await resumed;
      if (session !== active) return;
      if (active.context.state !== "running") {
        stop("El navegador ha pausado el audio. Abre de nuevo la conversación para activarlo.");
        return;
      }
      active.analyser = active.context.createAnalyser();
      active.analyser.fftSize = 1024;
      active.samples = new Float32Array(active.analyser.fftSize);
      const source = active.context.createMediaStreamSource(stream);
      const filter = active.context.createBiquadFilter();
      filter.type = "highpass";
      filter.frequency.value = 125;
      const silent = active.context.createGain();
      silent.gain.value = 0;
      source.connect(filter);
      filter.connect(active.analyser);
      active.analyser.connect(silent);
      silent.connect(active.context.destination);
      listen(active);
      monitor(active);
    } catch (error) {
      if (session !== active) return;
      stop(error.name === "NotAllowedError"
        ? "Permite el uso del micrófono en el navegador o continúa escribiendo."
        : "No se encontró un micrófono disponible. Puedes continuar escribiendo.");
    }
  });

  tutor.querySelector("details").addEventListener("toggle", event => {
    if (!event.target.open) stop();
  });
  question.addEventListener("submit", () => stop());
  window.addEventListener("pagehide", () => stop());
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop("El micrófono se ha cerrado al salir de esta pestaña.");
  });
})();
