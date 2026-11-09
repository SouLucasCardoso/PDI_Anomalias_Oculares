// Regressao do formulario real com DOM/transporte simulados; nao e teste visual.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {Blob} from 'node:buffer';

const source=await readFile(new URL('./app_celular/web/app.js',import.meta.url),'utf8');
const html=await readFile(new URL('./app_celular/web/index.html',import.meta.url),'utf8');
const ids=new Map([...html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"/g)].map(x=>[x[2],x[1]]));
const elements=new Map(),requests=[],gallery=[];
const context={fillRect(){},drawImage(){},beginPath(){},rect(){},fill(){},strokeRect(){},moveTo(){},lineTo(){},stroke(){}};
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this._value='';this.hidden=false;this.disabled=false;this.checked=false;this.dataset={};this.classList={toggle(){},add(){},remove(){}};}
  get value(){return this._value;}
  set value(value){this._value=String(value);}
  addEventListener(type,handler){this.listeners[type]=handler;}
  setAttribute(){}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;if(this.tag==='select')this._value=children[0]?.value||'';}
  focus(){}
  scrollIntoView(){}
  getContext(){return context;}
  querySelector(){return new Element('button');}
}
function element(id){assert.ok(ids.has(id),'ID ausente no HTML: '+id);if(!elements.has(id))elements.set(id,new Element(ids.get(id)));return elements.get(id);}
class Option {constructor(text,value){this.textContent=text;this.value=value;}}
let nextId=0,sandbox;
const run=code=>vm.runInContext(code,sandbox);
sandbox=vm.createContext({
  document:{getElementById:element,querySelectorAll:()=>[],createElement:tag=>new Element(tag)},
  localStorage:{getItem:()=>'',setItem(){},removeItem(){}},
  location:{hostname:'test.local',hash:''},window:{scrollTo(){}},
  URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},URLSearchParams,Blob,Option,
  setTimeout:()=>0,clearTimeout(){},prompt:()=>null,
  createImageBitmap:async()=>({width:1600,height:1200,close(){}}),
  fetch:async(path,options={})=>{
    if(path.startsWith('/api/assets/'))return {ok:true,blob:async()=>new Blob(['test'])};
    if(path==='/api/gallery')return {ok:true,json:async()=>gallery.map(x=>({...x}))};
    if(path==='/api/enroll'){
      const body=JSON.parse(options.body);requests.push(body);
      let person=gallery.find(x=>x.id===body.person_id);
      if(!person){person={id:'person-'+(++nextId),name:body.name,side:run('current.side'),samples:0};gallery.push(person);}
      person.samples++;
      return {ok:true,json:async()=>({person_id:person.id,name:person.name})};
    }
    throw new Error('Requisicao inesperada no teste: '+path);
  }
});
new vm.Script(source);
run(source.replace(/\ninit\(\);\s*$/,'\n'));
function capture(id,side='R'){
  run('current='+JSON.stringify({id,side,mode:'enroll',warnings:[],quality:{iris_width_px:150},elapsed_seconds:1}));
  return run('renderResult(current)');
}
function submit(){return element('enroll-form').listeners.submit({preventDefault(){}});}
export const results=[];

await capture('first');element('person-name').value='Ana';element('reviewed').checked=true;
await submit();
assert.equal(requests[0].name,'Ana');assert.equal(requests[0].person_id,null);
assert.equal(element('person-name').value,'');assert.equal(element('enroll-fields').hidden,true);
results.push('Novo registro envia o nome digitado e limpa o formulario ao salvar');

await run('readPhoto({})');await capture('second');
assert.equal(element('person-name').value,'');assert.equal(element('person-select').value,'');
assert.equal(element('new-name').hidden,false);assert.equal(element('existing-person').hidden,true);
assert.equal(element('person-name').required,true);assert.equal(element('person-select').disabled,true);
await submit();assert.equal(requests.length,1);
element('person-name').value='Bruno';element('reviewed').checked=true;
await Promise.all([submit(),submit()]);
assert.equal(requests.length,2);assert.equal(requests[1].name,'Bruno');assert.equal(requests[1].person_id,null);
assert.equal(gallery.length,2);
results.push('Segunda captura pede nome novo; nao copia Ana nem salva duas vezes');

gallery.push({id:'left-only',name:'Olho esquerdo',side:'L',samples:1});
await run('readPhoto({})');await capture('third');await run('refreshGallery()');
run("setEnrollmentKind('existing')");element('reviewed').checked=true;
await submit();assert.equal(requests.length,2);
assert.ok(!element('person-select').children.some(x=>x.value==='left-only'));
element('person-select').value='person-1';await run('refreshGallery()');
assert.equal(element('person-select').value,'person-1');assert.equal(element('new-name').hidden,true);
await submit();assert.equal(requests[2].person_id,'person-1');assert.equal(requests[2].name,'');
assert.equal(gallery.find(x=>x.id==='person-1').samples,2);
results.push('Adicionar foto exige selecao explicita, filtra o lado e preserva o registro escolhido');

await run('readPhoto({})');await capture('fourth');
assert.equal(run('enrollmentKind'),'new');assert.equal(element('person-name').value,'');
assert.equal(element('person-select').value,'');assert.equal(element('new-name').hidden,false);
assert.equal(element('existing-person').hidden,true);
results.push('Captura seguinte sempre volta a novo registro com nome vazio');

element('person-name').value='Nome antigo';element('person-select').value='person-1';
run('startNewEnrollment()');
assert.equal(run('current'),null);assert.equal(run('photo'),null);
assert.equal(element('person-name').value,'');assert.equal(element('person-select').value,'');
assert.equal(element('empty-capture').hidden,false);assert.equal(element('result-panel').hidden,true);
results.push('Novo registro na Galeria limpa tambem a foto e o resultado anteriores');
