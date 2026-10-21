import {render} from './engine.mjs';
const $=id=>document.getElementById(id),catalog=await (await fetch('catalog.json')).json();
let recording=null,models=[],current=null,reveal=false,phase=true;
const clean=s=>String(s).replace(/[\x00-\x1f\x7f]/g,' ');
for(const r of catalog.recordings)$('recording').add(new Option(r.id,r.id));
async function load(){
 recording=catalog.recordings.find(r=>r.id===$('recording').value);
 models=await (await fetch(`recordings/${recording.path}/pages.json`)).json();
 $('page').replaceChildren();
 for(const key of [...new Set(models.map(p=>p.id))].sort())$('page').add(new Option(key.replace('-',' / '),key));
 $('page').value=models.find(p=>p.number==='100')?.id||models[0].id;
 $('raw').href=`recordings/${recording.path}/${recording.id}.t42`;
 $('notes').href=`recordings/${recording.path}/notes.md`;
 $('metadata').href=`recordings/${recording.path}/metadata.json`;
 versions();
}
function versions(){
 $('version').replaceChildren();
 const candidates=models.filter(p=>p.id===$('page').value);
 for(const p of candidates)$('version').add(new Option(`${p.selected?'Selected · ':''}${p.content_sha256.slice(0,10)} · ${p.crc_status}`,p.content_sha256));
 $('version').value=(candidates.find(p=>p.selected)||candidates[0]).content_sha256;draw();
}
function draw(){
 current=models.find(p=>p.id===$('page').value&&p.content_sha256===$('version').value);
 render($('screen'),current,{reveal,phase});
 $('status').textContent=`P${current.number} / ${current.subpage.toString(16).padStart(4,'0')} · CRC: ${current.crc_status} · ${current.observations} observed transmissions`;
 $('details').textContent=`First: ${clean(current.first_header)} · Last: ${clean(current.last_header)} · Received display rows: ${current.receivedRows.join(', ')}.`;
 $('packet').href=`recordings/${recording.path}/${current.file}`;
 $('png').href=`recordings/${recording.path}/${current.file.replace('.t42','.png')}`;
 $('reveal').setAttribute('aria-pressed',String(reveal));
}
$('recording').onchange=()=>load().catch(e=>$('status').textContent=e.message);
$('page').onchange=versions;$('version').onchange=draw;
function step(direction){const options=[...$('page').options],i=options.findIndex(o=>o.value===$('page').value);$('page').value=options[(i+direction+options.length)%options.length].value;versions();}
$('previous').onclick=()=>step(-1);$('next').onclick=()=>step(1);$('reveal').onclick=()=>{reveal=!reveal;draw()};
setInterval(()=>{phase=!phase;if(current)render($('screen'),current,{reveal,phase})},700);
document.addEventListener('keydown',e=>{if(['SELECT','INPUT'].includes(e.target.tagName))return;if(e.key==='ArrowRight')step(1);if(e.key==='ArrowLeft')step(-1);if(e.key==='?'){reveal=!reveal;draw()}});
$('recording').value=catalog.recordings.at(-1).id;await load();
