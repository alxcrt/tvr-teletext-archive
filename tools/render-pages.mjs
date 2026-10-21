// Deterministic PNG previews of decoded Level 1 cells. No browser/fonts/network.
import {readFileSync,writeFileSync,readdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {deflateSync} from 'node:zlib';
import {interpret} from '../engine.mjs';
import {fonts} from '../fonts.mjs';
const root=resolve(process.argv[2]),width=480,height=500;
const palette=Array.from({length:8},(_,i)=>[i&1?255:0,i&2?255:0,i&4?255:0,255]);
function crc32(bytes){let c=0xffffffff;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function chunk(name,data){const tag=Buffer.from(name),length=Buffer.alloc(4),crc=Buffer.alloc(4);length.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([tag,data])));return Buffer.concat([length,tag,data,crc]);}
let count=0;
for(const directory of readdirSync(root)){
 const path=resolve(root,directory,'pages.json');let pages;try{pages=JSON.parse(readFileSync(path))}catch{continue}
 for(const page of pages){
  const pixels=Buffer.alloc(width*height*4);for(let i=3;i<pixels.length;i+=4)pixels[i]=255;
  const cells=interpret(page.rows,{romanian:page.romanian!==false,reveal:false,phase:true});let lower=new Set();
  for(let y=0;y<25;y++){
   const next=new Set();
   for(let x=0;x<40;x++){
    if(lower.has(x))continue;const c=cells[y][x],h=c.double?40:20;if(c.double)next.add(x);
    const mask=fonts.saa5050[c.char]||fonts.saa5050['?'];
    for(let py=0;py<h&&y*20+py<height;py++)for(let px=0;px<12;px++){
     let ink=false;
     if(!c.hidden){if(c.graphics){const raw=c.raw.charCodeAt(0),bits=(raw&31)|((raw&64)>>1),col=Math.floor(px/6),row=Math.floor(py*3/h);ink=!!(bits&(1<<(row*2+col)));if(c.separated&&(px%6===0||py===Math.ceil(row*h/3)))ink=false;}
      else ink=mask[Math.floor(py*20/h)*12+px]==='1';}
     const rgb=palette[ink?c.fg:c.bg],offset=((y*20+py)*width+x*12+px)*4;for(let k=0;k<4;k++)pixels[offset+k]=rgb[k];
    }
   }lower=next;
  }
  const outWidth=720,outHeight=600,scan=Buffer.alloc(outHeight*(1+outWidth*4));
  for(let y=0;y<outHeight;y++)for(let x=0;x<outWidth;x++){
   const from=(Math.floor(y*height/outHeight)*width+Math.floor(x*width/outWidth))*4,to=y*(outWidth*4+1)+1+x*4;
   for(let k=0;k<4;k++)scan[to+k]=pixels[from+k];
  }
  const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(outWidth,0);ihdr.writeUInt32BE(outHeight,4);ihdr[8]=8;ihdr[9]=6;
  const source=`https://github.com/alxcrt/tvr-teletext-archive/tree/main/recordings/${directory}`;
  const comment=`Derived Level 1 preview; source page packet SHA-256 ${page.source_sha256}; font/character rendering approximate.`;
  writeFileSync(resolve(root,directory,page.file.replace('.t42','.png')),Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ihdr),chunk('tEXt',Buffer.from('Source\0'+source)),chunk('tEXt',Buffer.from('Comment\0'+comment)),chunk('IDAT',deflateSync(scan,{level:9})),chunk('IEND',Buffer.alloc(0))]));count++;
 }
}
console.log(`Rendered ${count} version previews`);
