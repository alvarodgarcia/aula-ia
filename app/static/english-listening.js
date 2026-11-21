(() => {
  const forms = [...document.querySelectorAll('[data-listening-form]')];
  const tutor = document.getElementById('student-tutor');
  if (!forms.length || !tutor || !window.fetch) return;
  let active = false;
  let controller, speechContext, generation = 0;
  for (const form of forms) form.addEventListener('submit', async event => {
    if (active) { event.preventDefault(); return; }
    event.preventDefault();
    active = true;
    const stamp = ++generation;
    if (tutor.dataset.conversation === 'on') tutor.querySelector('[data-conversation-toggle]')?.click();
    const status = tutor.querySelector('[data-listening-status]');
    status.textContent = 'Preparando la práctica. El tutor hablará en inglés…';
    const buttons = forms.flatMap(f => [...f.querySelectorAll('button')]);
    const body = new FormData(form);
    if (event.submitter?.name) body.set(event.submitter.name, event.submitter.value);
    const context = window.AudioContext || window.webkitAudioContext;
    let audioContext;
    try {
      if (context) { audioContext = new context(); speechContext = audioContext; await audioContext.resume(); }
    } catch { audioContext = undefined; }
    tutor.dispatchEvent(new Event('tutor:stop-reading'));
    buttons.forEach(b => { b.disabled = true; });
    try {
      if (stamp !== generation) { audioContext?.close().catch(() => {}); return; }
      controller = new AbortController();
      const response = await fetch(form.action, {method:'POST', body, headers:{Accept:'application/json'},signal:controller.signal});
      const data = await response.json().catch(() => ({}));
      if (stamp !== generation) return;
      if (!response.ok || !data.reply) throw new Error(data.error || 'No se pudo preparar la práctica. Vuelve a entrar si la sesión ha caducado.');
      const reply = tutor.querySelector('#tutor-reply-text');
      reply.textContent = data.reply;
      reply.lang = data.locale;
      reply.closest('section').hidden = false;
      const details = reply.closest('details');
      if (details) details.open = false;
      const read = tutor.querySelector('[data-tutor-read=tutor-reply-text]');
      read.dataset.tutorSignature = data.signature;
      read.dataset.tutorLocale = data.locale;
      read.closest('[data-tutor-voice-control]').hidden = false;
      const help = tutor.querySelector('[data-english-help]');
      if (help) {
        help.hidden = !data.help;
        help.querySelector('#english-help').textContent = data.help || '';
        help.querySelector('[data-tutor-read]').dataset.tutorSignature = data.help_signature || '';
        help.querySelector('[data-tutor-voice-control]').hidden = !data.help;
      }
      const link = tutor.querySelector('[data-listening-link]');
      link.hidden = !data.link;
      if (typeof data.link === 'string' && /^\/exercise\/\d+$/.test(data.link)) link.href = data.link;
      const counter = document.querySelector(`[data-english-progress="${data.activity}"] b`);
      if (counter) counter.textContent = data.count;
      const question=tutor.querySelector('.tutor-user-question');
      if (question) question.textContent=`Tú: ${body.get('question') || ''}`;
      status.textContent = 'Escucha al tutor. Después puedes responder escribiendo o activar Conversar por voz.';
      const stop=tutor.querySelector('[data-listening-stop]');
      stop.hidden=false;
      stop.onclick=()=>tutor.dispatchEvent(new Event('tutor:stop-reading'));
      tutor.scrollIntoView({block:'start', behavior:'smooth'});
      tutor.dispatchEvent(new CustomEvent('tutor:read-conversation', {detail:{
        text:data.reply, signature:data.signature, locale:data.locale,
        character:tutor.querySelector('[name=character]').value, audioContext,
        done:message => { stop.hidden=true; if (message) status.textContent = message; audioContext?.close().catch(() => {}); },
      }}));
    } catch (error) {
      if (stamp === generation) status.textContent = error.name === 'AbortError' ? 'Práctica interrumpida.' : error.message;
      audioContext?.close().catch(() => {});
    } finally {
      active = false;
      buttons.forEach(b => { b.disabled = false; });
      if (tutor.dataset.state === 'thinking') { tutor.dataset.state = 'idle'; tutor.querySelector('#tutor-state').textContent = ''; }
    }
  });
  const stop = () => { generation++; controller?.abort(); tutor.dispatchEvent(new Event('tutor:stop-reading')); speechContext?.close().catch(() => {}); };
  window.addEventListener('pagehide',stop);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
})();
