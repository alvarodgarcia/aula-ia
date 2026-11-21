(() => {
  const panel = document.querySelector('[data-pronunciation]');
  const form = panel?.querySelector('[data-pronunciation-form]');
  if (!form) return;
  const record = form.querySelector('[data-pronunciation-record]');
  const cancel = form.querySelector('[data-pronunciation-cancel]');
  const status = panel.querySelector('[data-pronunciation-status]');
  const result = panel.querySelector('[data-pronunciation-result]');
  let session;
  const close = current => {
    clearTimeout(current.timer);
    current.stream?.getTracks().forEach(track => track.stop());
    current.context?.close().catch(() => {});
  };
  const reset = () => { record.disabled = false; record.textContent = 'Grabar otra lectura'; cancel.hidden = true; };
  function showResult(data) {
    result.replaceChildren();
    const heading = document.createElement('h3'); heading.textContent = 'Tu lectura, paso a paso'; result.append(heading);
    const metrics = document.createElement('p');
    const value = n => typeof n === 'number' ? `${n} / 100` : 'No disponible';
    metrics.textContent = `Precisión: ${value(data.accuracy)} · Fluidez: ${value(data.fluency)} · Texto completado: ${value(data.completeness)}`;
    result.append(metrics);
    const labels = {Omission:'Palabra omitida', Insertion:'Palabra añadida', Mispronunciation:'Vuelve a practicarla', None:'Registrada'};
    const words = document.createElement('ul'); words.className = 'pronunciation-words';
    for (const word of data.words || []) {
      const li = document.createElement('li');
      li.textContent = `${word.word} · ${value(word.accuracy)} · ${labels[word.error] || 'Registrada'}`;
      if (word.error !== 'None' || word.accuracy !== null && word.accuracy < 70) li.className = 'pronunciation-review';
      if (Array.isArray(word.sounds) && word.sounds.length) {
        const details=document.createElement('details'), summary=document.createElement('summary'), text=document.createElement('p');
        summary.textContent='Sonidos de referencia (Azure)';
        text.textContent=word.sounds.map(sound=>`${sound.name}: ${value(sound.accuracy)}`).join(' · ');
        details.append(summary,text);li.append(details);
      }
      words.append(li);
    }
    result.append(words);
    const advice = document.createElement('p');
    advice.textContent = 'Escucha otra vez el ejemplo y practica una o dos palabras cada vez. La puntuación es orientativa y puede cambiar por el ruido o el micrófono. No es una nota de clase.';
    result.append(advice); result.hidden = false;
  }
  async function encode(blob, current) {
    const Audio = window.AudioContext || window.webkitAudioContext;
    const context = new Audio(); current.context = context;
    const decoded = await context.decodeAudioData(await blob.arrayBuffer());
    if (!Number.isFinite(decoded.duration) || decoded.duration < 0.1 || decoded.duration > 20.05) throw new Error('La grabación debe durar como máximo 20 segundos.');
    const frames = Math.min(320000, Math.ceil(decoded.duration * 16000));
    const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    const offline = new Offline(1, frames, 16000);
    const source = offline.createBufferSource(); source.buffer = decoded; source.connect(offline.destination); source.start();
    const converted = await offline.startRendering();
    const samples = converted.getChannelData(0);
    const bytes = new ArrayBuffer(44 + frames * 2), view = new DataView(bytes);
    const text = (offset, value) => [...value].forEach((c,i) => view.setUint8(offset+i,c.charCodeAt(0)));
    text(0,'RIFF'); view.setUint32(4,36+frames*2,true); text(8,'WAVE'); text(12,'fmt '); view.setUint32(16,16,true);
    view.setUint16(20,1,true); view.setUint16(22,1,true); view.setUint32(24,16000,true); view.setUint32(28,32000,true);
    view.setUint16(32,2,true); view.setUint16(34,16,true); text(36,'data'); view.setUint32(40,frames*2,true);
    samples.forEach((sample,i) => { const n=Math.max(-1,Math.min(1,sample)); view.setInt16(44+i*2,n<0?n*32768:n*32767,true); });
    return new Blob([bytes],{type:'audio/wav'});
  }
  record.addEventListener('click', async () => {
    if (session?.recorder?.state === 'recording') { session.recorder.stop(); close(session); record.disabled = true; return; }
    if (session) return;
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !Audio || !(window.OfflineAudioContext || window.webkitOfflineAudioContext)) {
      status.textContent = 'Este navegador no permite grabar esta práctica. Usa una versión actual con HTTPS y permiso de micrófono.'; return;
    }
    document.getElementById('student-tutor')?.dispatchEvent(new Event('tutor:stop-reading'));
    const current = {canceled:false}; session = current; record.disabled = true; cancel.hidden = false;
    status.textContent = 'Esperando permiso para el micrófono…';
    try {
      current.stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
      if (current.canceled) { close(current); return; }
      const mime = ['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(type => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(current.stream,mime?{mimeType:mime}:{}); current.recorder=recorder;
      const parts=[];
      recorder.ondataavailable = event => { if (event.data.size) parts.push(event.data); };
      recorder.onerror = () => { current.canceled=true; close(current); session=null; reset(); status.textContent='No se pudo grabar. Inténtalo de nuevo.'; };
      recorder.onstop = async () => {
        close(current);
        if (current.canceled) return;
        record.disabled=true; cancel.hidden=true; status.textContent='Preparando y evaluando tu lectura…';
        try {
          const wav=await encode(new Blob(parts,{type:recorder.mimeType}),current);
          if (current.canceled) return;
          const body=new FormData(form); body.set('audio',wav,'lectura.wav');
          current.abort=new AbortController();
          const response=await fetch('/mis-tareas/ingles/pronunciacion/evaluar',{method:'POST',body,signal:current.abort.signal});
          const data=await response.json().catch(()=>({}));
          if (!response.ok || !data.result) throw new Error(data.error || 'No se pudo evaluar. No se reintentará automáticamente.');
          showResult(data.result); status.textContent='Lectura evaluada y guardada. Escucha el ejemplo antes de repetir.';
        } catch(error) { if (!current.canceled) status.textContent=error.message; }
        finally { close(current); if (session===current) session=null; reset(); }
      };
      recorder.start(); record.disabled=false; record.textContent='Terminar y evaluar'; status.textContent='Leyendo… máximo 20 segundos. Pulsa Terminar cuando acabes.';
      // Stop a little early to allow container/encoder padding without exceeding the server cap.
      current.timer=setTimeout(()=>{ if(recorder.state==='recording') { recorder.stop(); close(current); record.disabled=true; } },19500);
    } catch(error) { close(current); session=null; reset(); status.textContent='No se pudo abrir el micrófono. Revisa los permisos.'; }
  });
  function stop() {
    if(!session)return;
    const current=session; current.canceled=true; current.abort?.abort();
    if(current.recorder?.state==='recording')current.recorder.stop();
    close(current); session=null; reset(); status.textContent='Grabación cancelada.';
  }
  cancel.addEventListener('click',stop);
  window.addEventListener('pagehide',stop);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
})();
