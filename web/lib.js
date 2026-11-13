export const ui={catalog:[],project:null,state:null,result:null,tab:'workbench',live:false,busy:false,job:null,selection:0,render:()=>{},draw:()=>{},views:{}};
export const h=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const num=(v,d=1)=>v===null||v===undefined?'—':Number(v).toLocaleString(undefined,{maximumFractionDigits:d});
export const pct=v=>num(v*100,1)+'%';
export const button=(text,action,cls='',extra='')=>`<button class="${cls}" data-action="${h(action)}" ${extra}>${h(text)}</button>`;
export const panel=(title,body,extra='',flush=false)=>`<section class="panel"><div class="panelhead"><h3>${title}</h3>${extra}</div><div class="panelbody${flush?' flush':''}">${body}</div></section>`;
export const input=(id,label,value,type='text',extra='')=>`<label>${h(label)}<input id="${id}" type="${type}" value="${h(value)}" ${extra}></label>`;
export const select=(id,label,options,value)=>`<label>${h(label)}<select id="${id}">${options.map(o=>{const [v,t]=Array.isArray(o)?o:[o,o];return `<option value="${h(v)}" ${String(v)===String(value)?'selected':''}>${h(t)}</option>`}).join('')}</select></label>`;
export const textarea=(id,label,value)=>`<label>${h(label)}<textarea id="${id}">${h(value)}</textarea></label>`;
export const val=id=>document.getElementById(id)?.value;
export const stats=items=>`<div class="stats">${items.map(([label,value])=>`<div class="stat"><small>${h(label)}</small><strong>${h(value)}</strong></div>`).join('')}</div>`;
export const note=text=>`<div class="note">${h(text)}</div>`;
export const table=(headers,rows)=>`<div class="tablewrap"><table><thead><tr>${headers.map(t=>`<th>${h(t)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
export const result=(r=ui.state?.last_result)=>r?`<details><summary>Inspect structured results and provenance</summary><pre class="result">${h(JSON.stringify(r,null,2))}</pre></details>`:'';
export const canvas=(id,cls='')=>`<canvas id="${id}" class="${cls}" aria-label="Interactive project visualization"></canvas>`;
export function toast(text){const el=document.getElementById('toast');el.textContent=text;el.style.display='block';clearTimeout(el._timer);el._timer=setTimeout(()=>el.style.display='none',6500);}
export async function request(url,data){const response=await fetch(url,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const out=await response.json();if(!response.ok)throw Error(out.error||'Request failed');return out;}
export async function call(action,p={},background=false,quiet=false){
  if(ui.busy&&!quiet){toast('Wait for the current request to complete.');return;}
  if(!quiet){ui.busy=true;ui.lastError=null;}
  try{
    const out=await request(`/api/${ui.project.id}/${action}`,{...p,...(background?{_async:true}:{})});
    if(out.job_id){ui.live=false;ui.job={id:out.job_id,status:'running'};ui.render();poll(out.job_id);return;}
    if(out.state)ui.state=out.state;if(out.result!==null&&out.result!==undefined)ui.result=out.result;
    if(quiet){ui.draw();const box=document.getElementById('statistics');if(box&&ui.views[ui.project.id].stats)box.innerHTML=ui.views[ui.project.id].stats(ui.state);}else ui.render();
    return out.result;
  }catch(e){ui.lastError=e.message;toast(e.message);if(quiet)ui.live=false;}
  finally{if(!quiet)ui.busy=false;}
}
async function poll(id){
  try{const job=await request('/api/jobs/'+id);if(['queued','running'].includes(job.status)){if(ui.job?.id===id)setTimeout(()=>poll(id),700);return;}
    ui.job=null;if(job.response){ui.state=job.response.state;ui.result=job.response.result;}else toast(job.error||job.status);ui.render();
  }catch(e){ui.job=null;toast(e.message);ui.render();}
}
export async function fileData(id){const f=document.getElementById(id)?.files[0];if(!f)throw Error('Choose a file first');if(f.size>4000000)throw Error('Maximum file size is 4 MB');const raw=new Uint8Array(await f.arrayBuffer());let bin='';for(let i=0;i<raw.length;i+=8192)bin+=String.fromCharCode(...raw.subarray(i,i+8192));return {name:f.name,data:btoa(bin)};}
export function register(id,view){ui.views[id]=view;}
export function ctx(id){const el=document.getElementById(id);if(!el)return null;const ratio=Math.min(devicePixelRatio||1,2),w=el.clientWidth||600,he=el.clientHeight||330;if(el.width!==w*ratio||el.height!==he*ratio){el.width=w*ratio;el.height=he*ratio;}const c=el.getContext('2d');c.setTransform(ratio,0,0,ratio,0,0);c.clearRect(0,0,w,he);return {el,c,w,h:he};}
export function chart(id,series,keys,colors=['#d6b58a','#88c7c4','#b7a5de'],labels=true){
 const v=ctx(id);if(!v)return;const {c,w,h:height}=v;const left=47,top=25,bottom=height-30,right=w-20;if(!series?.length){c.fillStyle='#9cabb2';c.fillText('Run an experiment to collect observations.',25,45);return;}
 const max=Math.max(1,...series.flatMap(d=>keys.map(k=>Number(d[k])||0))),min=Math.min(0,...series.flatMap(d=>keys.map(k=>Number(d[k])||0)));c.font='10px system-ui';
 for(let i=0;i<5;i++){const y=top+(bottom-top)*i/4;c.strokeStyle='#334047';c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke();c.fillStyle='#889ba4';c.fillText(num(max-(max-min)*i/4),4,y+4);}
 keys.forEach((key,j)=>{c.strokeStyle=colors[j%colors.length];c.lineWidth=2;c.beginPath();series.forEach((d,i)=>{const x=left+(right-left)*i/Math.max(1,series.length-1),y=bottom-(Number(d[key])-min)/(max-min||1)*(bottom-top);i?c.lineTo(x,y):c.moveTo(x,y);});c.stroke();if(labels){c.fillStyle=colors[j%colors.length];c.fillText(key,left+j*140,13);}});
 c.fillStyle='#889ba4';c.fillText('first observation',left,height-9);c.fillText('latest',right-25,height-9);
}
export function grid(id,n,walls,points=[],trace=[],heat=null,onClick=null){const v=ctx(id);if(!v)return;const {el,c,w,h:height}=v;const size=Math.min(w-30,height-30)/n,ox=(w-size*n)/2,oy=(height-size*n)/2,max=heat?Math.max(1,...heat.flat()):1;c.fillStyle='#141e24';c.fillRect(ox,oy,size*n,size*n);for(let x=0;x<n;x++)for(let y=0;y<n;y++){if(heat?.[y]?.[x]){c.fillStyle=`rgba(235,156,104,${.8*heat[y][x]/max})`;c.fillRect(ox+x*size,oy+y*size,size,size);}c.strokeStyle='#28383f';c.strokeRect(ox+x*size,oy+y*size,size,size);}c.fillStyle='#4b5d65';walls.forEach(([x,y])=>c.fillRect(ox+x*size+1,oy+y*size+1,size-2,size-2));if(trace.length){c.strokeStyle='#e6bc83';c.lineWidth=2;c.beginPath();trace.forEach(([x,y],i)=>{const a=ox+(x+.5)*size,b=oy+(y+.5)*size;i?c.lineTo(a,b):c.moveTo(a,b);});c.stroke();}points.forEach(p=>{c.fillStyle=p.color||'#8acec5';c.beginPath();c.arc(ox+(p.pos[0]+.5)*size,oy+(p.pos[1]+.5)*size,size*(p.radius||.3),0,Math.PI*2);c.fill();});el.onclick=onClick?e=>{const r=el.getBoundingClientRect(),x=Math.floor((e.clientX-r.left-ox)/size),y=Math.floor((e.clientY-r.top-oy)/size);if(x>=0&&y>=0&&x<n&&y<n)onClick(x,y);}:null;}
export function network(id,nodes,edges,selected=null,onClick=null){const v=ctx(id);if(!v)return;const {el,c,w,h:height}=v;const coords=nodes.map((n,i)=>{const a=2*Math.PI*i/nodes.length-Math.PI/2,rad=Math.min(w,height)*(.3+.09*Math.sin(i*4));return [w/2+rad*Math.cos(a),height/2+rad*Math.sin(a)];});const map=new Map(nodes.map((n,i)=>[n.id,i]));edges.forEach(e=>{const a=map.get(e.source),b=map.get(e.target);if(a===undefined||b===undefined)return;c.strokeStyle=e.color||'#576c7955';c.lineWidth=e.width||1;c.beginPath();c.moveTo(...coords[a]);c.lineTo(...coords[b]);c.stroke();});nodes.forEach((n,i)=>{const p=coords[i];c.fillStyle=n.color||(n.id===selected?'#eac493':'#88a6ad');c.beginPath();c.arc(...p,n.id===selected?10:6,0,7);c.fill();if(nodes.length<18||n.id===selected){c.fillStyle='#ccd5d8';c.font='11px system-ui';c.fillText(n.name||String(n.id),p[0]+12,p[1]+4);}});el.onclick=onClick?e=>{const r=el.getBoundingClientRect();let best=-1,dist=25;coords.forEach((p,i)=>{const d=Math.hypot(p[0]-(e.clientX-r.left),p[1]-(e.clientY-r.top));if(d<dist){best=i;dist=d;}});if(best>=0)onClick(nodes[best].id);}:null;}
