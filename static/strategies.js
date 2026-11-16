'use strict';
(()=>{
const ko={ 'Gating strategy images':'게이팅 전략 이미지','View gating strategy':'게이팅 전략 보기','Close':'닫기','Review unassigned images':'미검토 이미지 검토','Experiment':'실험','Organ':'장기','Panel':'패널','All':'전체','Previous':'이전','Next':'다음','Original image':'원본 그림','Original workbook':'원본 엑셀','No matching reviewed images.':'조건에 맞는 검토 완료 이미지가 없습니다.','Preview unavailable for this format. Open the original workbook.':'이 형식은 미리보기를 지원하지 않습니다. 원본 엑셀을 열어주세요.','Save review':'검토 저장','Description':'설명','Reason':'변경 사유','Pending':'미검토','Approved strategy':'확인된 게이팅 전략','Not a strategy':'게이팅 전략 아님','Extract from uploaded workbook':'업로드된 엑셀에서 추출','Select workbook':'엑셀 선택','Assignments are confirmed by an administrator. Original image and workbook remain unchanged.':'관리자가 연결 정보를 확인합니다. 원본 그림과 엑셀은 변경하지 않습니다.'};
Object.assign(ko,{'Filters':'필터','Upload workbook':'엑셀 업로드','Image review':'이미지 검토','Source details':'원본 정보','Fit':'화면 맞춤','Zoom in':'확대','Zoom out':'축소'});
const sections={filters:true,upload:false,review:false,source:false};
const t=s=>I18n.language==='ko'?(ko[s]||s):s;
const dialog=document.querySelector('#strategy-dialog');
let rows=[],selected='',zoom=100,review=false,filters={experiment:'',organ:'',panel:''};
const get=id=>dialog.querySelector('#'+id);
const filtered=()=>rows.filter(r=>Object.entries(filters).every(([k,v])=>!v||r[k]===v));
function paint(){
 const listTop=dialog.querySelector('.strategy-list')?.scrollTop||0,railTop=dialog.querySelector('.strategy-sidebar')?.scrollTop||0;
 const admin=user?.role==='admin';const visible=filtered();if(!visible.some(r=>r.id===selected))selected=visible[0]?.id||'';
 const row=visible.find(r=>r.id===selected);const idx=visible.indexOf(row);
 dialog.innerHTML=`<div class="dialog-top"><h2>${t('Gating strategy images')}</h2><span>${visible.length} / ${rows.length}</span></div><p>${t('Assignments are confirmed by an administrator. Original image and workbook remain unchanged.')}</p>
 <div class="strategy-filters">${['experiment','organ','panel'].map(k=>`<label>${t(k[0].toUpperCase()+k.slice(1))}<select data-st-filter="${k}"><option value="">${t('All')}</option>${[...new Set(rows.map(r=>r[k]).filter(Boolean))].sort().map(v=>`<option ${filters[k]===v?'selected':''} value="${esc(v)}">${esc(v)}</option>`).join('')}</select></label>`).join('')}${admin?`<label class="inline"><input id="st-review" type="checkbox" ${review?'checked':''}>${t('Review unassigned images')}</label>`:''}</div>
 ${admin&&review?`<div class="inline"><label>Upload strategy workbook (XLSX, up to 10 MB)<input id="st-new-workbook" type="file" accept=".xlsx"></label><button id="st-direct-upload">Upload workbook</button></div><div class="inline"><select id="st-upload"><option value="">${t('Select workbook')}</option>${(data?.uploads||[]).filter(u=>u.filename?.toLowerCase().endsWith('.xlsx')).map(u=>`<option value="${esc(u.id)}">${esc(u.filename)}</option>`).join('')}</select><button id="st-extract">${t('Extract from uploaded workbook')}</button></div>`:''}
 <p id="st-error" role="alert"></p><div class="strategy-layout"><div class="strategy-list">${visible.map(r=>`<button data-st-image="${r.id}" class="${r.id===selected?'primary':''}">${r.mime?`<img loading="lazy" src="/api/strategies/${r.id}/preview" alt="">`:''}<b>${esc(r.experiment||r.filename)}</b><span>${esc(r.organ+' / '+r.panel)}</span><small>${esc(r.sheet+' · '+r.anchor+' · '+r.status)}</small></button>`).join('')}</div><div class="strategy-main">${row?`
 <div class="inline"><button id="st-prev" ${idx<=0?'disabled':''}>${t('Previous')}</button><span>${idx+1} / ${visible.length}</span><button id="st-next" ${idx>=visible.length-1?'disabled':''}>${t('Next')}</button><label>Zoom <input id="st-zoom" type="range" min="25" max="300" step="25" value="${zoom}"></label><span id="st-scale">${zoom}%</span></div>
 <p><b>${esc(row.filename)}</b> · ${esc(row.sheet)} · ${esc(row.anchor)}<br>${esc(row.member)}</p><div class="strategy-image-stage">${row.mime?`<img id="st-image" src="/api/strategies/${row.id}/preview" alt="${esc(row.description||row.panel||row.sheet)}" style="width:${zoom}%">`:`<p>${t('Preview unavailable for this format. Open the original workbook.')}</p>`}</div><p>${esc(row.description)}</p>
 <div class="inline"><a href="/api/strategies/${row.id}/original" download>${t('Original image')}</a><a href="/api/strategies/${row.id}/workbook" download>${t('Original workbook')}</a></div>
 ${admin&&review?`<form id="st-form"><div class="strategy-filters">${['experiment','organ','panel'].map(k=>`<label>${t(k[0].toUpperCase()+k.slice(1))}<input name="${k}" value="${esc(row[k])}" placeholder="${esc(k==='experiment'?row.filename.replace(/\.xlsx$/i,'').replaceAll(' ',''):k==='organ'?row.sheet.includes('Liver')?'Liver':row.sheet.includes('Gut')?'Gut':'':'')}" maxlength="200"></label>`).join('')}</div><label>${t('Description')}<textarea name="description" maxlength="2000">${esc(row.description)}</textarea></label><select name="status">${[['pending','Pending'],['approved','Approved strategy'],['not_strategy','Not a strategy']].map(([v,label])=>`<option value="${v}" ${row.status===v?'selected':''}>${t(label)}</option>`).join('')}</select><label>${t('Reason')}<input name="reason" required maxlength="2000"></label><button type="submit">${t('Save review')}</button></form>`:''}`:`<p>${t('No matching reviewed images.')}</p>`}</div></div>`;
 layoutViewer(row);
 requestAnimationFrame(()=>{dialog.querySelector('.strategy-list').scrollTop=listTop;dialog.querySelector('.strategy-sidebar').scrollTop=railTop;});
 dialog.querySelectorAll('[data-st-filter]').forEach(e=>e.onchange=()=>{filters[e.dataset.stFilter]=e.value;paint()});
 dialog.querySelectorAll('[data-st-image]').forEach(e=>e.onclick=()=>{selected=e.dataset.stImage;zoom=100;paint()});
 if(admin)get('st-review').onchange=async e=>{review=e.target.checked;filters={experiment:'',organ:'',panel:''};await load()};
 if(row){get('st-prev').onclick=()=>{selected=visible[idx-1]?.id||selected;zoom=100;paint()};get('st-next').onclick=()=>{selected=visible[idx+1]?.id||selected;zoom=100;paint()};}
 if(get('st-form'))get('st-form').onsubmit=async e=>{e.preventDefault();const values=Object.fromEntries(new FormData(e.target));try{await api('/strategies/'+row.id,'POST',{...values,version:row.version});await load()}catch(error){get('st-error').textContent=error.message}};
 if(get('st-direct-upload'))get('st-direct-upload').onclick=async e=>{const f=get('st-new-workbook').files[0];if(!f){get('st-error').textContent='Choose an XLSX workbook.';return}if(f.size>10*1024*1024){get('st-error').textContent='Workbook exceeds 10 MB.';return}e.target.disabled=true;try{const content=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]);r.onerror=reject;r.readAsDataURL(f)});await api('/strategies/upload','POST',{filename:f.name,content});await load()}catch(error){get('st-error').textContent=error.message;e.target.disabled=false}};
if(get('st-extract'))get('st-extract').onclick=async e=>{e.target.disabled=true;try{await api('/strategies/extract','POST',{upload_id:get('st-upload').value});await load()}catch(error){get('st-error').textContent=error.message;e.target.disabled=false}};
}

function fitImage(){
 const stage=dialog.querySelector('.strategy-image-stage'),img=get('st-image');
 if(!stage||!img||!img.naturalWidth)return;
 const scale=Math.min((stage.clientWidth-20)/img.naturalWidth,(stage.clientHeight-20)/img.naturalHeight)*zoom/100;
 img.style.width=Math.max(1,img.naturalWidth*scale)+'px';img.style.height=Math.max(1,img.naturalHeight*scale)+'px';
 stage.classList.toggle('is-pannable',stage.scrollWidth>stage.clientWidth||stage.scrollHeight>stage.clientHeight);
 get('st-scale').textContent=zoom+'%';
 get('st-minus').disabled=zoom<=25;get('st-plus').disabled=zoom>=300;
}
function sizeViewer(){
 if($('#gating').hidden)return;
 dialog.style.height=Math.max(360,window.innerHeight-dialog.getBoundingClientRect().top-24)+'px';fitImage();
}
function layoutViewer(row){
 const layout=dialog.querySelector('.strategy-layout'),main=dialog.querySelector('.strategy-main');
 const aside=document.createElement('aside');aside.className='strategy-sidebar';
 function section(key,label,nodes){const d=document.createElement('details');d.open=sections[key];const h=document.createElement('summary');h.textContent=t(label);d.append(h);const body=document.createElement('div');body.className='strategy-section-body';nodes.filter(Boolean).forEach(n=>body.append(n));d.append(body);d.ontoggle=()=>{sections[key]=d.open};aside.append(d);}
 const filters=dialog.querySelector('.strategy-filters');
 const uploadNodes=[...dialog.children].filter(n=>n.classList.contains('inline'));
 const intro=dialog.querySelector(':scope > p:not(#st-error)');
 section('filters','Filters',[filters]);
 if(uploadNodes.length)section('upload','Upload workbook',uploadNodes);
 const form=get('st-form');if(form)section('review','Image review',[form]);
 const sourceNodes=[...main.children].filter(n=>n.tagName==='P'||(n.classList.contains('inline')&&n.querySelector('a')));
 if(row)section('source','Source details',[...sourceNodes,intro]);else if(intro)intro.remove();
 layout.append(aside);
 if(row){
 const toolbar=main.querySelector('.inline');toolbar.className='strategy-view-toolbar';toolbar.querySelector('label').remove();get('st-scale').remove();
 const z=document.createElement('div');z.className='strategy-zoom';z.innerHTML=`<button id="st-minus" aria-label="${t('Zoom out')}">−</button><span id="st-scale">${zoom}%</span><button id="st-plus" aria-label="${t('Zoom in')}">+</button><button id="st-fit">${t('Fit')}</button>`;toolbar.append(z);
 const stage=main.querySelector('.strategy-image-stage');stage.tabIndex=0;
 const img=get('st-image');if(img){img.onload=fitImage;img.draggable=false;}
 let drag=null;
 stage.onpointerdown=e=>{if(e.button!==0||!img)return;if(stage.scrollWidth<=stage.clientWidth&&stage.scrollHeight<=stage.clientHeight)return;e.preventDefault();drag={id:e.pointerId,x:e.clientX,y:e.clientY,left:stage.scrollLeft,top:stage.scrollTop};stage.setPointerCapture(e.pointerId);stage.classList.add('is-dragging');};
 stage.onpointermove=e=>{if(!drag||drag.id!==e.pointerId)return;stage.scrollLeft=drag.left+drag.x-e.clientX;stage.scrollTop=drag.top+drag.y-e.clientY;};
 const endDrag=e=>{if(!drag||drag.id!==e.pointerId)return;drag=null;stage.classList.remove('is-dragging');if(stage.hasPointerCapture(e.pointerId))stage.releasePointerCapture(e.pointerId);};
 stage.onpointerup=endDrag;stage.onpointercancel=endDrag;stage.onlostpointercapture=endDrag;

 for(const [id,change] of [['st-minus',-25],['st-plus',25],['st-fit',0]])get(id).onclick=()=>{zoom=change?Math.min(300,Math.max(25,zoom+change)):100;fitImage();if(!change){stage.scrollTop=0;stage.scrollLeft=0}};
 }
 requestAnimationFrame(sizeViewer);
}
window.addEventListener('resize',sizeViewer);

async function load(){try{rows=(await api('/strategies'+(review?'?review=1':''))).filter(r=>!String(r.anchor||'').startsWith('Unmapped media;')&&!['metabolic biochemical outcomes','neutrophil panels'].includes(String(r.sheet||'').trim().replace(/\s+/g,' ').toLowerCase()));rows.sort((a,b)=>Number(Boolean(b.mime))-Number(Boolean(a.mime)));paint()}catch(e){paint();get('st-error').textContent=e.message+' — Please reload after the development server has restarted.';get('st-error').className='error'}}
async function open(context={}){if(guest){notice('Sign in and select study data to view gating strategies.');return}review=user?.role==='admin'&&!context.organ;filters={experiment:context.experiment||'',organ:context.organ||'',panel:context.panel||''};rows=[];paint();await load()}
document.addEventListener('click',e=>{if(e.target.closest('[data-page="gating"]')&&user&&!guest)open()});
document.addEventListener('languagechange',()=>{if(!$('#gating').hidden)paint()});
})();
