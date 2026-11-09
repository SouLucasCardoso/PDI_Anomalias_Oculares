'use strict';
const $ = id => document.getElementById(id);
let token = localStorage.getItem('iris-device') || '', mode = 'enroll', photo = null, crop = null;
let current = null, busy = false, people = [], drag = null, pollTimer = null, started = 0, view = null;
let enrollmentKind = 'new', savingEnrollment = false;
const blobs = new Map();
function show(id, yes=true) { $(id).hidden = !yes; }
function toast(message) { $('toast').textContent = message; show('toast'); setTimeout(()=>show('toast',false),6500); }
async function api(path, options={}) {
  const headers = {...(token ? {Authorization:'Bearer '+token} : {}), ...options.headers};
  let body = options.body;
  if (body && !(body instanceof Blob)) { body = JSON.stringify(body); headers['Content-Type']='application/json'; }
  const response = await fetch(path,{...options,headers,body});
  const value = await response.json();
  if (!response.ok) { if(response.status===401) { token=''; localStorage.removeItem('iris-device'); show('pair-panel'); show('app-panel',false); } throw new Error(value.error || 'Não foi possível concluir'); }
  return value;
}
async function asset(key, filename, element) {
  const response = await fetch(`/api/assets/${key}/${filename}`,{headers:{Authorization:'Bearer '+token}});
  if(!response.ok) throw new Error('Não foi possível carregar o recorte');
  if(blobs.has(element)) URL.revokeObjectURL(blobs.get(element));
  const url=URL.createObjectURL(await response.blob()); blobs.set(element,url); $(element).src=url;
}
function node(tag,text,className) { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(className)e.className=className; return e; }
function setEnrollmentKind(kind) {
  enrollmentKind=kind;
  const isNew=kind==='new',saved=Boolean(current&&current.already_enrolled);
  for(const key of ['new','existing']) { $('enroll-'+key).classList.toggle('selected',key===kind);$('enroll-'+key).setAttribute('aria-pressed',String(key===kind)); }
  show('new-name',isNew);show('existing-person',!isNew);
  $('person-name').disabled=!isNew||saved;$('person-name').required=isNew&&!saved;
  $('person-select').disabled=isNew||saved;$('person-select').required=!isNew&&!saved;$('reviewed').disabled=saved;
  $('save-enrollment').textContent=isNew?'Salvar novo registro':'Adicionar foto ao registro';
  $('save-enrollment').disabled=savingEnrollment||Boolean(current&&current.already_enrolled);
  show('enroll-fields',!Boolean(current&&current.already_enrolled));show('next-enrollment',Boolean(current&&current.already_enrolled));
  $('enroll-hint').textContent=isNew?'Dê um nome ao novo olho cadastrado. Para mais fotos do mesmo olho, escolha Adicionar foto.':'Selecione o registro ao qual esta foto pertence. Só aparecem cadastros do mesmo lado do olho.';
}
function resetEnrollment() {
  $('person-name').value='';$('person-select').value='';$('reviewed').checked=false;$('enroll-message').textContent='';
  setEnrollmentKind('new');
}
function refreshEnrollmentOptions() {
  const previous=$('person-select').value;
  const side=current ? current.side : $('eye-side').value;
  const compatible=people.filter(x=>x.side===side);
  $('person-select').replaceChildren(new Option('Escolha um registro existente',''),...compatible.map(x=>new Option(`${x.name} · ${x.side==='R'?'direito':'esquerdo'} · ${x.samples} foto(s)`,x.id)));
  $('person-select').value=compatible.some(x=>x.id===previous)?previous:'';
  setEnrollmentKind(enrollmentKind);
}
function startNewEnrollment() {
  if(busy||savingEnrollment){toast('Aguarde a análise ou o salvamento atual.');return;}
  setMode('enroll');current=null;localStorage.removeItem('iris-last-job');
  if(photo&&photo.close)photo.close();photo=null;crop=null;view=null;
  resetEnrollment();show('result-panel',false);show('crop-panel',false);show('analyze-button',false);show('empty-capture');navigate('capture');
}
function setMode(value) {
  mode=value;
  for(const key of ['enroll','recognize']) { $('mode-'+key).classList.toggle('selected',key===value); $('mode-'+key).setAttribute('aria-pressed',String(key===value)); }
}
function navigate(page) {
  for(const p of ['capture','gallery','trials']) show(p+'-page',p===page);
  document.querySelectorAll('[data-page]').forEach(e=>e.classList.toggle('active',e.dataset.page===page));
  if(page==='gallery') refreshGallery().catch(e=>toast(e.message));
  if(page==='trials') refreshTrials().catch(e=>toast(e.message));
  window.scrollTo({top:0,behavior:'smooth'});
}
async function connect() {
  $('pair-error').textContent=''; $('pair-button').disabled=true;
  try { const data=await api('/api/pair',{method:'POST',body:{code:$('pair-code').value.trim()}}); token=data.token;localStorage.setItem('iris-device',token); await activate(); }
  catch(e) { $('pair-error').textContent=e.message; }
  finally { $('pair-button').disabled=false; }
}
async function activate() {
  await refreshGallery(); show('app-panel'); show('pair-panel',false); $('connection').textContent='PC conectado · local'; $('connection').classList.remove('off');
  const key=localStorage.getItem('iris-last-job'); if(key&&!current&&!busy) poll(key);
}
async function readPhoto(file) {
  if(!file)return; if(busy||savingEnrollment){toast('Aguarde a análise ou o salvamento atual.');return;}
  try {
    if(photo&&photo.close)photo.close();
    photo=await createImageBitmap(file,{imageOrientation:'from-image'});
    const w=photo.width,h=photo.height;
    const cw=Math.min(w*.92,h*1.3*.92),ch=cw/1.3;
    crop={x:(w-cw)/2,y:(h-ch)/2,w:cw,h:ch,base:cw};
    $('zoom').value='1'; show('empty-capture',false); show('crop-panel');show('analyze-button');show('result-panel',false);
    current=null;resetEnrollment();localStorage.removeItem('iris-last-job');drawCrop();
  } catch(e){toast('Não foi possível abrir a foto. Use JPEG ou PNG.');}
}
function drawCrop() {
  if(!photo||!crop)return;
  const canvas=$('crop-canvas');canvas.width=1000;canvas.height=750;
  const scale=Math.min(canvas.width/photo.width,canvas.height/photo.height);
  view={scale,x:(canvas.width-photo.width*scale)/2,y:(canvas.height-photo.height*scale)/2};
  const ctx=canvas.getContext('2d');ctx.fillStyle='#142b30';ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.drawImage(photo,view.x,view.y,photo.width*scale,photo.height*scale);
  const x=view.x+crop.x*scale,y=view.y+crop.y*scale,w=crop.w*scale,h=crop.h*scale;
  ctx.fillStyle='#0a202bb3';ctx.beginPath();ctx.rect(0,0,canvas.width,canvas.height);ctx.rect(x,y,w,h);ctx.fill('evenodd');
  ctx.strokeStyle='#83e4c3';ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);
  ctx.strokeStyle='#ffffff45';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x+w/3,y);ctx.lineTo(x+w/3,y+h);ctx.moveTo(x+2*w/3,y);ctx.lineTo(x+2*w/3,y+h);ctx.moveTo(x,y+h/2);ctx.lineTo(x+w,y+h/2);ctx.stroke();
  $('crop-resolution').textContent=`${Math.round(crop.w)} × ${Math.round(crop.h)} px`;
}
function position(event) { const canvas=$('crop-canvas'),r=canvas.getBoundingClientRect();return {x:((event.clientX-r.left)/r.width*canvas.width-view.x)/view.scale,y:((event.clientY-r.top)/r.height*canvas.height-view.y)/view.scale}; }
function clampCrop() { crop.x=Math.max(0,Math.min(photo.width-crop.w,crop.x));crop.y=Math.max(0,Math.min(photo.height-crop.h,crop.y)); }
$('crop-canvas').addEventListener('pointerdown',e=>{if(!photo||busy)return;const p=position(e);drag={...p,x0:crop.x,y0:crop.y};e.target.setPointerCapture(e.pointerId);});
$('crop-canvas').addEventListener('pointermove',e=>{if(!drag)return;const p=position(e);crop.x=drag.x0+p.x-drag.x;crop.y=drag.y0+p.y-drag.y;clampCrop();drawCrop();});
for(const type of ['pointerup','pointercancel'])$('crop-canvas').addEventListener(type,()=>drag=null);
$('zoom').addEventListener('input',()=>{if(!crop||busy)return;const cx=crop.x+crop.w/2,cy=crop.y+crop.h/2;crop.w=crop.base/Number($('zoom').value);crop.h=crop.w/1.3;crop.x=cx-crop.w/2;crop.y=cy-crop.h/2;clampCrop();drawCrop();});
function setBusy(value) {
  busy=value;for(const id of ['analyze-button','camera-button','file-button','mode-enroll','mode-recognize','eye-side','zoom'])$(id).disabled=value;
  show('progress-panel',value);
}
async function analyze() {
  if(!photo||busy||savingEnrollment)return;
  setBusy(true);show('result-panel',false);started=Date.now();$('progress-message').textContent='Enviando somente o recorte';
  try {
    const scale=Math.min(1,2560/Math.max(crop.w,crop.h)),canvas=document.createElement('canvas');
    canvas.width=Math.round(crop.w*scale);canvas.height=Math.round(crop.h*scale);
    canvas.getContext('2d').drawImage(photo,crop.x,crop.y,crop.w,crop.h,0,0,canvas.width,canvas.height);
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.95));
    if(!blob)throw new Error('Não foi possível preparar o recorte');
    const data=await api('/api/analyze',{method:'POST',headers:{'X-Eye-Side':$('eye-side').value,'X-Mode':mode,'Content-Type':'image/jpeg'},body:blob});
    localStorage.setItem('iris-last-job',data.id);poll(data.id);
    $('progress-panel').scrollIntoView({behavior:'smooth',block:'center'});
  } catch(e){setBusy(false);toast(e.message);}
}
async function poll(key) {
  clearTimeout(pollTimer);setBusy(true);if(!started)started=Date.now();
  try {
    const job=await api('/api/jobs/'+key);$('progress-message').textContent=job.message;
    $('progress-time').textContent=`${Math.floor((Date.now()-started)/1000)} s nesta página · a primeira foto também carrega os modelos.`;
    if(job.status==='done'){setBusy(false);current=job.result;await renderResult(current);return;}
    if(job.status==='error'){setBusy(false);localStorage.removeItem('iris-last-job');throw new Error(job.message);}
    pollTimer=setTimeout(()=>poll(key),1200);
  } catch(e){setBusy(false);toast(e.message);}
}
async function renderResult(result) {
  await Promise.all([asset(result.id,'overlay.jpg','overlay-image'),asset(result.id,'polar.png','polar-image')]);
  $('quality').replaceChildren();
  for(const [value,label] of [[result.quality.iris_width_px+' px','largura prevista da íris'],[Math.round(result.elapsed_seconds)+' s','processamento da foto']]) {const d=node('div');d.append(node('strong',value),node('span',label));$('quality').append(d);}
  $('warnings').replaceChildren(...result.warnings.map(t=>node('p',t,'warning')));
  show('enroll-form',result.mode==='enroll');show('match-panel',result.mode==='recognize');resetEnrollment();refreshEnrollmentOptions();$('trial-message').textContent='';
  $('trial-form').querySelector('button').disabled=false;
  if(result.already_enrolled){$('save-enrollment').disabled=true;$('enroll-message').textContent='Esta foto já está salva no cadastro.';}
  if(result.mode==='recognize') {
    const matching=result.matching;$('ranking').replaceChildren();
    $('match-explanation').textContent=matching.duplicate_image?'Esta é a mesma imagem já cadastrada. Faça outra foto para um teste independente.':!matching.candidate_count?'Ainda não há cadastro compatível para este lado do olho. Cadastre primeiro e use uma nova foto.':`${matching.candidate_count} pessoa(s) comparada(s) para o olho ${result.side==='R'?'direito':'esquerdo'}. A ordem abaixo indica semelhança, sem confirmar identidade.`;
    for(const [index,entry] of matching.ranking.entries()) {const row=node('div',undefined,'rank-row'),name=node('div',undefined,'rank-name');name.append(node('strong',entry.name),node('small',`${entry.samples} foto(s) de cadastro`));row.append(node('span',String(index+1).padStart(2,'0'),'rank-index'),name,node('span',entry.score.toFixed(3),'rank-score'));$('ranking').append(row);}
    $('expected-person').replaceChildren(new Option('Selecione após conferir o resultado',''),...matching.ranking.map(x=>new Option(x.name,x.person_id)),new Option('Pessoa não cadastrada','unknown'));
    show('trial-form',matching.candidate_count>0&&!matching.duplicate_image);
  }
  show('result-panel');$('result-panel').scrollIntoView({behavior:'smooth',block:'start'});
}
async function refreshGallery() {
  people=await api('/api/gallery');
  const unique=[...new Map(people.map(x=>[x.id,x])).values()];
  refreshEnrollmentOptions();
  $('gallery-list').replaceChildren();
  if(!unique.length)$('gallery-list').append(node('div','Seu cadastro está vazio. Comece com três fotos independentes de um olho.','empty-list'));
  for(const person of unique) {
    const card=node('div',undefined,'card person-card');card.append(node('div',person.name.slice(0,1).toUpperCase(),'initial'),node('h3',person.name));
    card.append(node('p',people.filter(x=>x.id===person.id).map(x=>`${x.side==='R'?'Direito':'Esquerdo'} · ${x.samples} foto(s)`).join(' / ')));
    const rename=node('button','Renomear registro','text-button');rename.addEventListener('click',async()=>{
      const name=prompt('Novo nome deste registro:',person.name);
      if(name===null)return;
      try{await api('/api/rename-person',{method:'POST',body:{person_id:person.id,name}});await refreshGallery();toast('Nome atualizado. Fotos e testes preservados.');}catch(e){toast(e.message);}
    });card.append(rename);
    const remove=node('button','Excluir pessoa e fotos','text-button');remove.addEventListener('click',async()=>{
      if(!confirm('Excluir esta pessoa, as fotos dela e todos os registros de testes?'))return;
      try{await api('/api/delete-person',{method:'POST',body:{person_id:person.id}});current=null;localStorage.removeItem('iris-last-job');show('result-panel',false);await refreshGallery();toast('Pessoa e registros removidos.');}catch(e){toast(e.message);}
    });card.append(remove);$('gallery-list').append(card);
  }
}
async function refreshTrials() {
  const trials=await api('/api/trials'),known=trials.filter(x=>x.top1_correct!==null),correct=known.filter(x=>x.top1_correct===1).length;
  $('trial-summary').textContent=`${trials.length} teste(s) registrado(s). Em ${known.length} foto(s) de pessoas cadastradas, o primeiro candidato coincidiu com o informado em ${correct}. Resultados descritivos, sem estimativa de acurácia geral.`;
  $('trial-list').replaceChildren();
  for(const trial of trials) {const row=node('div',undefined,'trial-entry');row.append(node('span',trial.top1_correct===null?'Pessoa não cadastrada · sem decisão binária':trial.top1_correct?'Primeiro candidato correspondeu':'Primeiro candidato não correspondeu'),node('small',new Date(trial.created*1000).toLocaleString('pt-BR')));$('trial-list').append(row);}
}
$('enroll-form').addEventListener('submit',async e=>{
  e.preventDefault();if(!current||savingEnrollment||current.already_enrolled)return;
  const isNew=enrollmentKind==='new',name=$('person-name').value.trim(),personId=isNew?null:$('person-select').value;
  if(isNew&&!name){toast('Dê um nome a este novo registro.');$('person-name').focus();return;}
  if(!isNew&&!personId){toast('Escolha o registro que receberá esta foto.');return;}
  if(!$('reviewed').checked){toast('Confira a região verde antes de salvar.');return;}
  savingEnrollment=true;$('save-enrollment').disabled=true;
  try{
    const saved=await api('/api/enroll',{method:'POST',body:{capture:current.id,name:isNew?name:'',person_id:personId,reviewed:true}});
    current.already_enrolled=true;resetEnrollment();
    $('enroll-message').textContent=`Foto salva em “${saved.name||name}”. Uma nova captura começará com nome vazio; para o mesmo olho, escolha Adicionar foto.`;
    await refreshGallery();
  }catch(error){toast(error.message);}
  finally{savingEnrollment=false;setEnrollmentKind(enrollmentKind);}
});
$('trial-form').addEventListener('submit',async e=>{e.preventDefault();if(!current)return;try{await api('/api/trials',{method:'POST',body:{capture:current.id,expected:$('expected-person').value}});$('trial-message').textContent='Teste registrado.';$('trial-form').querySelector('button').disabled=true;}catch(error){toast(error.message);}});
$('discard-button').addEventListener('click',async()=>{if(!current||savingEnrollment)return;try{await api('/api/discard',{method:'POST',body:{capture:current.id}});current=null;localStorage.removeItem('iris-last-job');show('result-panel',false);toast('Captura descartada.');}catch(e){toast(e.message);}});
$('enroll-new').onclick=()=>setEnrollmentKind('new');$('enroll-existing').onclick=()=>setEnrollmentKind('existing');
$('mode-enroll').onclick=()=>setMode('enroll');$('mode-recognize').onclick=()=>setMode('recognize');
$('camera-button').onclick=()=>$('camera-file').click();$('file-button').onclick=()=>$('gallery-file').click();
for(const id of ['camera-file','gallery-file'])$(id).addEventListener('change',e=>{readPhoto(e.target.files[0]);e.target.value='';});
$('analyze-button').onclick=analyze;$('pair-button').onclick=connect;$('pair-code').addEventListener('keydown',e=>{if(e.key==='Enter')connect();});
document.querySelectorAll('[data-page]').forEach(e=>e.onclick=()=>navigate(e.dataset.page));
$('add-person').onclick=startNewEnrollment;
$('next-enrollment').onclick=startNewEnrollment;
$('show-connection').onclick=()=>{show('pair-panel');$('pair-panel').scrollIntoView({behavior:'smooth'});};
async function init() {
  try {
    await api('/api/status');$('connection').textContent=token?'Conferindo conexão':'PC disponível · conectar';
    if(['localhost','127.0.0.1'].includes(location.hostname)) {const info=await api('/api/pairing');$('pc-code').textContent=info.code;$('lan-url').textContent=info.url;$('lan-url').href=info.url;$('qr').src='/api/qr.svg';show('pc-pairing');$('pair-code').value=info.code;if(info.transport==='usb')$('lan-state').textContent='Modo USB. Com o cabo e o encaminhamento ativos, abra este endereço no S23. Internet e Wi-Fi não são necessários.';else if(!info.lan_enabled)$('lan-state').textContent='Modo de teste no PC. O acesso pelo Wi-Fi ainda não foi habilitado.';}
    const fragment=new URLSearchParams(location.hash.slice(1)),code=fragment.get('pair');
    if(code){history.replaceState(null,'',location.pathname);$('pair-code').value=code;await connect();}
    else if(token)await activate();else show('pair-panel');
  } catch(e){$('connection').textContent='PC indisponível';$('connection').classList.add('off');show('pair-panel');toast(e.message);}
}
init();
