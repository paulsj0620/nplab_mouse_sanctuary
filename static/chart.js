(function(root){
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const gateName=path=>String(path??'').split('/').map(s=>s.trim()).filter(Boolean).pop()||'';
const referencePalette=[{key:'Chow',color:'#000000',shape:'square',fill:'outline'},{key:'Western',color:'#fc225c',shape:'triangle',fill:'outline'},{key:'TRF 6:18',color:'#197274',shape:'down',fill:'outline'},{key:'TRF 10:14',color:'#64c3fa',shape:'diamond',fill:'outline'},{key:'ADF',color:'#3b0070',shape:'circle',fill:'outline'},{key:'Reverse',color:'#a55af8',shape:'square',fill:'outline'}];
function groupKey(group){const text=String(group).toLowerCase(),compact=text.replace(/[\s:_-]/g,'');if(/\bchow\b/.test(text))return 'Chow';if(/\bwestern\b|\bwd\b/.test(text))return 'Western';if(compact.includes('trf618'))return 'TRF 6:18';if(compact.includes('trf1014'))return 'TRF 10:14';if(/\badf\b/.test(text))return 'ADF';if(/\breverse\b|\brc\b/.test(text))return 'Reverse';return String(group);}
function defaultGroupStyle(group,index=0){const key=groupKey(group),position=referencePalette.findIndex(p=>p.key===key),found=referencePalette[position];return {...(found||{color:'#555555',shape:'circle',fill:'outline'}),order:position<0?700+index:(position+1)*100+index};}
function moveGroup(keys,source,target,after=false){const result=keys.filter(k=>k!==source);if(!keys.includes(source)||!keys.includes(target)||source===target)return [...keys];result.splice(result.indexOf(target)+(after?1:0),0,source);return result;}
function formatP(value,prefix='p'){if(!Number.isFinite(value)||value<0||value>1)throw Error('p-value must be a number between 0 and 1.');return value===0?`${prefix} ≈ 0`:`${prefix} = ${value<0.0001?value.toExponential(2):Number(value.toPrecision(4))}`;}
function comparisonLabels(analysis,cfg,groups){if(cfg.comparisonMode==='none'||analysis?.status!=='ok')return [];const valid=analysis.groups.map(g=>g.group).filter(g=>groups.includes(g));let pairs=analysis.pairs.filter(p=>valid.includes(p.a)&&valid.includes(p.b));const mode=cfg.comparisonMode||'p05';if(mode==='p10')pairs=pairs.filter(p=>p.p_adjusted<0.1);else if(mode==='p05')pairs=pairs.filter(p=>p.p_adjusted<0.05);return pairs.map(p=>[p.a,p.b,formatP(p.p_adjusted)]);}
function metricTitle(metric){return metric.source_header||(metric.name.startsWith('Geometric Mean (')&&metric.gate?`${metric.gate} | ${metric.name}`:[metric.name,metric.organ,gateName(metric.gate)].filter(Boolean).join(' · '));}
function wrapTitle(title,maxChars){const lines=[];let line='';for(const token of String(title).match(/[^\s/]+\/?|\s+/g)||[]){if(line.length+token.length>maxChars&&line.trim()){lines.push(line.trim());line='';}for(let part=token;part;){const room=maxChars-line.length;line+=part.slice(0,room);part=part.slice(room);if(part){lines.push(line.trim());line='';}}}if(line.trim())lines.push(line.trim());return lines.length?lines:[''];}
function stats(v){const n=v.length;if(!n)return {n,mean:null,sd:null,sem:null};const mean=v.reduce((a,b)=>a+b,0)/n,sd=n>1?Math.sqrt(v.reduce((a,b)=>a+(b-mean)**2,0)/(n-1)):null;return {n,mean,sd,sem:sd===null?null:sd/Math.sqrt(n)};}
function marker(x,y,shape,color,size=4.5,open=false,attrs=''){
 const a=`fill="${open?'white':color}" stroke="${color}" stroke-width="1.3" ${attrs}`;
 if(shape==='square')return `<rect x="${x-size}" y="${y-size}" width="${size*2}" height="${size*2}" ${a}/>`;
 if(shape==='triangle')return `<path d="M${x} ${y-size*1.2}L${x+size} ${y+size}L${x-size} ${y+size}Z" ${a}/>`;
 if(shape==='down')return `<path d="M${x} ${y+size*1.2}L${x+size} ${y-size}L${x-size} ${y-size}Z" ${a}/>`;
 if(shape==='diamond')return `<path d="M${x} ${y-size*1.3}L${x+size} ${y}L${x} ${y+size*1.3}L${x-size} ${y}Z" ${a}/>`;
 return `<circle cx="${x}" cy="${y}" r="${size}" ${a}/>`;
}
function weekNumber(label){
 const match=String(label).trim().match(/^(?:w(?:eeks?|k)?\s*[-_:]?\s*)?(\d+(?:\.\d+)?)\s*(?:w(?:eeks?|k)?)?$/i);
 return match?Number(match[1]):null;
}
function dateNumber(label){const text=String(label);if(!/^\d{4}-\d{2}-\d{2}$/.test(text))return null;const n=Date.parse(text+'T00:00:00Z');return Number.isFinite(n)&&new Date(n).toISOString().slice(0,10)===text?n/86400000:null;}
function timeNumber(label){return dateNumber(label)??Number(label);}
function isWeight(metric){
 return /^(?:body[ _-]*)?weight(?:$|[ _(-](?:g\b|timeline\b|endpoint\b))/i.test(metric?.name||'');
}
function metricChoices(data,metrics){
 const files=new Map((data.uploads||[]).map(u=>[u.id,u.filename]));
 const evidence=new Map();
 for(const row of data.measurements){
  if(!Number.isFinite(row.value))continue;
  if(!evidence.has(row.metric_id))evidence.set(row.metric_id,{times:new Set(),sources:new Set()});
  const entry=evidence.get(row.metric_id);
  entry.times.add(row.timepoint);entry.sources.add(files.get(row.upload_id)||'');
 }
 const choices=[];
 const pathsByGate=new Map();
 for(const metric of metrics){
  const entry=evidence.get(metric.id);
  if(!entry)continue;
  const {name,organ,gate}=metric;
  let labels={};
  try{labels=JSON.parse(metric.identity||'{}')||{};}catch{}
  const add=(path,view='')=>choices.push({metric,path,view});
  if(gate){
   const sources=[...entry.sources].map(f=>/\bt[ _-]*reg(?:s)?\b/i.test(f)?'Treg Panel':/\bt[ _-]*cells?\b/i.test(f)?'T Cell Panel':'Unspecified panel');
   const panel=labels.panel||(new Set(sources).size===1?sources[0]:'Mixed / unspecified panels');
   const path=['Flow cytometry',organ||'Unspecified organ',panel,gateName(gate)||'Unspecified gate'];
   add(path);
   const key=JSON.stringify(path);
   if(!pathsByGate.has(key))pathsByGate.set(key,new Map());
   const populations=pathsByGate.get(key);
   if(!populations.has(gate))populations.set(gate,[]);
   populations.get(gate).push(path);
  }else if(labels.pathway||/qPCR/i.test(name)){
   add(['qPCR',organ||'Unspecified organ',labels.pathway||'Unspecified pathway']);
  }else if(/^(?:PSR|HE\b|H&E|lipid droplet)/i.test(name)){
   add(['Histology',organ||'Unspecified organ']);
  }else if(isWeight(metric)){
   const times=[...entry.times];
   if(times.some(t=>weekNumber(t)!==null))add(['Metabolic outcome','Weight-timeline'],'weekly');
   if(times.some(t=>dateNumber(t)!==null))add(['Metabolic outcome','Weight-timeline'],'dated');
   if(times.some(t=>weekNumber(t)===null&&dateNumber(t)===null))add(['Metabolic outcome','Weight-endpoint'],'endpoint');
  }else if(/^(OGTT|ITT)\b/i.test(name)){
   add(['Metabolic outcome',name.match(/^(OGTT|ITT)/i)[0].toUpperCase()]);
  }else{
   add([/weight|cholesterol|ldl|hdl|triglyceride|glucose/i.test(name)?'Metabolic outcome':'Other measurements']);
  }
 }
 // Disambiguate identical terminal names only within the same organ and panel.
 for(const populations of pathsByGate.values()){
  if(populations.size<2)continue;
  for(const [gate,paths] of populations){
   const parent=gate.split('/').map(part=>part.trim()).filter(Boolean).slice(0,-1).join(' / ');
   for(const path of paths)path[3]+=' ('+(parent||'root')+')';
  }
 }
 return choices;
}
function rowsForPanel(data,cfg){
 const weekly=cfg.type==='line'&&isWeight(data.metrics?.find(m=>m.id===Number(cfg.metric)));
 const rows=data.measurements.filter(r=>r.metric_id===Number(cfg.metric)&&(!cfg.replicate||r.replicate===cfg.replicate)&&(cfg.type==='line'||!cfg.timepoint||r.timepoint===cfg.timepoint));
 if(!weekly)return rows;
 const dated=cfg.weightAxis==='date'||(!cfg.weightAxis&&!rows.some(r=>weekNumber(r.timepoint)!==null));
 return dated?rows.filter(r=>dateNumber(r.timepoint)!==null):rows.filter(r=>weekNumber(r.timepoint)!==null).map(r=>({...r,timepoint:String(weekNumber(r.timepoint))}));
}
function dataset(data,cfg){
 const mice=data.mice.filter(m=>(!Array.isArray(cfg.scope_mouse_ids)||cfg.scope_mouse_ids.includes(m.mouse_id))&&(!Array.isArray(cfg.scope_experiments)||cfg.scope_experiments.includes(m.experiment))&&(!cfg.experiment||m.experiment===cfg.experiment)&&(!cfg.weeks||m.weeks===cfg.weeks));const byId=new Map(mice.map(m=>[m.mouse_id,m]));
 const records=rowsForPanel(data,cfg).filter(r=>byId.has(r.mouse_id));
 if(cfg.type==='line'&&isWeight(data.metrics.find(m=>m.id===Number(cfg.metric)))&&new Set(records.map(r=>byId.get(r.mouse_id).experiment).filter(Boolean)).size>1)throw Error('Select one experiment for the body weight timeline in Graph settings.');
 let groups=[...new Set(mice.map(m=>m[cfg.grouping]||'Not specified'))];groups=groups.filter(g=>cfg.styles?.[g]?.include!==false).sort((a,b)=>(cfg.styles?.[a]?.order??0)-(cfg.styles?.[b]?.order??0));
 const times=cfg.type==='line'?[...new Set(records.map(r=>r.timepoint))].sort((a,b)=>timeNumber(a)-timeNumber(b)):[cfg.timepoint||'endpoint'];
 if(cfg.type==='line'&&times.some(t=>t.trim()===''||!Number.isFinite(timeNumber(t))))throw Error('Time courses require numeric timepoints or ISO dates.');
 if(cfg.type==='line'&&times.some(t=>dateNumber(t)!==null)&&times.some(t=>dateNumber(t)===null))throw Error('Dates and numeric timepoints cannot be mixed.');
 const summaries=[];
 for(const g of groups)for(const tp of times){const roster=mice.filter(m=>(m[cfg.grouping]||'Not specified')===g),ids=new Set(roster.map(m=>m.mouse_id));const rows=records.filter(r=>ids.has(r.mouse_id)&&(cfg.type!=='line'||r.timepoint===tp));const active=rows.filter(r=>!byId.get(r.mouse_id).excluded&&r.value!==null);if(new Set(active.map(r=>r.mouse_id)).size!==active.length)throw Error('Multiple replicates of a mouse are mixed. Select one replicate.');const missing=roster.filter(m=>!m.excluded&&!active.some(r=>r.mouse_id===m.mouse_id)).length;
 const present=new Set(rows.map(r=>r.mouse_id));const missing_values=roster.filter(m=>!m.excluded&&present.has(m.mouse_id)&&!active.some(r=>r.mouse_id===m.mouse_id)).length;
 const ordered=active.map(r=>r.value).sort((a,b)=>a-b),mid=Math.floor(ordered.length/2);
 const median=ordered.length?(ordered[mid]+ordered[Math.floor((ordered.length-1)/2)])/2:null;
 const lower=ordered[Math.floor((ordered.length-1)/2)],upper=ordered[mid];
 const median_mouse_ids=active.filter(r=>r.value===lower||r.value===upper).map(r=>r.mouse_id).sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true}));
 const median_is_midpoint=ordered.length>0&&lower!==upper;
 const median_tied=median_mouse_ids.length>(median_is_midpoint?2:1);
 summaries.push({median,median_mouse_ids,median_is_midpoint,median_tied,group:g,timepoint:tp,...stats(active.map(r=>r.value)),missing,missing_values,unmeasured:missing-missing_values,excluded:roster.filter(m=>m.excluded).length,rows});}
 const coverage={measured:[],missing:[],unmeasured:[],excluded:[]};
 for(const mouse of mice.filter(m=>groups.includes(m[cfg.grouping]||'Not specified'))){const rows=records.filter(r=>r.mouse_id===mouse.mouse_id);coverage[mouse.excluded?'excluded':rows.some(r=>r.value!==null)?'measured':rows.length?'missing':'unmeasured'].push(mouse.mouse_id);}
 return {groups,times,summaries,byId,records,coverage};
}
function sampleRows(data,cfg){
 const records=rowsForPanel(data,cfg);
 const byMouse=new Map();for(const row of records){if(!byMouse.has(row.mouse_id))byMouse.set(row.mouse_id,[]);byMouse.get(row.mouse_id).push(row);}
 return data.mice.filter(m=>(!Array.isArray(cfg.scope_mouse_ids)||cfg.scope_mouse_ids.includes(m.mouse_id))&&(!Array.isArray(cfg.scope_experiments)||cfg.scope_experiments.includes(m.experiment))&&(!cfg.experiment||m.experiment===cfg.experiment)&&(!cfg.weeks||m.weeks===cfg.weeks)).map(mouse=>({mouse,rows:byMouse.get(mouse.mouse_id)||[]}));
}
function sampleTree(data,configs,{query='',showMissing=false}={}){
 const all=new Map(),q=query.trim().toLowerCase(),sort=(a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true});
 configs.forEach((cfg,index)=>sampleRows(data,cfg).forEach(s=>{if(!all.has(s.mouse.mouse_id))all.set(s.mouse.mouse_id,{mouse:s.mouse,panels:[]});all.get(s.mouse.mouse_id).panels.push({index,rows:s.rows});}));
 const experiments=new Map();
 for(const sample of all.values()){
  const m=sample.mouse,experiment=m.experiment||'Exp not specified',diet=m.diet||m.group_name||'Diet not specified';
  if(!showMissing&&!sample.panels.some(p=>p.rows.length))continue;
  if(q&&![experiment,diet,m.group_name,m.mouse_id].join(' ').toLowerCase().includes(q))continue;
  if(!experiments.has(experiment))experiments.set(experiment,new Map());
  const diets=experiments.get(experiment);if(!diets.has(diet))diets.set(diet,[]);diets.get(diet).push(sample);
 }
 return [...experiments].sort(([a],[b])=>sort(a,b)).map(([experiment,diets])=>({experiment,diets:[...diets].sort(([a],[b])=>sort(a,b)).map(([diet,samples])=>({diet,samples:samples.sort((a,b)=>sort(a.mouse.mouse_id,b.mouse.mouse_id))}))}));
}
function composeFigures(figures){
 if(!figures.length||figures.length>8)throw Error('Check the graphs before exporting.');
 const plotted=figures.map((figure,index)=>({figure,index})).filter(({figure,index})=>{
  if(figure?.error)throw Error('Graph '+(index+1)+': '+figure.message);
  return figure?.svg;
 });
 if(!plotted.length)throw Error('Select a metric with measurements in at least one graph before exporting.');
 const width=plotted.length===1?800:1600,height=Math.ceil(plotted.length/2)*640;
 const content=plotted.map(({figure,index},position)=>{const x=position%2*800,y=Math.floor(position/2)*640;return `<g><text x="${x+16}" y="${y+24}" font-family="Arial, sans-serif" font-size="20" font-weight="bold">${String.fromCharCode(65+index)}</text>${figure.svg.replace(/<svg\b[^>]*>/,tag=>tag.replace(/\s(?:width|height)="[^"]*"/g,'').replace('<svg ',`<svg x="${x}" y="${y+30}" width="800" height="600" `))}</g>`;}).join('');
 return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${plotted.length} graphs"><rect width="100%" height="100%" fill="white"/>${content}</svg>`;
}
function render(data,cfg){
 const metric=data.metrics.find(m=>m.id===Number(cfg.metric));if(!metric)return {svg:'',summary:[],message:'Import measurements, then select a column.'};
 const set=dataset(data,cfg),{times,summaries,byId}=set;const groups=set.groups.filter(g=>summaries.some(s=>s.group===g&&(s.n>0||(cfg.showExcluded&&s.rows.some(r=>r.value!==null)))));if(!groups.length)return {svg:'',summary:summaries.map(({rows,...s})=>s),set,coverage:set.coverage,message:'No measurements match the selected conditions.'};
 const weekly=cfg.type==='line'&&isWeight(metric),trend=weekly?(cfg.trend||'off'):'mean';
 const err=s=>cfg.error==='SEM'?s.sem:cfg.error==='SD'?s.sd:null;
 const values=summaries.flatMap(s=>[s.mean==null?null:s.mean-(err(s)||0),s.mean==null?null:s.mean+(err(s)||0),...s.rows.filter(r=>cfg.showExcluded||!byId.get(r.mouse_id).excluded).map(r=>r.value)]).filter(v=>v!==null);
 const observed=summaries.flatMap(s=>s.rows.filter(r=>r.value!==null&&(cfg.showExcluded||!byId.get(r.mouse_id).excluded)).map(r=>r.value));
 let lo=cfg.ymin===''||cfg.ymin==null?0:Number(cfg.ymin),hi=cfg.ymax===''||cfg.ymax==null?Math.max(1,...values)*1.12:Number(cfg.ymax);
 if(!Number.isFinite(lo)||!Number.isFinite(hi)||hi<=lo)throw Error('The Y-axis maximum must exceed the minimum.');
 if(observed.some(v=>v<lo)||values.some(v=>v>hi))throw Error('Individual values or error bars are outside the Y-axis range. Expand the range.');
 if(cfg.type==='bar'&&(lo>0||hi<0))throw Error('The Y-axis range must include zero for bar graphs.');
 const analysis=cfg.analysis||null;
 const annotations=comparisonLabels(analysis,cfg,groups);
 if(annotations.length>190)throw Error('Too many comparison brackets. Choose a narrower p-value threshold.');
 if(cfg.type==='line'&&annotations.length)throw Error('Comparison brackets are not supported for time courses. Use a single-timepoint graph.');
 const statisticalHeader=cfg.comparisonMode!=='none'&&analysis?.status==='ok'?formatP(analysis.anova.p,'ANOVA p')+' · Tukey-adjusted p-values':'';
 const W=Math.max(800,groups.length*(cfg.type==='line'?30:75)+140),fs=Math.max(10,Math.min(28,Number(cfg.font)||16));
 const title=cfg.title||metricTitle(metric),titleLines=wrapTitle(title,Math.floor((W-60)/((fs+5)*.6))),titleExtra=(titleLines.length-1)*(fs+7);
 const legendColumns=Math.max(1,Math.floor((W-145)/Math.max(130,...groups.map(g=>g.length*7+35)))),legendExtra=cfg.type==='line'?(Math.ceil(groups.length/legendColumns)-1)*24:0;
 const H=600+legendExtra+annotations.length*28+(statisticalHeader?30:0)+titleExtra,L=105,R=W-40,T=80+annotations.length*28+(statisticalHeader?30:0)+titleExtra,B=H-140-legendExtra;
 const y=v=>B-(v-lo)/(hi-lo)*(B-T),xGroup=i=>L+(R-L)*(i+.5)/groups.length;
 const minX=times.length?timeNumber(times[0]):0,maxX=times.length?timeNumber(times[times.length-1]):1,xTime=t=>L+25+(R-L-50)*(timeNumber(t)-minX)/(maxX-minX||1);
 const yt=cfg.ytitle||`${metric.name} (${metric.unit})`,clipId=`plot-clip-${W}-${H}-${T}`,clippedLowerErrorBars=summaries.filter(s=>s.mean!==null&&err(s)!==null&&s.mean-err(s)<lo).length;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title><defs><clipPath id="${clipId}"><rect x="${L-1}" y="${T-1}" width="${R-L+2}" height="${B-T+1}"/></clipPath></defs><rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif" fill="black" font-size="${fs}"><text x="${W/2}" y="32" text-anchor="middle" font-size="${fs+5}" font-weight="bold">${titleLines.map((line,i)=>`<tspan x="${W/2}" y="${32+i*(fs+7)}">${esc(line)}</tspan>`).join('')}</text>`;
 if(!data.synthetic)svg+=`<text x="${W/2}" y="${53+titleExtra}" text-anchor="middle" font-size="10">${esc([cfg.experiment,metric.organ,gateName(metric.gate),cfg.type==='line'?'time series':cfg.timepoint,'replicate '+cfg.replicate].filter(Boolean).join(' · '))}</text>`;
 if(statisticalHeader)svg+=`<text x="${W/2}" y="${74+titleExtra}" text-anchor="middle" font-size="12">${esc(statisticalHeader)}</text>`;
 if(data.synthetic)svg+=`<text x="${W/2}" y="${53+titleExtra}" text-anchor="middle" font-size="11">Synthetic example · Not research results</text>`;
 svg+=`<path d="M${L} ${T}V${B}H${R}" fill="none" stroke="black" stroke-width="2"/><text transform="translate(28 ${(T+B)/2}) rotate(-90)" text-anchor="middle" font-weight="bold">${esc(yt)}</text>`;
 for(let i=0;i<=5;i++){let v=lo+(hi-lo)*i/5,yy=y(v);svg+=`<path d="M${L-7} ${yy}H${L}" stroke="black" stroke-width="2"/><text x="${L-12}" y="${yy+fs*.3}" text-anchor="end">${Number(v.toPrecision(3))}</text>`;}
 const style=(g,i)=>({...defaultGroupStyle(g,i),...cfg.styles?.[g]});
 const bars=(s,cx,st)=>{if(s.mean===null)return '';const e=err(s);let out='';if(cfg.type==='bar')out+=`<rect x="${cx-22}" y="${Math.min(y(0),y(s.mean))}" width="44" height="${Math.abs(y(0)-y(s.mean))}" fill="${st.fill==='solid'?st.color:'white'}" fill-opacity="${st.fill==='solid'?'.35':'1'}" stroke="${st.color}" stroke-width="2"/>`;else if(cfg.type==='scatter')out+=`<path d="M${cx-20} ${y(s.mean)}H${cx+20}" stroke="${st.color}" stroke-width="2"/>`;
 if(e!==null)out+=`<path d="M${cx} ${y(s.mean-e)}V${y(s.mean+e)}M${cx-6} ${y(s.mean-e)}H${cx+6}M${cx-6} ${y(s.mean+e)}H${cx+6}" stroke="${st.color}" stroke-width="1.6" fill="none"/>`;return `<g clip-path="url(#${clipId})">${out}</g>`;};
 for(let i=0;i<groups.length;i++){const g=groups[i],st=style(g,i),ss=summaries.filter(s=>s.group===g);
 if(!/^#[0-9a-fA-F]{6}$/.test(st.color))st.color='#111111';
 if(cfg.type==='line'&&trend!=='off'){let path='',connected=false;for(const s of ss){if(s.mean===null){connected=false;continue;}path+=`${connected?'L':'M'}${xTime(s.timepoint)} ${y(trend==='median'?s.median:s.mean)} `;connected=true;}svg+=`<path d="${path}" fill="none" stroke="${st.color}" stroke-width="2"/>`;}
 for(const s of ss){const cx=cfg.type==='line'?xTime(s.timepoint):xGroup(i);svg+=bars(s,cx,st);
 if(cfg.type==='line'&&s.mean!==null){const central=weekly&&trend==='median'?s.median:s.mean;svg+=`<g data-timepoint="${esc(s.timepoint)}" tabindex="0" role="img" aria-label="${esc(g+' · '+s.timepoint+' · '+(weekly&&trend==='median'?'Median':'Mean')+': '+central+' · n='+s.n)}"><title>${esc(g)} · ${esc(s.timepoint)} · ${weekly&&trend==='median'?'Median':'Mean'}: ${Number(central.toPrecision(5))} ${esc(metric.unit)} · n=${s.n}</title>${marker(cx,y(central),st.shape,st.color,5,false)}</g>`;}
 s.rows.filter(r=>(!weekly||cfg.showIndividuals===true)&&r.value!==null&&(cfg.showExcluded||!byId.get(r.mouse_id).excluded)).forEach(r=>{const excluded=!!byId.get(r.mouse_id).excluded,hash=[...r.mouse_id].reduce((a,b)=>a*31+b.charCodeAt(0),0)>>>0,jitter=cfg.type==='line'?0:(hash%31-15);svg+=`<g data-mouse="${esc(r.mouse_id)}" role="button" tabindex="0" aria-label="Mouse ${esc(r.mouse_id)}, ${r.value} ${esc(metric.unit)}${excluded?', Excluded':''}"><title>Mouse ${esc(r.mouse_id)} · ${esc(r.timepoint)} · ${r.value} ${esc(metric.unit)}</title>${marker(cx+jitter,y(r.value),st.shape,excluded?'#999':st.color,cfg.type==='line'?3.1:4.5,excluded)}</g>`;});
 if(cfg.type!=='line'){const angle=-Number(cfg.angle||0);svg+=`<path d="M${cx} ${B}V${B+6}" stroke="black" stroke-width="2"/><text transform="translate(${cx} ${B+23}) rotate(${angle})" text-anchor="${angle?'end':'middle'}">${esc(g)}</text><text x="${cx}" y="${H-38}" text-anchor="middle" font-size="11">n=${s.n}</text>`;}}
 if(cfg.type==='line')svg+=`${marker(L+10+(i%legendColumns)*((R-L)/legendColumns),B+95+Math.floor(i/legendColumns)*24,st.shape,st.color,4)}<text x="${L+20+(i%legendColumns)*((R-L)/legendColumns)}" y="${B+100+Math.floor(i/legendColumns)*24}" font-size="12">${esc(g)}</text>`;
 }
 if(cfg.type==='line'){
  const dated=times.some(t=>dateNumber(t)!==null),gap=dated?105:55;let last=-Infinity;
  const labelled=new Set();
  times.forEach((t,i)=>{const x=xTime(t),end=xTime(times[times.length-1]);if(i===0||i===times.length-1||(x-last>=gap&&end-x>=gap)){labelled.add(t);last=x;}});
  for(const t of times){const x=xTime(t),major=labelled.has(t);svg+=`<path data-axis-timepoint="${esc(t)}" d="M${x} ${B}V${B+(major?7:4)}" stroke="black" stroke-width="${major?1.5:1}"><title>${esc(t)}</title></path>`;if(major)svg+=`<text x="${x}" y="${B+25}" text-anchor="middle">${esc(t)}</text>`;}
  svg+=`<text x="${(L+R)/2}" y="${B+55}" text-anchor="middle" font-weight="bold">${esc(cfg.xtitle||(dated?'Date':weekly?'Week':'Time (min)'))}</text>`;
 }

 annotations.forEach((a,i)=>{const x1=xGroup(groups.indexOf(a[0])),x2=xGroup(groups.indexOf(a[1])),yy=(statisticalHeader?100:70)+i*28+titleExtra;svg+=`<path d="M${x1} ${yy+5}V${yy}H${x2}V${yy+5}" stroke="black" stroke-width="1.5" fill="none"/><text x="${(x1+x2)/2}" y="${yy-5}" text-anchor="middle" font-size="14">${esc(a[2])}</text>`;});
 svg+=`<text x="${R}" y="${H-12}" text-anchor="end" font-size="10">${weekly?(times.some(t=>dateNumber(t)!==null)?'Date trend: ':'Weekly trend: ')+trend+' · ':''}Mean${cfg.error==='none'?'':' ± '+cfg.error} · ${weekly&&cfg.showIndividuals!==true?'Individual values hidden':'one mouse per point'}${cfg.comparisonMode!=='none'&&analysis?.status==='ok'?' · '+esc(analysis.method)+' · adjusted p':''}${clippedLowerErrorBars?' · error bars below '+lo+' not shown':''}</text></g></svg>`;
 const axis={min:lo,max:hi,clippedLowerErrorBars,negativeMeasurements:observed.filter(v=>v<0).length,errorBelowZero:summaries.some(s=>s.mean!==null&&err(s)!==null&&s.mean-err(s)<0)};
 return {svg,summary:summaries.map(({rows,...s})=>s),set,title,analysis,coverage:set.coverage,axis};
}
const api={isWeight,weekNumber,dateNumber,metricChoices,stats,dataset,render,esc,gateName,sampleRows,sampleTree,composeFigures,groupKey,defaultGroupStyle,referencePalette,formatP,comparisonLabels,moveGroup,metricTitle};if(typeof module!=='undefined')module.exports=api;else root.Figure=api;
})(typeof window!=='undefined'?window:globalThis);
