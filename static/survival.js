/* Kaplan–Meier: deaths precede censoring at tied times; no event inferred from weight. */
(function(root){
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function estimate(records){
 if(!records.length)return [];
 for(const r of records)if(!Number.isFinite(r.time)||r.time<0||typeof r.event!=='boolean')throw Error('Invalid survival record');
 let risk=records.length,survival=1;
 return [...new Set(records.map(r=>r.time))].sort((a,b)=>a-b).map(time=>{const mice=records.filter(r=>r.time===time),deaths=mice.filter(r=>r.event).length,censored=mice.length-deaths;const before=risk;survival*=1-deaths/risk;risk-=mice.length;return {time,risk:before,deaths,censored,survival,mice};});
}
// Two-group, unweighted log-rank; tied deaths use hypergeometric variance.
function logRank(records){
 estimate(records);
 if(records.some(r=>!['CD','WD'].includes(r.group)))throw Error('Invalid survival group');
 if(!['CD','WD'].every(g=>records.some(r=>r.group===g)))return null;
 let observed=0,expected=0,variance=0;
 for(const time of [...new Set(records.filter(r=>r.event).map(r=>r.time))]){
  const risk=records.filter(r=>r.time>=time),n=risk.length,n1=risk.filter(r=>r.group==='CD').length,n2=n-n1;
  const deaths=records.filter(r=>r.time===time&&r.event),d=deaths.length;
  observed+=deaths.filter(r=>r.group==='CD').length;expected+=d*n1/n;
  if(n>1)variance+=n1*n2*d*(n-d)/(n*n*(n-1));
 }
 if(variance<=0)return null;
 const chiSquare=(observed-expected)**2/variance;
 // erfc(sqrt(chi-square/2)): stable upper tail, absolute error < 1.5e-7.
 const x=Math.sqrt(chiSquare/2),t=1/(1+0.5*x);
 const p=chiSquare===0?1:Math.min(1,t*Math.exp(-x*x-1.26551223+t*(1.00002368+t*(0.37409196+t*(0.09678418+t*(-0.18628806+t*(0.27886807+t*(-1.13520398+t*(1.48851587+t*(-0.82215223+t*0.17087277))))))))));
 return {chiSquare,p,observed,expected,variance};
}
function displayId(r){return r.perakakis_id?`Perakakis ID ${r.perakakis_id}`:r.mouse_id;}
if(typeof module!=='undefined')module.exports={estimate,logRank,displayId};
if(typeof document==='undefined')return;
let payload=null,selectedStudy='H2',selectedPoint=null,requestId=0;const ko=()=>window.I18n?.language==='ko',t=(en,kr)=>ko()?kr:en;
const button=document.createElement('button');button.id='survival-open';button.type='button';button.textContent='Infection';button.setAttribute('aria-pressed','false');
document.querySelector('.graph-selection-actions .import-tabs').append(button);
const graphPage=document.querySelector('#graphs');const dialog=document.createElement('section');dialog.id='infection-view';dialog.hidden=true;dialog.setAttribute('aria-labelledby','survival-heading');dialog.setAttribute('data-no-translate','');graphPage.querySelector('.graph-toolbar').after(dialog);
function tooltip(point){return `${t('dpi','dpi')} ${point.time} · ${t('Survival','생존율')} ${(point.survival*100).toFixed(1)}%\n${t('At risk before this time','해당 시점 직전 관찰 수')}: ${point.risk}\n\n`+point.mice.map(r=>`${displayId(r)} · ${r.group}\n${r.event?t('Death','사망'):t('Censored (observation ended)','관찰 종료 (중도절단)')} · dpi ${r.time}\n${t('Last measured weight','마지막 측정 체중')}: ${r.last_weight} g (dpi ${r.last_day})\n${t('Baseline','초기 체중')}: ${r.baseline_weight} g · ${t('Change','변화율')}: ${((r.last_weight/r.baseline_weight-1)*100).toFixed(1)}%`).join('\n\n');}
function chart(study){
 const result=logRank(study.records),pLabel=result?`CD vs WD · Log-rank p = ${result.p<0.0001?result.p.toExponential(2):result.p.toFixed(4)}`:'CD vs WD · Log-rank p: not estimable';
 const end=Math.max(...study.records.map(r=>r.time)),x=v=>65+v/end*560,y=v=>295-v*230;
 let svg=`<svg viewBox="0 0 670 410" role="img" aria-label="${esc(study.name)} survival"><rect width="670" height="410" fill="white"/><text x="335" y="25" text-anchor="middle" font-size="20" font-weight="700">${esc(study.name)} · Survival</text><text data-survival-p="" x="335" y="44" text-anchor="middle" font-size="12">${pLabel}</text><path d="M65 55V295H625" fill="none" stroke="#222"/>`;
 for(const n of [0,.25,.5,.75,1])svg+=`<text x="56" y="${y(n)+4}" text-anchor="end" font-size="12">${n*100}</text>`;
 const ticks=[...new Set([0,...Array.from({length:Math.floor(end/2)},(_,i)=>(i+1)*2),end])];
 for(const day of ticks)svg+=`<path d="M${x(day)} 295v5" stroke="#222"/><text x="${x(day)}" y="316" font-size="12" text-anchor="middle">${day}</text>`;
 svg+='<text x="335" y="340" text-anchor="middle" font-size="13">Days post infection (dpi)</text><text transform="translate(18 180) rotate(-90)" text-anchor="middle" font-size="13">Survival (%)</text>';
 for(const [i,group] of ['CD','WD'].entries()){
  const records=study.records.filter(r=>r.group===group),points=estimate(records),color=i?'#fc225c':'#222';if(!records.length)continue;
  let path=`M${x(0)} ${y(1)}`;
  for(const p of points)path+=`H${x(p.time)}V${y(p.survival)}`;
  svg+=`<path d="${path}" fill="none" stroke="${color}" stroke-width="2.5"/>`;
  for(const p of points){const title=tooltip(p);svg+=`<g tabindex="0" role="button" aria-pressed="false" data-group="${group}" data-day="${p.time}" data-tip="${esc(title)}" aria-label="${esc(group)} · Day ${p.time} · ${t('Show individual outcomes','개체별 결과 보기')}"><circle cx="${x(p.time)}" cy="${y(p.survival)}" r="9" fill="transparent"/>`;
   if(p.deaths)svg+=`<circle cx="${x(p.time)}" cy="${y(p.survival)}" r="4" fill="${color}"/>`;
   if(p.censored)svg+=`<path d="M${x(p.time)-5} ${y(p.survival)}h10M${x(p.time)} ${y(p.survival)-5}v10" stroke="${color}" stroke-width="2"/>`;
   svg+='</g>';
  }
  svg+=`<text x="${190+i*260}" y="366" fill="${color}" font-size="13" font-weight="700">${group} · n=${records.length} · ${records.filter(r=>r.event).length} deaths</text>`;
 }
 return svg+'<text x="335" y="392" text-anchor="middle" font-size="11">Kaplan–Meier · + censored · click markers for individual weights</text></svg>';
}
function exportSVG(svg){const copy=svg.cloneNode(true);copy.style.removeProperty('height');copy.querySelectorAll('[aria-pressed]').forEach(el=>el.setAttribute('aria-pressed','false'));return copy.outerHTML;}
function save(name,text,type){const url=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
let fitFrame=0;
function fit(){
 fitFrame=0;if(dialog.hidden||graphPage.hidden)return;
 const card=dialog.querySelector('.survival-card');if(!card)return;
 const style=getComputedStyle(card),svg=card.querySelector('svg');
 const chrome=parseFloat(style.paddingTop)+parseFloat(style.paddingBottom)+2+card.querySelector('.survival-actions').getBoundingClientRect().height+[...card.querySelectorAll('details')].reduce((sum,d)=>{const cs=getComputedStyle(d);return sum+d.querySelector('summary').getBoundingClientRect().height+parseFloat(cs.paddingTop)+parseFloat(cs.paddingBottom)+parseFloat(cs.borderTopWidth);},0);
 const available=innerHeight-(card.getBoundingClientRect().top+scrollY)-chrome-18;
 const height=Math.max(220,Math.min(available,(card.clientWidth-28)*410/670));svg.style.height=height+'px';
 dialog.style.setProperty('--infection-panel-height',(height+chrome)+'px');
}
function scheduleFit(){if(!fitFrame)fitFrame=requestAnimationFrame(fit);}
window.addEventListener('resize',scheduleFit);
const sizing=new ResizeObserver(scheduleFit);sizing.observe(document.querySelector('#workspace>header'));sizing.observe(graphPage.querySelector('.graph-toolbar'));
new MutationObserver(scheduleFit).observe(graphPage,{attributes:true,attributeFilter:['hidden']});
function render(){
 dialog.innerHTML=`<div class="infection-toolbar"><label>${t('Experiment','실험')}<select id="infection-experiment"><option value="H2">H2</option><option value="H3">H3</option></select></label><strong id="survival-heading">${esc(selectedStudy)} · Survival</strong></div><p>${t('H2 and H3 are separate infection experiments. Red cells = death; others censored at their last recorded Day. Main Graph selections and exclusions do not apply.','H2와 H3는 별개의 감염 실험입니다. 붉은 셀은 사망, 나머지는 마지막 기록일의 관찰 종료입니다. 기존 Graph의 선택·제외는 적용되지 않습니다.')}</p><div id="survival-content"></div>`;
 dialog.querySelector('#infection-experiment').value=selectedStudy;
 dialog.querySelector('#infection-experiment').onchange=e=>{selectedStudy=e.target.value;selectedPoint=null;render();dialog.querySelector('#infection-experiment').focus();};
 const content=dialog.querySelector('#survival-content');if(!payload){content.textContent=t('Loading…','불러오는 중…');return;}
 if(!payload.studies?.length){content.textContent=t('No survival dataset has been installed on this server.','이 서버에는 생존 데이터가 등록되지 않았습니다.');return;}
 const studies=payload.studies.filter(s=>s.name===selectedStudy);
 content.innerHTML=studies.map((s,i)=>`<section class="survival-card">${chart(s)}<div class="survival-actions"><button data-svg="${i}">Export SVG</button><button data-csv="${i}">Data CSV</button></div><details><summary>${t('Individual outcomes and last weights','개체별 결과 및 마지막 체중')} (${s.records.length})</summary><div class="table-scroll"><table><thead><tr>${['Mouse ID','Group','dpi','Outcome','Last weight (g)','Last weight dpi'].map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${s.records.map(r=>`<tr><td>${esc(r.perakakis_id||r.mouse_id)}</td><td>${esc(r.group)}</td><td>${r.time}</td><td>${r.event?t('Death','사망'):t('Censored','관찰 종료')}</td><td>${r.last_weight}</td><td>${r.last_day}</td></tr>`).join('')}</tbody></table></div></details><details><summary>${t('Number at risk (just before dpi)','해당 dpi 직전 관찰 수')}</summary><div class="table-scroll"><table><tr><th>Group</th>${Array.from({length:Math.max(...s.records.map(r=>r.time))+1},(_,d)=>`<th>${d}</th>`).join('')}</tr>${['CD','WD'].map(g=>`<tr><td>${g}</td>${Array.from({length:Math.max(...s.records.map(r=>r.time))+1},(_,d)=>`<td>${s.records.filter(r=>r.group===g&&r.time>=d).length}</td>`).join('')}</tr>`).join('')}</table></div></details></section>`).join('');
 content.insertAdjacentHTML('beforeend',`<aside class="survival-inspector" aria-labelledby="survival-info-heading"><h3 id="survival-info-heading">${t('Selected point','선택한 지점')}</h3><div id="survival-point-info" aria-live="polite"><p>${t('Click a death or censor marker on the graph to view the mice and their last measured weights.','그래프의 사망 또는 관찰 종료 표시를 클릭하면 해당 마우스와 마지막 측정 체중을 볼 수 있습니다.')}</p></div></aside>`);
 content.querySelectorAll('[data-svg]').forEach(b=>b.onclick=()=>save(studies[b.dataset.svg].name+'-survival.svg',exportSVG(content.querySelectorAll('svg')[b.dataset.svg]).replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" '),'image/svg+xml'));
 content.querySelectorAll('[data-csv]').forEach(b=>b.onclick=()=>{const s=studies[b.dataset.csv],fields=['display_id','group','time','event','last_weight','last_day','baseline_weight'];const q=v=>'"'+String(v).replaceAll('"','""')+'"';save(s.name+'-survival.csv',fields.join(',')+'\n'+s.records.map(r=>fields.map(k=>q(k==='display_id'?displayId(r):(r[k]??''))).join(',')).join('\n'),'text/csv;charset=utf-8');});
 const metadata=payload.infection_roster?.records||[];
 const roster=studies.flatMap(s=>s.records.map(r=>({...r,diet:r.group,dpi:r.time,age_weeks:'—',...metadata.find(m=>r.perakakis_id&&m.perakakis_id===r.perakakis_id)})));
 if(roster.length)content.querySelector('.survival-inspector').insertAdjacentHTML('beforeend',`<details class="infection-roster" open><summary>${t('Mouse roster','마우스 명단')} (${roster.length})</summary><p>${t('dpi = days post infection; weeks = age.','dpi = 감염 후 경과일, weeks = 주령입니다.')}</p><div class="table-scroll"><table><thead><tr><th>Mouse ID</th><th>Diet</th><th>Weeks</th><th>dpi</th></tr></thead><tbody>${roster.map(r=>`<tr><td>${esc(r.perakakis_id||r.mouse_id)}</td><td>${esc(r.diet)}</td><td>${esc(r.age_weeks)}</td><td>${esc(r.dpi)}</td></tr>`).join('')}</tbody></table></div></details>`);
 const info=dialog.querySelector('#survival-point-info');
 function selectPoint(el){
  selectedPoint={group:el.dataset.group,day:el.dataset.day};
  content.querySelectorAll('[data-tip]').forEach(point=>point.setAttribute('aria-pressed',String(point===el)));
  const blocks=el.dataset.tip.split('\n\n');
  info.innerHTML=`<div class="survival-point-overview"><strong>${esc(selectedStudy)} · ${esc(el.dataset.group)}</strong><p>${esc(blocks[0])}</p></div>`+blocks.slice(1).filter(block=>block.trim()).map(block=>`<article class="survival-mouse-info"><strong>${esc(block.split('\n')[0])}</strong><p>${esc(block.split('\n').slice(1).join('\n'))}</p></article>`).join('');
  info.parentElement.scrollTop=0;
 }
 content.querySelectorAll('[data-tip]').forEach(el=>{el.onclick=()=>selectPoint(el);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectPoint(el);}};if(selectedPoint&&el.dataset.group===selectedPoint.group&&el.dataset.day===selectedPoint.day)selectPoint(el);});scheduleFit();
}
button.onclick=async()=>{const id=++requestId;payload=null;graphPage.classList.add('infection-mode');dialog.hidden=false;button.setAttribute('aria-pressed','true');document.querySelectorAll('[data-study]').forEach(b=>b.setAttribute('aria-pressed','false'));render();try{const response=await fetch('/api/survival');if(!response.ok)throw Error(t('Sign in to view survival data.','생존 데이터를 보려면 로그인해주세요.'));const result=await response.json();if(id!==requestId)return;payload=result;render();}catch(e){if(id===requestId)dialog.querySelector('#survival-content').textContent=e.message;}};
document.querySelectorAll('[data-study]').forEach(b=>b.addEventListener('click',()=>{requestId++;graphPage.classList.remove('infection-mode');dialog.hidden=true;button.setAttribute('aria-pressed','false');}));
document.addEventListener('languagechange',()=>{if(!dialog.hidden)render();});
})(typeof window!=='undefined'?window:globalThis);
