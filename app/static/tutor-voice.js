(() => {
  const tutor = document.querySelector("#student-tutor");
  if (!tutor) return;

  const status = tutor.querySelector("#tutor-state");
  const speech = window.speechSynthesis;
  const browserSpeech = speech && typeof window.SpeechSynthesisUtterance === "function";
  const clips = new Map();
  let current;
  const voicesByCharacter = {
    lumo: { names: /elvira|dalia|paulina|sabrina/, pitch: 1.04, pace: 1.02 },
    nora: { names: /helena|monica|laura|paloma/, pitch: 1.00, pace: 0.96 },
    samir: { names: /alvaro|pablo|jorge|raul|juan/, pitch: 0.98, pace: 1.0 },
  };

  function setState(state, message = "") {
    tutor.dataset.state = state;
    status.textContent = message;
  }

  function resetReading(message = "") {
    if (!current) return;
    const playback = current;
    current = undefined;
    if (playback.button) playback.button.textContent = playback.label;
    playback.stop?.();
    setState("idle", message);
    playback.done?.(message);
  }

  function stopReading() {
    resetReading();
  }

  function preference(key, value) {
    const storageKey = `aula-ia:tutor:${tutor.dataset.profile}:${key}`;
    try {
      if (value === undefined) return localStorage.getItem(storageKey);
      localStorage.setItem(storageKey, value);
    } catch {
      // The controls still work for this page when storage is disabled.
    }
  }

  const characters = Array.from(tutor.querySelectorAll('input[name="tutor-character"]'));
  const portrait = tutor.querySelector("#tutor-portrait");
  const name = tutor.querySelector("#tutor-name");
  const selectedCharacter = tutor.querySelector("#tutor-selected-character");
  const question = tutor.querySelector("#tutor-question");
  const greeting = tutor.querySelector('[data-tutor-read="tutor-greeting-text"]');
  const greetingText = tutor.querySelector("#tutor-greeting-text");
  let saveQueue = Promise.resolve();

  function saveCharacter(character) {
    preference("character", character);
    saveQueue = saveQueue.then(async () => {
      const response = await fetch("/tutor/personaje", {
        method: "POST", keepalive: true,
        body: new URLSearchParams({ character, csrf_token: question.elements.csrf_token.value }),
      });
      if (!response.ok) throw new Error("No se pudo guardar el personaje");
    }).catch(() => {
      if (!current) setState("idle", "No se pudo guardar el personaje en el perfil.");
    });
  }

  function showCharacter(selected) {
    selected.checked = true;
    portrait.src = `/static/tutor-${selected.value}.webp`;
    name.textContent = selected.dataset.name;
    selectedCharacter.value = selected.value;
    greetingText.textContent = selected.dataset.greeting;
    greeting.dataset.tutorSignature = selected.dataset.signature;
    greeting.closest("[data-tutor-voice-control]").hidden = !browserSpeech && !selected.dataset.signature;
  }
  const profileChoice = tutor.dataset.savedCharacter;
  const storedCharacter = profileChoice || preference("character");
  const savedCharacter = characters.find(option => option.value === storedCharacter);
  if (savedCharacter) {
    showCharacter(savedCharacter);
    if (!profileChoice) saveCharacter(savedCharacter.value);
  }
  characters.forEach(character => {
    character.addEventListener("change", () => {
      stopReading();
      showCharacter(character);
      saveCharacter(character.value);
      if (tutor.dataset.conversation !== "on" && !greeting.closest("[data-tutor-voice-control]").hidden) greeting.click();
    });
  });

  const motion = tutor.querySelector("#tutor-reduce-motion");
  function applyMotion() {
    tutor.classList.toggle("tutor-motion-reduced", motion.checked);
  }
  motion.checked = preference("reduce-motion") === "true";
  applyMotion();
  motion.addEventListener("change", () => {
    applyMotion();
    preference("reduce-motion", String(motion.checked));
  });
  tutor.querySelector("#tutor-preferences").hidden = false;

  question.addEventListener("submit", event => {
    if (tutor.dataset.state === "thinking") {
      event.preventDefault();
      return;
    }
    stopReading();
    setState("thinking", "Pensando…");
  });

  window.addEventListener("pagehide", stopReading);
  window.addEventListener("pageshow", event => {
    if (event.persisted) setState("idle");
  });
  const panel = tutor.querySelector("details");
  if (location.hash === "#student-tutor") panel.open = true;
  document.querySelectorAll("[data-open-student-tutor]").forEach(link => {
    link.addEventListener("click", event => {
      event.preventDefault();
      panel.open = true;
      tutor.scrollIntoView({ block: "start" });
      panel.querySelector("summary").focus({ preventScroll: true });
    });
  });
  panel.addEventListener("toggle", () => {
    if (!panel.open) stopReading();
  });

  if (browserSpeech) speech.getVoices();

  function spokenText(text, locale) {
    const operations = locale === "es-ES" ? { "+": "más", "-": "menos", "−": "menos", "×": "por", "*": "por", "÷": "entre", "=": "es igual a" } : { "+": "plus", "-": "minus", "−": "minus", "×": "times", "*": "times", "÷": "divided by", "=": "equals" };
    return text
      .replace(/^[ \t]*(?:[-*] |#{1,6} )/gm, "")
      .replace(/\*\*|__|`/g, "")
      .replace(/(\d)\s*([+−×*÷=\-])\s*(?=[\d(])/g, (_, number, operator) => `${number} ${operations[operator]} `)
      .replace(/(\d)\s*%/g, locale === "es-ES" ? "$1 por ciento" : "$1 percent");
  }

  function chooseVoice(style, locale) {
    const peninsular = speech.getVoices().filter(voice => voice.lang.replace("_", "-").toLowerCase() === locale.toLowerCase());
    const score = voice => {
      const name = voice.name.toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
      return (voice.lang.toLowerCase() === "es-es" ? 7 : 0)
        + (style.names.test(name) ? 3 : 0)
        + (/natural|neural|premium|enhanced/.test(name) ? 8 : 0)
        + (voice.localService ? 2 : 0);
    };
    return peninsular.sort((left, right) => score(right) - score(left))[0];
  }

  function playBrowser(playback, text, character) {
    if (!browserSpeech) {
      resetReading("No se ha podido reproducir la voz.");
      return;
    }
    const style = voicesByCharacter[character] ?? voicesByCharacter.nora;
    const locale = playback.locale || tutor.dataset.locale || "es-ES";
    const utterance = new SpeechSynthesisUtterance(spokenText(text, locale));
    const voice = chooseVoice(style, locale);
    if (!voice) {
      tutor.dataset.voiceSource = `unavailable-${locale}`;
      resetReading(locale === "es-ES" ? "Este dispositivo no tiene una voz de España disponible. Puedes leer el texto o instalar una voz es-ES." : `Este dispositivo no tiene una voz ${locale} disponible. Puedes leer el texto o instalar una voz de ese idioma.`);
      return;
    }
    tutor.dataset.voiceSource = `browser-${locale}`;
    utterance.lang = locale;
    utterance.voice = voice;
    utterance.pitch = style.pitch;
    utterance.rate = Number(tutor.dataset.rate) * style.pace;
    playback.stop = () => speech.cancel();
    utterance.onstart = () => {
      if (current === playback) setState("speaking", `Voz del dispositivo · ${locale}.`);
    };
    utterance.onend = () => {
      if (current === playback) resetReading();
    };
    utterance.onerror = () => {
      if (current === playback) resetReading(
        playback.button === greeting ? "Pulsa «Escuchar saludo» para oírlo." : "Pulsa Escuchar al tutor para iniciar el audio.",
      );
    };
    speech.speak(utterance);
  }

  async function playNeural(playback, text, character, signature) {
    const locale = playback.locale || tutor.dataset.locale || "es-ES";
    const key = `${locale}:${character}:${signature}`;
    let clip = clips.get(key);
    if (!clip) {
      const controller = new AbortController();
      playback.stop = () => controller.abort();
      const response = await fetch("/tutor/voz", {
        method: "POST", signal: controller.signal,
        body: new URLSearchParams({ text, character, signature, locale, csrf_token: question.elements.csrf_token.value }),
      });
      if (!response.ok || !response.headers.get("content-type")?.startsWith("audio/")) {
        throw new Error("Proveedor de voz no disponible");
      }
      clip = { data: await response.blob(), provider: response.headers.get("X-Aula-Voice-Provider") === "azure" ? "azure" : "openai" };
      if (current !== playback) return;
      if (!playback.audioContext) clips.set(key, clip);
    }
    const providerLabel = clip.provider === "azure" ? `Azure Speech · ${locale}` : `OpenAI · ${locale}`;
    if (playback.audioContext) {
      const context = playback.audioContext;
      const buffer = await context.decodeAudioData(await clip.data.arrayBuffer());
      if (current !== playback) return;
      if (context.state !== "running") throw new Error("Audio en pausa");
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      source.onended = () => {
        if (current === playback) resetReading();
      };
      playback.stop = () => {
        source.onended = null;
        source.stop();
        source.disconnect();
      };
      source.start();
      tutor.dataset.voiceSource = clip.provider;
      setState("speaking", `Voz generada por IA (${providerLabel}) · el tutor está hablando…`);
      return;
    }
    const url = URL.createObjectURL(clip.data);
    const audio = new Audio(url);
    let started = false;
    playback.stop = () => {
      audio.pause();
      URL.revokeObjectURL(url);
    };
    audio.onplaying = () => {
      started = true;
      if (current === playback) {
        tutor.dataset.voiceSource = clip.provider;
        setState("speaking", `Voz generada por IA (${providerLabel}) · leyendo en voz alta…`);
      }
    };
    audio.onended = () => {
      if (current === playback) resetReading();
    };
    audio.onerror = () => {
      if (started && current === playback) resetReading("No se ha podido reproducir la voz.");
    };
    try {
      await audio.play();
    } catch (error) {
      if (current !== playback) return;
      if (error.name !== "NotAllowedError") throw error;
      resetReading(playback.button === greeting
        ? "Pulsa «Escuchar saludo» para oírlo." : "El audio está listo. Pulsa Escuchar otra vez.");
    }
  }

  tutor.addEventListener("tutor:stop-reading", stopReading);
  tutor.addEventListener("tutor:read-conversation", async event => {
    const { text, signature, character, audioContext, done, locale } = event.detail;
    stopReading();
    const playback = { done, audioContext, locale };
    current = playback;
    setState("idle", "Preparando el audio…");
    if (signature) {
      try {
        await playNeural(playback, text, character, signature);
        return;
      } catch {
        if (current !== playback) return;
        playback.stop?.();
      }
    }
    playBrowser(playback, text, character);
  });

  tutor.querySelectorAll("[data-tutor-read]").forEach(button => {
    if (button !== greeting) {
      if (!button.dataset.tutorSignature && !browserSpeech) return;
      button.closest("[data-tutor-voice-control]").hidden = false;
    }
    button.addEventListener("click", async () => {
      if (tutor.dataset.state === "thinking" || tutor.dataset.conversation === "on") return;
      const alreadyPlaying = current?.button === button;
      stopReading();
      if (alreadyPlaying) return;

      const text = document.getElementById(button.dataset.tutorRead)?.textContent;
      if (!text?.trim()) return;
      const character = selectedCharacter.value;
      const signature = button.dataset.tutorSignature;
      const playback = { button, label: button.textContent.trim(), locale: button.dataset.tutorLocale || tutor.dataset.locale || "es-ES" };
      current = playback;
      button.textContent = "Detener lectura";
      setState("idle", "Preparando el audio…");
      if (signature) {
        try {
          await playNeural(playback, text, character, signature);
          return;
        } catch {
          if (current !== playback) return;
          playback.stop?.();
        }
      }
      playBrowser(playback, text.trim(), character);
    });
  });
  if (tutor.dataset.autoRead === "yes" || tutor.dataset.autoTarget) {
    const target = tutor.dataset.autoTarget || "tutor-reply-text";
    tutor.dataset.autoRead = "no";
    tutor.dataset.autoTarget = "";
    const button = [...tutor.querySelectorAll("[data-tutor-read]")].find(b => b.dataset.tutorRead === target);
    if (button) { button.closest("[data-tutor-voice-control]").hidden = false; button.click(); }
  }
  if (savedCharacter && tutor.dataset.greetOnEntry === "yes" && !greeting.closest("[data-tutor-voice-control]").hidden) {
    greeting.click();
  }
})();
