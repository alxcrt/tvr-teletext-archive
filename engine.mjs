// A bounded Level 1 cell interpreter. X/26, DRCS and Level 2.5 are not decoded.
import {fonts} from './fonts.mjs';
export const palette=['#000000','#ff0000','#00ff00','#ffff00','#0000ff','#ff00ff','#00ffff','#ffffff'];
const subset={'$':'¤','@':'Ţ','[':'Â','\\':'Ş',']':'Ă','^':'Î','_':'ı','`':'ţ','{':'â','|':'ş','}':'ă','~':'î'};
const reverse=Object.fromEntries(Object.entries(subset).map(([k,v])=>[v,k]));
Object.assign(reverse,{'Ș':'\\','ș':'|','Ț':'@','ț':'`'});
export function encode(text){return [...text].map(c=>{if(c in reverse)return reverse[c];if(c.charCodeAt(0)<32)return c;if(c.charCodeAt(0)<=126&&!(c in subset))return c;throw Error('Caracter nereprezentabil: '+c)}).join('');}
export function decode(c,romanian=true){const s=romanian?(subset[c]||c):c;return s.replaceAll('Ş','Ș').replaceAll('ş','ș').replaceAll('Ţ','Ț').replaceAll('ţ','ț');}
export function interpret(rows,{romanian=true,reveal=false,phase=true}={}){
 return Array.from({length:25},(_,y)=>{
  let fg=7,bg=0,graphics=false,separated=false,flash=false,conceal=false,double=false,hold=false,held=' ';
  return Array.from({length:40},(_,x)=>{
   const c=(rows[y]||'')[x]||' ';const n=c.charCodeAt(0)&127;
   // Set-at attributes affect the control cell itself.
   if(n===0x18)conceal=true;if(n===0x19)separated=false;if(n===0x1a)separated=true;
   if(n===0x1c)bg=0;if(n===0x1d)bg=fg;if(n===0x1e)hold=true;
   const mosaic=graphics&&(n>=0x20&&n<=0x3f||n>=0x60&&n<=0x7f);
   if(mosaic)held=String.fromCharCode(n);
   const glyph=n<32?(hold&&graphics?held:' '):String.fromCharCode(n);
   const cell={char:decode(glyph,romanian),raw:glyph,fg,bg,graphics:graphics&&(n<32?hold:mosaic),separated,double,hidden:(conceal&&!reveal)||(flash&&!phase)};
   // Set-after controls apply to subsequent cells.
   if(n<=7){fg=n;graphics=false;conceal=false;}
   if(n===8)flash=true;if(n===9)flash=false;if(n===12){double=false;held=' ';}if(n===13){double=true;held=' ';}
   if(n>=16&&n<=23){fg=n-16;graphics=true;conceal=false;}
   if(n===31)hold=false;
   return cell;
  });
 });
}
export function parseTTI(text){
 const pages=[];let page=null;
 for(const line of text.split(/\r?\n/)){
  const key=line.slice(0,2),v=line.slice(3);
  if(key==='PN'){
   const m=/^([1-8][0-9]{2})([0-9a-fA-F]{2})?$/.exec(v.trim());if(!m)throw Error('PN invalid: '+v);
   page={number:Number(m[1]),subpage:parseInt(m[2]||'0',16),rows:Array(25).fill(' '.repeat(40)),links:[100,100,100,100],romanian:true,quality:'Import TTI',note:'Import local; funcțiile Level 2.5 și X/26 nu sunt decodate.'};pages.push(page);
  }else if(page&&key==='OL'){
   const split=v.indexOf(',');const row=Number(v.slice(0,split));if(split<0||!Number.isInteger(row)||row<0||row>24)throw Error('Rând TTI neacceptat: '+v.slice(0,10));
   const raw=v.slice(split+1).replace(/\x1b([@-_])/g,(_,c)=>String.fromCharCode(c.charCodeAt(0)-64));
   if(raw.length>40)throw Error('Rândul depășește 40 de celule');page.rows[row]=raw.padEnd(40);
  }else if(page&&key==='FL')page.links=v.split(',').slice(0,4).map(x=>parseInt(x,16)).map(n=>parseInt(n.toString(16),10));
  else if(page&&key==='RE')page.romanian=v.trim()==='3';
  else if(page&&key==='SC'){const n=parseInt(v,16);if(!Number.isFinite(n))throw Error('SC invalid');page.subpage=n;}
 }
 if(!pages.length)throw Error('Fișierul nu conține pagini PN');return pages;
}
export function exportTTI(page){
 if(!Number.isInteger(page.number)||page.number<100||page.number>899)throw Error('Export TTI: pagina trebuie să fie 100–899');
 const sub=(page.subpage||0).toString(16).padStart(4,'0');
 const lines=[`PN,${page.number}${sub.slice(-2)}`,`SC,${sub}`,`PS,${page.romanian===false?'8000':'8380'}`,`RE,${page.romanian===false?'0':'3'}`,'CT,8,T'];
 for(let y=0;y<25;y++){
  const raw=page.rows[y]||'';if(raw.length>40)throw Error('Rând prea lung');
  const encoded=[...raw].map(c=>c.charCodeAt(0)<32?'\x1b'+String.fromCharCode(c.charCodeAt(0)+64):c.charCodeAt(0)<=127?c:encode(c)).join('');
  lines.push(`OL,${y},${encoded}`);
 }
 lines.push('FL,'+(page.links||[100,100,100,100]).concat([100,100]).join(','));return lines.join('\r\n')+'\r\n';
}
export function render(canvas,page,options={}){
 const ctx=canvas.getContext('2d'),cw=18,ch=24;canvas.width=720;canvas.height=600;
 ctx.clearRect(0,0,720,600);if(!options.mix){ctx.fillStyle='#000';ctx.fillRect(0,0,720,600);}ctx.textBaseline='top';ctx.font='bold 23px "Courier New",monospace';
 const cells=interpret(page.rows,{...options,romanian:page.romanian!==false});let lower=new Set();
 for(let y=0;y<25;y++){
  const next=new Set();
  for(let x=0;x<40;x++){
   const c=cells[y][x];if(lower.has(x))continue;
   const h=c.double?ch*2:ch;ctx.fillStyle=palette[c.bg];if(!options.mix||c.bg!==0)ctx.fillRect(x*cw,y*ch,cw,h);
   if(c.double)next.add(x);if(c.hidden)continue;ctx.fillStyle=palette[c.fg];
   if(c.graphics){const n=c.raw.charCodeAt(0),bits=(n&31)|((n&64)>>1);for(let b=0;b<6;b++)if(bits&(1<<b)){const gap=c.separated?2:0;ctx.fillRect(x*cw+(b%2)*9+gap,y*ch+Math.floor(b/2)*h/3+gap,9-gap,h/3-gap);}}
   else{
    const mask=(fonts[page.font]||fonts.saa5050)[c.char]||fonts.saa5050[c.char]||fonts.saa5050['?'];
    const key=(page.font||'saa5050')+'/'+c.char+'/'+c.fg;
    let tile=glyphCache.get(key);
    if(!tile){tile=document.createElement('canvas');tile.width=12;tile.height=20;const t=tile.getContext('2d');t.fillStyle=palette[c.fg];for(let i=0;i<240;i++)if(mask[i]==='1')t.fillRect(i%12,Math.floor(i/12),1,1);glyphCache.set(key,tile);}
    ctx.imageSmoothingEnabled=false;ctx.drawImage(tile,x*cw,y*ch,cw,h);
   }
  }lower=next;
 }
 return cells;
}
const glyphCache=new Map();
