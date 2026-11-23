(() => {
  const form=document.querySelector('[data-profile-photo]');
  if(!form)return;
  const file=form.querySelector('[data-photo-file]'), camera=form.querySelector('[data-photo-camera]');
  const button=form.querySelector('[data-photo-camera-button]'), preview=form.querySelector('[data-photo-preview]');
  const status=form.querySelector('[data-photo-status]');
  let url;
  const clear=()=>{if(url)URL.revokeObjectURL(url);url=undefined;preview.hidden=true;preview.removeAttribute('src');};
  function show(){
    clear();const photo=file.files[0];if(!photo)return;status.hidden=false;
    if(photo.size>5*1024*1024){file.value='';status.textContent='Elige una foto de hasta 5 MB.';return;}
    status.textContent='Revisa el encuadre y pulsa Guardar mi foto.';
    url=URL.createObjectURL(photo);preview.src=url;preview.hidden=false;
  }
  button.hidden=false;button.addEventListener('click',()=>camera.click());
  camera.addEventListener('change',()=>{if(camera.files.length){file.files=camera.files;show();}});
  file.addEventListener('change',show);
  preview.addEventListener('error',()=>{preview.hidden=true;status.textContent='Este navegador no muestra la vista previa. Puedes guardar la foto para que el servidor compruebe su formato.';});
  window.addEventListener('pagehide',clear);
})();
