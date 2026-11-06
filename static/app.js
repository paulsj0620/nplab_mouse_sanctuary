'use strict';
const $=s=>document.querySelector(s),esc=Figure.esc;let user=null,setup=false,data=null,audit=[],stage=null,example=false,lastFigure=null,styles=Object.create(null),editing=null,pageIndex=0,presetVersion=null,busy=false;
const colors=['#111111','#ff176d','#008c88','#55bce8','#65089c','#ae5cff'];
async function api(path,method='GET',body){const r=await fetch('/api'+path,{method,headers:method==='GET'?{}:{'Content-Type':'application/json','X-CSRF-Token':user?.csrf||''},body:body===undefined?undefined:JSON.stringify(body)});const d=await r.json();if(!r.ok){if(r.status===401&&path!=='/login')location.reload();const error=new Error(d.error||'Request failed');error.status=r.status;throw error}return d;}
function notice(s){$('#message').hidden=false;$('#message').textContent=s;}
function download(name,content,type='text/plain;charset=utf-8'){const u=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),3000)}
function csv(rows,keys){const cell=v=>{let s=v==null?'':String(v);if(typeof v==='string'&&/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"'};return '\uFEFF'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(cell).join(',')).join('\r\n')}
function options(el,values,empty='',previous=el.value){el.innerHTML=(empty?`<option value="">${empty}</option>`:'')+values.map(v=>typeof v==='object'?`<option value="${esc(v.value)}">${esc(v.label)}</option>`:`<option value="${esc(v)}">${esc(v||'Not specified')}</option>`).join('');if([...el.options].some(o=>o.value===previous))el.value=previous;}
let graphStudy='all',comparisonIds=null;
const comparisonBranches=new Map(),comparisonOpen=new Map();
function studyMouseIds(){const d=example?demo:data;if(!d)return [];return d.mice.filter(m=>example||comparisonIds===null||comparisonIds.has(m.mouse_id)).map(m=>m.mouse_id);}
function studyExperiments(){const ids=new Set(studyMouseIds());return [...new Set((example?demo:data).mice.filter(m=>ids.has(m.mouse_id)).map(m=>m.experiment))];}
function current(){const d=example?demo:data;if(!d||example||!sampleChanges.size)return d;return {...d,mice:d.mice.map(m=>sampleChanges.has(m.mouse_id)?{...m,excluded:Number(!sampleChanges.get(m.mouse_id).included)}:m)};}
function renderStudyTabs(){$('#graph-selection-status').textContent='Current selection: '+({all:'All experiments',basic:'Basic diet',di:'Dietary Intervention',custom:'Custom selection'}[graphStudy]||'Custom selection');for(const button of document.querySelectorAll('[data-study]'))button.setAttribute('aria-pressed',String(button.dataset.study===graphStudy));$('#graph-study-note').textContent='Quick selection sets the starting comparison. All experiments remain available on the right, including unclassified experiments and mice without measurements. Comparison selection does not change saved exclusions.';}
function comparisonChanged(){for(const panel of panels){panel.experiment='';panel.weeks='';}$('#experiment').value='';$('#weeks').value='';renderStudyTabs();renderGraph(false);}
function switchStudy(next){if(example)return;rememberPanel();graphStudy=next;comparisonIds=next==='all'?null:new Set(StudyScope.selection(data,next));comparisonChanged();}
document.querySelectorAll('[data-study]').forEach(button=>button.onclick=()=>switchStudy(button.dataset.study));
function renderComparison(){if(!data||!panels[activePanel])return;const d=current(),selected=new Set(studyMouseIds());for(const el of $('#comparison-tree').querySelectorAll('[data-comparison-open]'))comparisonOpen.set(el.dataset.comparisonOpen,el.open);comparisonBranches.clear();const cfg={...panels[activePanel],scope_mouse_ids:undefined,scope_experiments:undefined,experiment:'',weeks:''};const tree=Figure.sampleTree(d,[cfg],{query:$('#comparison-search').value,showMissing:true});
 const measured=s=>s.panels.some(p=>p.rows.some(r=>r.value!==null));
 const leaf=s=>`<label class="sample-row"><input type="checkbox" data-comparison-mouse="${esc(s.mouse.mouse_id)}" aria-label="Compare mouse ${esc(s.mouse.mouse_id)}" ${selected.has(s.mouse.mouse_id)?'checked':''} ${example?'disabled':''}><span>Mouse ${esc(s.mouse.mouse_id)}</span><small>${!measured(s)?'No data for current metric':s.mouse.excluded?'Globally excluded':''}</small></label>`;
 const branch=(name,key,samples,body)=>{const id=String(comparisonBranches.size);comparisonBranches.set(id,samples.map(s=>s.mouse.mouse_id));const n=samples.filter(s=>selected.has(s.mouse.mouse_id)).length;return `<details class="sample-branch" data-comparison-open="${esc(key)}" ${comparisonOpen.get(key)||$('#comparison-search').value?'open':''}><summary><input type="checkbox" data-comparison-branch="${id}" aria-label="Compare ${esc(name)}" ${n===samples.length?'checked':''} ${n>0&&n<samples.length?'data-mixed="true"':''} ${example?'disabled':''}><span>${esc(name)}</span><small>${n}/${samples.length}${samples.some(measured)?'':' · No data for current metric'}</small></summary>${body}</details>`;};
 $('#comparison-tree').innerHTML=tree.map(e=>{const samples=e.diets.flatMap(g=>g.samples),ages=[...new Set(samples.map(s=>s.mouse.weeks).filter(Boolean))],type=data.experiment_types?.[e.experiment],label=e.experiment+(ages.length?' · '+ages.join('/')+' Weeks':'')+' · '+(type==='di'?'DI':type==='basic'?'Basic diet':'Unclassified');return branch(label,JSON.stringify([e.experiment]),samples,e.diets.map(g=>branch(g.diet,JSON.stringify([e.experiment,g.diet]),g.samples,g.samples.map(leaf).join(''))).join(''));}).join('')||'<p>No matching samples.</p>';
 for(const el of $('#comparison-tree').querySelectorAll('[data-mixed]')){el.indeterminate=true;el.setAttribute('aria-checked','mixed');}
 $('#comparison-status').textContent=`${selected.size} of ${d.mice.length} mice selected for comparison. Plotted N also depends on measurements, saved exclusions and graph filters.`;
}
$('#comparison-search').oninput=renderComparison;
$('#comparison-tree').onchange=event=>{if(example)return;const input=event.target.closest('[data-comparison-mouse],[data-comparison-branch]');if(!input)return;rememberPanel();comparisonIds=new Set(studyMouseIds());const ids=input.dataset.comparisonMouse?[input.dataset.comparisonMouse]:(comparisonBranches.get(input.dataset.comparisonBranch)||[]);for(const id of ids)if(input.checked)comparisonIds.add(id);else comparisonIds.delete(id);graphStudy='custom';comparisonChanged();};
$('#comparison-tree').onclick=event=>{if(event.target.matches('input'))event.stopPropagation();};

const demo={synthetic:true,mice:[],metrics:[{id:1,name:'Live cells',unit:'%',organ:'Liver',gate:'Live cells',parent_gate:'All cells',denominator:'all cells'}],measurements:[]};
['Chow diet','Western diet','TRF6:18','TRF10:14','ADF','RC'].forEach((g,i)=>{for(let n=0;n<8;n++){const id=`DEMO-${i+1}-${n+1}`;demo.mice.push({mouse_id:id,group_name:g,diet:g,experiment:'Synthetic',weeks:'',excluded:0});demo.measurements.push({id:i*8+n,mouse_id:id,metric_id:1,timepoint:'endpoint',replicate:'1',value:+([69,61,72,22,54,53][i]+Math.sin(n*2+i)*[8,14,6,4,25,25][i]).toFixed(2)});}});
const sampleChanges=new Map(),sampleBranches=new Map(),treeOpen=new Map();let treeSearchWasActive=false;
function currentTree(){return Figure.sampleTree(current(),panelConfigs(),{query:$('#sample-search').value,showMissing:$('#sample-show-missing').checked});}
function visibleSamples(){return currentTree().flatMap(exp=>exp.diets.flatMap(diet=>diet.samples));}
function renderSamples(){if(!data)return;const tree=currentTree(),samples=tree.flatMap(exp=>exp.diets.flatMap(diet=>diet.samples)),included=s=>sampleChanges.get(s.mouse.mouse_id)?.included??!s.mouse.excluded;
 if(!treeSearchWasActive)for(const detail of $('#sample-list').querySelectorAll('[data-tree-key]'))treeOpen.set(detail.dataset.treeKey,detail.open);treeSearchWasActive=!!$('#sample-search').value.trim();sampleBranches.clear();
 const branch=(label,key,children,content,weeks='')=>{const id=String(sampleBranches.size),n=children.filter(included).length;sampleBranches.set(id,children);const open=$('#sample-search').value.trim()||treeOpen.get(key)===true;return `<details class="sample-branch" data-tree-key="${esc(key)}" ${open?'open':''}><summary><input type="checkbox" data-sample-branch="${id}" aria-label="${esc(JSON.parse(key).join(' · '))} Include all" title="Apply to the ${children.length} visible mice in this branch" ${n===children.length?'checked':''} ${n>0&&n<children.length?'data-partial="true"':''} ${example||busy?'disabled':''}><span>${esc(label)}</span>${weeks?`<span class="exp-weeks">${esc(weeks)}</span>`:''}<small>${n}/${children.length}</small></summary><div class="sample-children">${content}</div></details>`;};
 const leaf=s=>{const m=s.mouse,on=included(s),measured=s.panels.filter(p=>p.rows.some(r=>r.value!==null)).length,recorded=s.panels.some(p=>p.rows.length);return `<label class="sample-row ${on?'':'is-excluded'}"><input type="checkbox" data-sample-select="${esc(m.mouse_id)}" aria-label="Mouse ${esc(m.mouse_id)} Included" ${on?'checked':''} ${example||busy?'disabled':''}><span class="sample-name">Mouse ${esc(m.mouse_id)}</span><span class="sample-value">${measured?measured+' graphs':recorded?'Missing':'Unmeasured'}</span></label>`;};
 $('#sample-count').textContent=`${samples.length} mice · Included ${samples.filter(included).length} · Excluded ${samples.filter(s=>!included(s)).length}`;
 $('#sample-list').innerHTML=tree.map(exp=>{const children=exp.diets.flatMap(d=>d.samples),content=exp.diets.map(diet=>branch(diet.diet,JSON.stringify([exp.experiment,diet.diet]),diet.samples,diet.samples.map(leaf).join(''))).join('');const members=current().mice.filter(m=>(m.experiment||'Exp not specified')===exp.experiment),weeks=[...new Set(members.map(m=>String(m.weeks||'').trim()).filter(Boolean))].sort((a,b)=>Number(a)-Number(b)),intervention=members.some(m=>[m.diet,m.group_name].some(g=>/\b(?:ADF|RC|Reverse|TRF)/i.test(String(g||''))));const label=[weeks.length?weeks.join(' / ')+' Weeks':'',intervention?'Dietary Intervention':''].filter(Boolean).join(' / ');return branch(exp.experiment,JSON.stringify([exp.experiment]),children,content,label);}).join('')||'<div class="sample-empty">No samples to display.</div>';
 for(const input of $('#sample-list').querySelectorAll('[data-partial]')){input.indeterminate=true;input.setAttribute('aria-checked','mixed');}
 $('#sample-pending').textContent=example?'Sample selections cannot be saved in the synthetic example.':sampleChanges.size?`${sampleChanges.size} mice with unsaved changes · Previewing across all graphs`:'';
 for(const id of ['samples-save','samples-cancel'])$('#'+id).disabled=example||busy||!sampleChanges.size;
 for(const id of ['samples-include','samples-exclude'])$('#'+id).disabled=example||busy||!samples.length;
}
function chooseSample(id,included){const mouse=data.mice.find(m=>m.mouse_id===id);if(!mouse)return;if(included===!mouse.excluded)sampleChanges.delete(id);else sampleChanges.set(id,{mouse_id:id,version:sampleChanges.get(id)?.version??mouse.version,included});}
$('#sample-search').oninput=renderSamples;$('#sample-show-missing').onchange=renderSamples;
$('#sample-list').onchange=event=>{if(example||busy)return;const branch=event.target.closest('[data-sample-branch]'),input=event.target.closest('[data-sample-select]');if(branch)(sampleBranches.get(branch.dataset.sampleBranch)||[]).forEach(s=>chooseSample(s.mouse.mouse_id,branch.checked));else if(input)chooseSample(input.dataset.sampleSelect,input.checked);else return;renderGraph(false);};
$('#sample-list').addEventListener('click',event=>{if(event.target.matches('input[type=checkbox]'))event.stopPropagation();});
for(const [id,included] of [['samples-include',true],['samples-exclude',false]])$('#'+id).onclick=()=>{if(example||busy)return;visibleSamples().forEach(s=>chooseSample(s.mouse.mouse_id,included));renderGraph(false);};
$('#samples-cancel').onclick=()=>{sampleChanges.clear();$('#sample-reason').value='';renderGraph(false);};
$('#samples-save').onclick=async()=>{if(example||busy||!sampleChanges.size)return;const reason=$('#sample-reason').value.trim();if(!reason){notice('Enter a reason for changing sample inclusion.');$('#sample-reason').focus();return;}try{busy=true;renderSamples();const result=await api('/mice/inclusion','POST',{reason,changes:[...sampleChanges.values()]});sampleChanges.clear();$('#sample-reason').value='';await sync(true);renderGraph(false);notice(`Saved inclusion status for ${result.updated.length} mice across all graphs and metrics.`);}catch(error){if(error.status===409){sampleChanges.clear();await sync(true);renderGraph(false);}notice(error.message);}finally{busy=false;renderSamples();}};

function fullMetricLabel(m){return [m.name,m.organ,m.gate,m.parent_gate?'parent: '+m.parent_gate:'',`(${m.unit}${m.denominator?' / '+m.denominator:''})`].filter(Boolean).join(' · ')}
function metricLabel(m){if(!m)return 'No measurements';const name=m.name.startsWith('Freq. of Parent')?'Frequency · '+m.name:m.name.startsWith('Geometric Mean (')?'MFI · '+m.name:m.name;return [name,m.organ,Figure.gateName(m.gate),`(${m.unit})`].filter(Boolean).join(' · ')}
let panels=[],activePanel=0,graphCount=4,boardResults=[];
const boardCache=Object.create(null);
const analysisCache=new Map();let statisticsTimer=null,statisticsFetching=false;
let groupPalette=Object.create(null),sharedGroups=defaultSharedGroups(),availableGroupKeys=new Set(),draggedGroup=null;
function defaultSharedGroups(){return Object.assign(Object.create(null),Object.fromEntries(Figure.referencePalette.map((p,i)=>[p.key,{color:p.color,shape:p.shape,fill:p.fill,include:true,order:i+1}])));}
function sharedGroup(key){if(key==='Not specified'&&!Object.hasOwn(sharedGroups,key)&&Object.hasOwn(sharedGroups,'미기재'))sharedGroups[key]={...sharedGroups['미기재']};if(!Object.hasOwn(sharedGroups,key)){const base=Figure.defaultGroupStyle(key);sharedGroups[key]={color:groupPalette[key]||base.color,shape:base.shape,fill:base.fill,include:true,order:Object.keys(sharedGroups).length+1};}return sharedGroups[key];}
function initialStyle(group){const value=sharedGroup(Figure.groupKey(group));return {color:value.color,shape:value.shape,fill:value.fill,order:value.order};}
function syncGroupStyles(){availableGroupKeys=new Set();panels.forEach((panel,index)=>{const samples=Figure.sampleRows(current(),panel),groups=new Map();for(const sample of samples){const group=sample.mouse[panel.grouping]||'Not specified';groups.set(group,(groups.get(group)||false)||sample.rows.length>0);}const next=Object.create(null);for(const [group,available] of groups){const key=Figure.groupKey(group),setting=sharedGroup(key);next[group]={...initialStyle(group),include:setting.include&&available};if(available&&index<graphCount)availableGroupKeys.add(key);}panel.styles=next;});styles=Object.assign(Object.create(null),structuredClone(panels[activePanel].styles));}
function visibleGroupKeys(){return Object.keys(sharedGroups).filter(key=>Figure.referencePalette.some(p=>p.key===key)||availableGroupKeys.has(key)).sort((a,b)=>sharedGroups[a].order-sharedGroups[b].order);}
function renderPalette(){const keys=visibleGroupKeys(),existing=[...$('#global-colors').querySelectorAll('[data-global-group]')];if(existing.length===keys.length&&existing.every((card,i)=>card.dataset.globalGroup===keys[i])){for(const [i,key] of keys.entries()){const card=existing[i],value=sharedGroup(key);card.querySelector('.group-position').textContent=i+1;card.querySelector('[data-palette-key]').value=value.color;const text=card.querySelector('[data-palette-hex]');if(document.activeElement!==text)text.value=value.color;card.querySelector('[data-global-style="include"]').checked=value.include;for(const field of ['shape','fill'])card.querySelector(`[data-global-style="${field}"]`).value=value[field];}return;}
 $('#global-colors').innerHTML=keys.map((key,i)=>{const value=sharedGroup(key);return `<div class="global-group-card" data-global-group="${esc(key)}"><div class="global-group-head"><button type="button" class="group-drag" draggable="true" data-group-drag="${esc(key)}" aria-label="${esc(key)} Reorder" title="Drag or use arrow keys to reorder">≡</button><span class="group-position">${i+1}</span><label><input type="checkbox" data-global-style="include" aria-label="${esc(key)} Show group" ${value.include?'checked':''}><b>${esc(key)}</b></label></div><div class="group-color"><input type="color" data-palette-key="${esc(key)}" aria-label="${esc(key)} Color" value="${esc(value.color)}"><input type="text" data-palette-hex="${esc(key)}" aria-label="${esc(key)} Color code" value="${esc(value.color)}" maxlength="7" spellcheck="false"></div><label>Symbol<select data-global-style="shape" aria-label="${esc(key)} Symbol">${[['square','Square'],['triangle','Triangle'],['down','Inverted triangle'],['diamond','Diamond'],['circle','Circle']].map(([shape,label])=>`<option value="${shape}" ${value.shape===shape?'selected':''}>${label}</option>`).join('')}</select></label><label>Bar<select data-global-style="fill" aria-label="${esc(key)} Bar fill"><option value="solid" ${value.fill==='solid'?'selected':''}>Filled</option><option value="outline" ${value.fill==='outline'?'selected':''}>Outline</option></select></label></div>`;}).join('');}
function setGroupColor(key,color){if(!/^#[0-9a-f]{6}$/i.test(color)){notice('Enter a color in #RRGGBB format.');return;}groupPalette[key]=color;sharedGroup(key).color=color;renderGraph(false);}
$('#global-colors').onchange=event=>{const input=event.target.closest('[data-palette-key],[data-palette-hex],[data-global-style]');if(!input)return;const card=input.closest('[data-global-group]'),key=card.dataset.globalGroup;if(input.dataset.globalStyle){sharedGroup(key)[input.dataset.globalStyle]=input.type==='checkbox'?input.checked:input.value;renderGraph(false);}else setGroupColor(key,input.value);};
$('#global-colors').oninput=event=>{const input=event.target.closest('[data-palette-key],[data-palette-hex]');if(input&&/^#[0-9a-f]{6}$/i.test(input.value))setGroupColor(input.dataset.paletteKey||input.dataset.paletteHex,input.value);};
$('#palette-reset').onclick=()=>{groupPalette=Object.create(null);for(const key of Object.keys(sharedGroups))sharedGroups[key].color=Figure.defaultGroupStyle(key).color;renderGraph(false);notice('Default colors applied to all graphs.');};
function reorderSharedGroup(source,target,after){const ordered=Figure.moveGroup(Object.keys(sharedGroups).sort((a,b)=>sharedGroups[a].order-sharedGroups[b].order),source,target,after);ordered.forEach((key,i)=>sharedGroups[key].order=i+1);renderGraph(false);$('#group-order-status').textContent=`Group order: ${visibleGroupKeys().join(' → ')}`;const handle=[...$('#global-colors').querySelectorAll('[data-group-drag]')].find(el=>el.dataset.groupDrag===source);handle?.focus();}
$('#global-colors').addEventListener('dragstart',event=>{const handle=event.target.closest('[data-group-drag]');if(!handle){event.preventDefault();return;}draggedGroup=handle.dataset.groupDrag;event.dataTransfer.setData('text/plain',draggedGroup);event.dataTransfer.effectAllowed='move';});
$('#global-colors').addEventListener('dragover',event=>{const card=event.target.closest('[data-global-group]');if(!card||!draggedGroup)return;event.preventDefault();event.dataTransfer.dropEffect='move';});
$('#global-colors').addEventListener('drop',event=>{const card=event.target.closest('[data-global-group]');if(!card||!draggedGroup)return;event.preventDefault();const rect=card.getBoundingClientRect(),source=draggedGroup;draggedGroup=null;reorderSharedGroup(source,card.dataset.globalGroup,event.clientX>rect.left+rect.width/2);});
$('#global-colors').addEventListener('dragend',()=>{draggedGroup=null;});
$('#global-colors').addEventListener('keydown',event=>{const handle=event.target.closest('[data-group-drag]');if(!handle||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;event.preventDefault();const keys=visibleGroupKeys(),index=keys.indexOf(handle.dataset.groupDrag),next=index+(['ArrowRight','ArrowDown'].includes(event.key)?1:-1);if(next>=0&&next<keys.length)reorderSharedGroup(keys[index],keys[next],next>index);});

function analysisInput(panel){return {scope_mouse_ids:studyMouseIds(),scope_experiments:studyExperiments(),metric:panel.metric,type:panel.type,experiment:panel.experiment,weeks:panel.weeks,grouping:panel.grouping,timepoint:panel.timepoint,replicate:panel.replicate,styles:Object.fromEntries(Object.entries(panel.styles||{}).map(([g,s])=>[g,{include:s.include,order:s.order}]))};}
function analysisKey(panel){const input=analysisInput(panel);return JSON.stringify({revision:data.revision,...input,styles:Object.fromEntries(Object.entries(input.styles).sort(([a],[b])=>a.localeCompare(b)).map(([g,s])=>[g,s.include])),selection:[...sampleChanges.values()].sort((a,b)=>a.mouse_id.localeCompare(b.mouse_id))});}
function panelAnalysis(panel){if(!panel.metric)return {status:'unavailable',message:''};if(panel.statMode!=='anova-tukey')return null;if(example)return {status:'unavailable',message:'Research p-values are not calculated for synthetic examples.'};const state=analysisCache.get(analysisKey(panel));return state?.result||{status:state?.error?'unavailable':'pending',message:state?.error||'Calculating p-values…'};}
function queueStatistics(){if(example||statisticsFetching)return;clearTimeout(statisticsTimer);statisticsTimer=setTimeout(async()=>{const pending=new Map();for(const panel of panelConfigs())if(panel.metric&&panel.statMode==='anova-tukey'){const key=analysisKey(panel);if(!analysisCache.has(key))pending.set(key,analysisInput(panel));}if(!pending.size)return;statisticsFetching=true;for(const key of pending.keys())analysisCache.set(key,{loading:true});try{const response=await api('/analyze','POST',{revision:data.revision,panels:[...pending].map(([key,config])=>({key,config})),sample_selection:[...sampleChanges.values()]});for(const row of response.results)if(pending.has(row.key))analysisCache.set(row.key,{result:row.result});}catch(error){for(const key of pending.keys())analysisCache.set(key,{error:error.message});if(error.status===409&&!sampleChanges.size)await sync(true);}finally{statisticsFetching=false;renderGraph(false);}},250);}
function renderStatistics(){const panel=panels[activePanel],analysis=panelAnalysis(panel);if(panel.comparisonMode==='none'){$('#statistics-table').innerHTML='<p>P-values are hidden on the graph. Calculated results remain in the statistics CSV.</p>';return;}if(analysis?.status!=='ok'){$('#statistics-table').innerHTML=analysis?`<p>${esc(analysis.message)}</p>`:'';return;}const pairs=Figure.comparisonLabels(analysis,panel,analysis.groups.map(g=>g.group));$('#statistics-table').innerHTML=`<p><b>${esc(analysis.method)}</b><br>${esc(Figure.formatP(analysis.anova.p,'ANOVA p'))} · F=${Number(analysis.anova.f.toPrecision(4))} · df=${analysis.anova.df_between}, ${analysis.anova.df_within}</p><p class="help">Showing ${pairs.length} of ${analysis.pairs.length} pairs · CSV includes all results</p>`+(pairs.length?`<div class="table-scroll">${table(['Comparison','Tukey-adjusted p'],pairs.map(pair=>[esc(pair[0]+' / '+pair[1]),esc(pair[2])]))}</div>`:'<p>No comparison pairs meet this threshold.</p>');}
$('#statistics-retry').onclick=()=>{if(!example&&panels[activePanel])analysisCache.delete(analysisKey(panels[activePanel]));renderGraph(false);};
$('#stats-panel').addEventListener('toggle',()=>{if($('#stats-panel').open)renderStatistics();});
$('#statistics-csv').onclick=()=>{const rows=[];boardResults.forEach((figure,index)=>{const result=figure.analysis;if(result?.status!=='ok')return;result.pairs.forEach(pair=>rows.push({panel:index+1,metric_id:panels[index].metric,method:result.method,anova_f:result.anova.f,anova_p:result.anova.p,group_a:pair.a,n_a:result.groups.find(g=>g.group===pair.a).n,group_b:pair.b,n_b:result.groups.find(g=>g.group===pair.b).n,p_adjusted:pair.p_adjusted,mean_difference:pair.mean_difference,correction_scope:result.correction_scope,data_sha256:result.data_sha256,revision:result.revision,selection_preview:result.preview,engine:result.engine}));});if(!rows.length)return notice('No completed statistical results are available.');download('anova-tukey-results.csv',csv(rows,Object.keys(rows[0])),'text/csv');};

function newPanel(metric){const d=current(),groups=[...new Set(d.mice.map(m=>m.group_name||'Not specified'))],ids=new Set(d.measurements.filter(r=>r.metric_id===metric?.id).map(r=>r.mouse_id)),weekly=Figure.isWeight(metric)&&d.measurements.some(r=>r.metric_id===metric.id&&Number.isFinite(r.value)&&Figure.weekNumber(r.timepoint)!==null),line=weekly||/OGTT|ITT/i.test(metric?.name||'');const panelStyles=Object.create(null);groups.forEach((g,i)=>panelStyles[g]={include:d.mice.some(m=>(m.group_name||'Not specified')===g&&ids.has(m.mouse_id)),...initialStyle(g,i)});const records=d.measurements.filter(r=>r.metric_id===metric?.id);return {metric:String(metric?.id||''),experiment:'',weeks:'',grouping:'group_name',timepoint:records[0]?.timepoint||'endpoint',replicate:records[0]?.replicate||'1',type:line?'line':'bar',error:'SEM',title:'',ytitle:'',xtitle:weekly?'Week':'Time (min)',ymin:'0',ymax:'',font:18,angle:'45',showExcluded:false,statMode:'anova-tukey',comparisonMode:'p05',styles:panelStyles};}
function hasRecordedValue(row){return Number.isFinite(row.value);}
function graphMetrics(dataset){
 const observed=new Set(dataset.measurements.filter(hasRecordedValue).map(row=>row.metric_id));
 return dataset.metrics.filter(metric=>observed.has(metric.id));
}
function ensurePanels(){const metrics=graphMetrics(current()),preferred=[metrics.find(m=>m.name==='Absolute Count'&&Figure.gateName(m.gate)==='Live cells'),metrics.find(m=>m.name.startsWith('Freq. of Parent')&&Figure.gateName(m.gate)==='Live cells'),metrics.find(m=>m.name==='Geometric Mean (CD3)'),metrics.find(m=>m.name==='Absolute Count'&&Figure.gateName(m.gate)==='CD3+')].filter(Boolean),ordered=[...preferred,...metrics.filter(m=>m.gate),...metrics];const unique=[...new Map(ordered.map(m=>[m.id,m])).values()];for(let i=0;i<8;i++){if(!panels[i]||panels[i].metric&&!metrics.some(m=>String(m.id)===String(panels[i].metric)))panels[i]=newPanel(unique[i]);panels[i].statMode='anova-tukey';if(panels[i].ymin===''||panels[i].ymin==null)panels[i].ymin='0';panels[i].comparisonMode=panels[i].comparisonMode==='significant'?'p05':['none','all','p10','p05'].includes(panels[i].comparisonMode)?panels[i].comparisonMode:'p05';delete panels[i].referenceGroup;delete panels[i].annotations;delete panels[i].annotationMethod;}graphCount=Math.max(1,Math.min(8,Number(graphCount)||4));activePanel=Math.max(0,Math.min(graphCount-1,activePanel));}
function rememberPanel(){if(panels[activePanel])panels[activePanel]=structuredClone(cfg());}
function panelConfigs(){return panels.slice(0,graphCount);}
function restorePanelControls(){const c=panels[activePanel];if(!c)return;styles=Object.assign(Object.create(null),structuredClone(c.styles||{}));$('#weight-trend').value=c.trend||'off';const fields={metric:'metric',experiment:'experiment',weeks:'weeks',grouping:'grouping',type:'chart-type',error:'error-type',title:'plot-title',ytitle:'y-title',xtitle:'x-title',ymin:'y-min',ymax:'y-max',font:'font-size',angle:'angle',comparisonMode:'comparison-mode'};for(const [key,id] of Object.entries(fields))if(c[key]!==undefined)$('#'+id).value=c[key];updateTime();if([...$('#timepoint').options].some(o=>o.value===c.timepoint))$('#timepoint').value=c.timepoint;if([...$('#replicate').options].some(o=>o.value===c.replicate))$('#replicate').value=c.replicate;$('#show-excluded').checked=!!c.showExcluded;$('#active-graph').value=String(activePanel);$('#graph-count').value=String(graphCount);$('#active-graph-label').textContent=`Graph ${activePanel+1}`;}
function focusPanel(index){if(index===activePanel)return;rememberPanel();activePanel=index;restorePanelControls();renderGraph();}
function changePanelMetric(index,metricId,view=''){if(index===activePanel)rememberPanel();const metric=current().metrics.find(m=>m.id===Number(metricId));panels[index]=newPanel(metric);
 if(view==='weekly'){panels[index].type='line';panels[index].xtitle='Week';}
 if(view==='endpoint'){panels[index].type='bar';panels[index].timepoint=current().measurements.find(r=>r.metric_id===metric.id&&Number.isFinite(r.value)&&Figure.weekNumber(r.timepoint)===null)?.timepoint||'endpoint';}
 activePanel=index;restorePanelControls();renderGraph();}
function boardConfig(){rememberPanel();return {...cfg(),dashboard:{study:graphStudy,comparisonIds:comparisonIds===null?null:[...comparisonIds],panels:structuredClone(panels),count:graphCount,active:activePanel,palette:structuredClone(groupPalette),groupSettings:structuredClone(sharedGroups)}};}
function switchExample(next){rememberPanel();boardCache[example?'demo':'real']={panels,activePanel,graphCount,groupPalette,sharedGroups};example=next;const saved=boardCache[example?'demo':'real'];panels=saved?.panels||[];activePanel=saved?.activePanel||0;graphCount=saved?.graphCount||4;groupPalette=saved?.groupPalette||Object.create(null);sharedGroups=saved?.sharedGroups||defaultSharedGroups();$('#example').textContent=example?'Return to study data':'Preview with example data';populate();}
function renderGraph(rebuild=true){if(!data)return;rememberPanel();for(const panel of panels){panel.scope_experiments=studyExperiments();panel.scope_mouse_ids=studyMouseIds();}syncGroupStyles();const d=current();boardResults=[];const availableMetrics=graphMetrics(d);const choiceLabel=panel=>{const m=d.metrics.find(m=>String(m.id)===panel.metric);return m?metricLabel(m):(availableMetrics.length?'Select a metric':'No measurements');};
 $('#choose-metric').textContent=choiceLabel(panels[activePanel]);$('#choose-metric').disabled=!availableMetrics.length;
 $('#weekly-trend').hidden=!(Figure.isWeight(d.metrics.find(m=>String(m.id)===panels[activePanel].metric))&&panels[activePanel].type==='line');
 $('#figure').innerHTML=panelConfigs().map((panel,index)=>{let figure;try{figure=Figure.render(d,{...panel,analysis:panelAnalysis(panel)});}catch(error){figure={svg:'',error:true,summary:[],message:error.message};}boardResults.push(figure);const n=figure.set?new Set(figure.set.records.filter(r=>r.value!==null&&!figure.set.byId.get(r.mouse_id).excluded&&figure.set.groups.includes(figure.set.byId.get(r.mouse_id)[panel.grouping]||'Not specified')).map(r=>r.mouse_id)).size:0;return `<article class="chart-card ${index===activePanel?'is-active':''}" data-panel-index="${index}"><header class="chart-card-header"><button type="button" data-panel-focus="${index}" aria-label="Graph ${index+1} Settings" aria-pressed="${index===activePanel}"><b>${String.fromCharCode(65+index)} · Graph ${index+1}</b><span>${index===activePanel?'Active':'Settings'}</span></button><button type="button" data-panel-statistics="${index}">p-value</button><span class="chart-card-n">n=${n} · ${esc(panel.error==='none'?'Mean':panel.error)}</span></header><label class="chart-metric-label">Metric<button type="button" ${availableMetrics.length?'':'disabled'} aria-haspopup="dialog" data-choose-metric="${index}">${esc(choiceLabel(panel))}</button></label><div class="chart-coverage">${figure.coverage?`Missing ${figure.coverage.missing.length} · Unmeasured ${figure.coverage.unmeasured.length} · Excluded ${figure.coverage.excluded.length}`:''}<button type="button" data-panel-coverage="${index}">N details</button></div><div class="chart-range-note">${figure.axis?.clippedLowerErrorBars?`Y-axis starts at ${esc(figure.axis.min)} · Lower ${esc(panel.error)} error bars partly clipped`:""}</div><div class="chart-statistics" ${panel.comparisonMode==='none'?'hidden':''}>${panel.statMode==='anova-tukey'?(figure.analysis?.status==='ok'?esc(Figure.formatP(figure.analysis.anova.p,'ANOVA p'))+' · Tukey-adjusted p':esc(panelAnalysis(panel)?.message||'Calculating…')):'Calculating p-values…'}</div><div class="chart-plot">${figure.svg||`<p class="chart-error">${esc(figure.message)}</p>`}</div></article>`}).join('');
 if(metricPicker)drawMetricStep();
 lastFigure=boardResults[activePanel];$('#figure-status').textContent=example?`${graphCount} graphs · Synthetic example (not research results)`:`${graphCount} graphs · ${studyMouseIds().length} mice selected · Globally excluded ${d.mice.filter(m=>m.excluded).length} mice${sampleChanges.size?' · Previewing unsaved sample selection':''}`;
 $('#summary-label').textContent=`Graph ${activePanel+1} Summary`;$('#summary').innerHTML=lastFigure?.summary?.length?'<table><thead><tr><th>Group / Timepoint</th><th>n</th><th>Mean</th><th>SD</th><th>SEM</th><th>Missing</th><th>Unmeasured</th><th>Excluded</th></tr></thead><tbody>'+lastFigure.summary.map(s=>`<tr><td>${esc(s.group)}${cfg().type==='line'?' / '+esc(s.timepoint):''}</td><td>${s.n}</td><td>${fmt(s.mean)}</td><td>${fmt(s.sd)}</td><td>${fmt(s.sem)}</td><td>${s.missing_values}</td><td>${s.unmeasured}</td><td>${s.excluded}</td></tr>`).join('')+'</tbody></table>':'';const metric=d.metrics.find(m=>m.id===Number(panels[activePanel].metric));$('#measurement-unit-note').hidden=metric?.unit!=='a.u.';$('#measurement-unit-note').textContent='a.u. = arbitrary units of relative fluorescence intensity, not cell counts or concentrations. This file reports Geometric Mean.';renderSamples();renderComparison();renderPalette();renderStatistics();queueStatistics();}
function showCoverage(index){const figure=boardResults[index],coverage=figure?.coverage;if(!coverage)return;$('#coverage-title').textContent=`Graph ${String.fromCharCode(65+index)} · Sample count`;const metric=current().metrics.find(m=>m.id===Number(panels[index].metric));$('#coverage-details').innerHTML=`<p>${esc(metricLabel(metric))}</p><p>N includes mice with values for the selected groups, experiment, timepoint and replicate. Zero is a measured value. Each mouse counts once across timepoints.</p>`+[['measured','Measured (n)'],['missing','Missing: observation exists, but value is blank'],['unmeasured','Unmeasured: no observation for this metric/timepoint'],['excluded','Globally excluded, with or without a measured value']].map(([key,label])=>`<details ${key!=='measured'?'open':''}><summary>${esc(label)} · ${coverage[key].length} mice</summary><p>${coverage[key].length?coverage[key].map(id=>'Mouse '+esc(id)).join(', '):'None'}</p></details>`).join('');$('#coverage-dialog').showModal();}
$('#coverage-close').onclick=()=>$('#coverage-dialog').close();
function exportBoardSvg(){rememberPanel();if(!example&&panelConfigs().some((p,i)=>boardResults[i]?.svg&&p.comparisonMode!=='none'&&p.statMode==='anova-tukey'&&panelAnalysis(p)?.status==='pending'))throw Error('Wait for p-value calculations before exporting.');const svg=Figure.composeFigures(boardResults);const meta=esc(JSON.stringify({config:boardConfig(),metrics:current().metrics.filter(m=>panelConfigs().some(c=>Number(c.metric)===m.id)),revision:data.revision,statistical_results:boardResults.map(f=>f.analysis),coverage:boardResults.map(f=>f.coverage),axes:boardResults.map(f=>f.axis),pending_sample_selection:[...sampleChanges.values()],synthetic:example,exported_at:new Date().toISOString()}));return svg.replace(/(<svg\b[^>]*>)/,`$1<metadata>${meta}</metadata>`);}
$('#active-graph').onchange=()=>focusPanel(Number($('#active-graph').value));
$('#graph-count').onchange=()=>{rememberPanel();graphCount=Number($('#graph-count').value);ensurePanels();options($('#active-graph'),Array.from({length:graphCount},(_,i)=>({value:String(i),label:`Graph ${i+1}`})),'',String(activePanel));restorePanelControls();renderGraph();};
let metricPicker=null;
const pickerTrigger=()=>metricPicker.side?$('#choose-metric'):$(`[data-choose-metric="${metricPicker.index}"]`);
function closeMetricPicker(){
 if(metricPicker)pickerTrigger()?.setAttribute('aria-expanded','false');
 $('#metric-popup').close();
 if(metricPicker)pickerTrigger()?.focus();
 metricPicker=null;
}
function openMetricPicker(index,side=false){
 const toggle=metricPicker?.index===index&&metricPicker.side===side;
 closeMetricPicker();
 if(toggle)return;
 metricPicker={index,side,path:[]};
 drawMetricStep();
 if(metricPicker)$('#metric-popup').showModal();
}
function drawMetricStep(){
 const {index,side,path}=metricPicker,trigger=pickerTrigger();
 if(!trigger||trigger.disabled||(side&&index!==activePanel)){closeMetricPicker();return;}
 const data=current(),selected=new Set(studyMouseIds());
 const scoped={...data,measurements:data.measurements.filter(r=>selected.has(r.mouse_id))};
 const choices=Figure.metricChoices(scoped,data.metrics);
 const matches=choice=>path.every((item,i)=>choice.path[i]===item);
 while(path.length&&!choices.some(matches))path.pop();

 const order=['Metabolic outcome','Histology','Flow cytometry','qPCR','Weight-timeline','Weight-endpoint','ITT','OGTT'];
 const rank=label=>order.includes(label)?order.indexOf(label):order.length;
 const ko=document.documentElement.lang==='ko';
 const step=$('#metric-step');
 trigger.setAttribute('aria-expanded','true');
 const columns=[];
 let level=choices,offset=0;
 for(let depth=0;depth<=path.length;depth++){
  const folders=[...new Set(level.map(choice=>choice.path[depth]).filter(Boolean))].sort((a,b)=>rank(a)-rank(b)||a.localeCompare(b));
  const leaves=level.filter(choice=>choice.path.length===depth);
  const folderButtons=folders.map(label=>`<button type="button" data-folder="${esc(label)}" aria-pressed="${path[depth]===label}" title="${esc(label)}"><span>${esc(label)}</span><span aria-hidden="true">›</span></button>`);
  const leafButtons=leaves.map(({metric,view})=>`<button type="button" data-pick="${esc(metric.id)}" data-view="${esc(view)}" title="${esc(fullMetricLabel(metric))}"><span>${esc(metric.name)} (${esc(metric.unit)})</span></button>`);
  columns.push(`<div class="metric-column" data-depth="${depth}" style="--row-offset:${offset}">${folderButtons.join('')}${leafButtons.join('')}</div>`);
  if(depth<path.length){
   offset+=Math.max(0,folders.indexOf(path[depth]));
   level=level.filter(choice=>choice.path[depth]===path[depth]);
  }
 }
 const html='<div class="metric-columns">'+columns.join('')+'</div>'+
 (choices.length?'':`<p>${ko?'선택한 조건에 측정값이 없습니다.':'No measurements match the selected conditions.'}</p>`)+
 `<footer><button type="button" data-clear>Clear graph</button><button type="button" data-close>Close</button></footer>`;
 if(metricPicker.html!==html){step.innerHTML=html;metricPicker.html=html;}
 step.onclick=event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.hasAttribute('data-folder')){
   const depth=Number(button.closest('[data-depth]').dataset.depth);
   const list=step.querySelector('.metric-columns');
   const scrollTop=list.scrollTop,scrollLeft=list.scrollLeft;
   path.splice(depth,path.length-depth,button.dataset.folder);
   drawMetricStep();
   const next=step.querySelector('.metric-columns');
   next.scrollTo(scrollLeft,scrollTop);
   const first=next.querySelector('[data-depth="'+(depth+1)+'"] button');
   first?.focus({preventScroll:true});first?.scrollIntoView({block:'nearest',inline:'nearest'});
   return;
  }
  closeMetricPicker();
  if(!button.hasAttribute('data-close'))changePanelMetric(index,button.dataset.pick||'',button.dataset.view||'');
  (side?$('#choose-metric'):$(`[data-choose-metric="${index}"]`))?.focus();
 };
}
$('#metric-popup').oncancel=event=>{event.preventDefault();closeMetricPicker();};
$('#metric-popup').onclick=event=>{
 if(event.target!==event.currentTarget)return;
 const bounds=event.currentTarget.getBoundingClientRect();
 if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)closeMetricPicker();
};
$('#choose-metric').onclick=()=>openMetricPicker(activePanel,true);
$('#figure').addEventListener('click',event=>{const button=event.target.closest('[data-choose-metric]');if(button)openMetricPicker(Number(button.dataset.chooseMetric));});
function showGraphControl(panelId){
 for(const toggle of document.querySelectorAll('.graph-control-menu button')){
  const target=document.getElementById(toggle.getAttribute('aria-controls'));
  const selected=target.id===panelId;
  target.hidden=!selected;
  toggle.setAttribute('aria-expanded',String(selected));
 }
}
$('.graph-control-menu').onclick=event=>{
 const toggle=event.target.closest('button');
 if(toggle)showGraphControl(toggle.getAttribute('aria-expanded')==='true'?null:toggle.getAttribute('aria-controls'));
};
$('#figure').addEventListener('click',event=>{const button=event.target.closest('[data-panel-focus]');if(button){focusPanel(Number(button.dataset.panelFocus));showGraphControl('graph-settings-body');}const coverage=event.target.closest('[data-panel-coverage]');if(coverage)showCoverage(Number(coverage.dataset.panelCoverage));const stats=event.target.closest('[data-panel-statistics]');if(stats){focusPanel(Number(stats.dataset.panelStatistics));showGraphControl('graph-settings-body');$('#stats-panel').open=true;$('#stats-panel').scrollIntoView({block:'nearest'});}});

function cfg(){return {trend:$('#weight-trend').value,scope_mouse_ids:studyMouseIds(),scope_experiments:studyExperiments(),metric:$('#metric').value,experiment:$('#experiment').value,weeks:$('#weeks').value,grouping:$('#grouping').value,timepoint:$('#timepoint').value,replicate:$('#replicate').value,type:$('#chart-type').value,error:$('#error-type').value,title:$('#plot-title').value,ytitle:$('#y-title').value,xtitle:$('#x-title').value,ymin:$('#y-min').value,ymax:$('#y-max').value,font:$('#font-size').value,angle:$('#angle').value,showExcluded:$('#show-excluded').checked,statMode:'anova-tukey',comparisonMode:$('#comparison-mode').value,styles}}
function populate(){renderStudyTabs();const d=current();ensurePanels();const availableMetrics=graphMetrics(d);options($('#metric'),availableMetrics.map(m=>({value:m.id,label:metricLabel(m)})),availableMetrics.length?'Select a metric':'No measurements');$('#metric').disabled=!availableMetrics.length;options($('#experiment'),[...new Set(d.mice.map(m=>m.experiment))].filter(Boolean),'All');options($('#weeks'),[...new Set(d.mice.map(m=>m.weeks))].filter(Boolean).sort((a,b)=>+a-+b),'All');for(const option of $('#metric').options){const metric=d.metrics.find(m=>m.id===Number(option.value));if(metric)option.title=fullMetricLabel(metric);}options($('#active-graph'),Array.from({length:graphCount},(_,i)=>({value:String(i),label:`Graph ${i+1}`})),'',String(activePanel));options($('#preset'),data.presets.map(p=>({value:p.id,label:p.name})),'Select a saved preset');restorePanelControls();renderGraph();renderData();}
function updateTime(){const r=current().measurements.filter(r=>r.metric_id===Number($('#metric').value));options($('#timepoint'),[...new Set(r.map(r=>r.timepoint))]);options($('#replicate'),[...new Set(r.map(r=>r.replicate))]);$('#timepoint').disabled=$('#chart-type').value==='line';}
function fmt(n){return n===null||n===undefined?'—':Number(n).toFixed(2)}
function table(headers,rows){return '<table><thead><tr>'+headers.map(h=>`<th>${esc(h)}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
function renderData(){const q=$('#search').value.toLowerCase(),kind=$('#table-kind').value;let rows;if(kind==='mice')rows=data.mice.filter(m=>Object.values(m).join(' ').toLowerCase().includes(q));else rows=data.measurements.map(r=>({...r,mouse:data.mice.find(m=>m.mouse_id===r.mouse_id),metric:data.metrics.find(m=>m.id===r.metric_id)})).filter(r=>[r.mouse_id,r.mouse.group_name,fullMetricLabel(r.metric),r.timepoint].join(' ').toLowerCase().includes(q));const pages=Math.max(1,Math.ceil(rows.length/50));pageIndex=Math.min(pageIndex,pages-1);$('#page-number').textContent=`${pageIndex+1} / ${pages} · ${rows.length} rows`;$('#prev').disabled=pageIndex===0;$('#next').disabled=pageIndex>=pages-1;
 $('#data-table').innerHTML=kind==='mice'?table(['Mouse ID','Group','Experiment','Age (weeks)','Diet','Notes','Status',''],rows.slice(pageIndex*50,pageIndex*50+50).map(m=>[esc(m.mouse_id),esc(m.group_name),esc(m.experiment),esc(m.weeks)||'—',esc(m.diet),esc(m.note),m.excluded?'Excluded':'Included',`<button data-edit-mouse="${esc(m.mouse_id)}">Edit</button>`])):table(['Mouse ID','Group','Metric','Timepoint','Replicate','Value','Missing reason','Version',''],rows.slice(pageIndex*50,pageIndex*50+50).map(r=>[esc(r.mouse_id),esc(r.mouse.group_name),`<span title="${esc(fullMetricLabel(r.metric))}">${esc(metricLabel(r.metric))}</span>`,esc(r.timepoint),esc(r.replicate),fmt(r.value),esc(r.missing_reason),r.version,`<button data-edit-measure="${r.id}">Edit</button>`]));
 $('#data-count').textContent=`${data.mice.length} mice · ${data.metrics.length} metrics · ${data.measurements.length} observations`;
 $('#uploads').innerHTML=data.uploads.map(u=>`<div class="source-row"><span>${esc(u.filename)} · ${esc(u.uploaded_by)} · ${esc(new Date(u.created_at).toLocaleString('en-GB'))}</span><a href="/api/source/${u.id}">Download original</a>${user.role==='admin'||(user.role==='editor'&&user.username===u.uploaded_by)?`<button type="button" data-remove-upload="${esc(u.id)}">${document.documentElement.lang==='ko'?'가져오기 삭제':'Remove import'}</button>`:''}</div>`).join('')||'<p>No measurement files imported yet.</p>';
}
async function sync(silent=false){try{const next=await api('/state');if(!data||next.revision!==data.revision){data=next;renderHomeSummary(data);populate();if(!silent)notice('Loaded the latest server data.');}$('#sync-state').textContent='Saved on server · Last checked '+new Date().toLocaleTimeString('en-GB');}catch(e){$('#sync-state').textContent='Disconnected. Check your connection before saving.';if(!silent)notice(e.message)}}
async function start(){const state=await api('/me');setup=state.setup_required;user=state.user;if(!user){$('#auth').hidden=false;$('#workspace').hidden=true;$('#auth-description').textContent=setup?'Create the first administrator account to manage lab users.':'Sign in with your lab account.';$('#login-button').textContent=setup?'Create administrator':'Sign in';if(setup&&!state.local_setup_allowed){$('#login-button').disabled=true;$('#auth-description').textContent='Set up the first administrator on the server computer using localhost.'}return;}$('#auth').hidden=true;$('#workspace').hidden=false;$('#account').textContent=user.username;$('#users-tab').hidden=user.role!=='admin';$('[data-page="fcs"]').hidden=!user.fcs_access;if(!user.fcs_access){$('#fcs').hidden=true;if($('[data-page="fcs"]').classList.contains('active'))$('[data-page="graphs"]')?.click();}data=await api('/state');populate();$('#sync-state').textContent='Connected to server';await renderHome();}
$('#login').onsubmit=async e=>{e.preventDefault();try{user=await api(setup?'/setup':'/login','POST',{username:$('#username').value,password:$('#password').value});$('#password').value='';await start()}catch(e){$('#auth-error').textContent=e.message}};
$('#logout').onclick=async()=>{await api('/logout','POST',{});location.reload()};$('#refresh').onclick=()=>sync();
document.addEventListener('click',async e=>{const nav=e.target.closest('[data-page]');if(nav){document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!==nav.dataset.page);document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('active',b===nav));try{if(nav.dataset.page==='experiments')await renderExperiments();if(nav.dataset.page==='home'){await sync(true);await renderHome()}if(nav.dataset.page==='history'){audit=await api('/audit');renderAudit()}if(nav.dataset.page==='users')await renderUsers()}catch(e){notice(e.message)}}const m=e.target.closest('[data-edit-measure]');if(m)openEdit('measurement',Number(m.dataset.editMeasure));const mouse=e.target.closest('[data-edit-mouse],[data-mouse]');if(mouse){if(example&&mouse.hasAttribute('data-mouse')){notice('Synthetic examples cannot be edited. Click a real data point to exclude or restore a mouse globally.');return;}openEdit('mouse',mouse.dataset.editMouse||mouse.dataset.mouse)}});
document.addEventListener('keydown',e=>{if(e.target.matches('[data-mouse]')&&['Enter',' '].includes(e.key)){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}))}});
$('#example').onclick=()=>{if(sampleChanges.size){notice('Save or cancel pending sample selections before opening the example.');return;}switchExample(!example);};
$('#metric').onchange=()=>changePanelMetric(activePanel,$('#metric').value);
for(const id of ['experiment','weeks','grouping','timepoint','replicate','chart-type','weight-trend','error-type','angle','show-excluded','comparison-mode'])$('#'+id).onchange=()=>{updateTime();renderGraph()};
for(const id of ['plot-title','y-title','x-title','y-min','y-max','font-size'])$('#'+id).oninput=()=>renderGraph(false);
$('#save-preset').onclick=async()=>{try{const name=$('#preset-name').value.trim();const existing=data.presets.find(p=>p.name===name);const saved=await api('/presets','POST',{name,config:boardConfig(),version:existing?($('#preset').value===String(existing.id)?presetVersion:null):undefined});await sync(true);$('#preset').value=String(saved.id);presetVersion=saved.version;notice('Shared graph preset saved.');}catch(e){notice(e.message)}};
$('#preset').onchange=()=>{const preset=data.presets.find(p=>p.id===Number($('#preset').value));if(!preset)return;const c=preset.config;graphStudy=['all','basic','di','custom'].includes(c.dashboard?.study)?c.dashboard.study:'all';comparisonIds=Array.isArray(c.dashboard?.comparisonIds)?new Set(c.dashboard.comparisonIds):c.dashboard?.comparisonIds===null?null:['basic','di'].includes(graphStudy)?new Set(StudyScope.selection(data,graphStudy,c.dashboard?.diControls||[])):null;if(c.dashboard&&Array.isArray(c.dashboard.panels)&&c.dashboard.panels.length>=1&&c.dashboard.panels.length<=8){panels=structuredClone(c.dashboard.panels);graphCount=Number(c.dashboard.count)||panels.length;activePanel=Number(c.dashboard.active)||0;groupPalette=Object.assign(Object.create(null),c.dashboard.palette||{});sharedGroups=Object.assign(defaultSharedGroups(),structuredClone(c.dashboard.groupSettings||{}));if(!c.dashboard.groupSettings){for(const panel of panels)for(const [group,style] of Object.entries(panel.styles||{}))if(style.include){const key=Figure.groupKey(group);sharedGroup(key).color=groupPalette[key]||style.color;sharedGroup(key).shape=style.shape;sharedGroup(key).fill=style.fill;}}}else{panels[activePanel]=structuredClone(c);}ensurePanels();populate();$('#preset').value=String(preset.id);$('#preset-name').value=preset.name;presetVersion=preset.version;};
$('#svg-export').onclick=()=>{try{download('figures.svg',exportBoardSvg(),'image/svg+xml');}catch(error){notice(error.message)}};
$('#png-export').onclick=()=>{let svg;try{svg=exportBoardSvg();}catch(error){return notice(error.message);}const img=new Image(),url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));img.onload=()=>{const canvas=document.createElement('canvas');canvas.width=img.width*2;canvas.height=img.height*2;canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>{if(blob)download('figures-2x.png',blob,'image/png');else notice('PNG conversion failed. Export as SVG instead.');URL.revokeObjectURL(url)},'image/png')};img.onerror=()=>{URL.revokeObjectURL(url);notice('PNG conversion failed. Export as SVG instead.')};img.src=url;};
$('#plot-csv').onclick=()=>{const rows=[];boardResults.forEach((figure,index)=>{if(!figure?.set)return;const set=figure.set,panel=panels[index],metric=current().metrics.find(m=>m.id===Number(panel.metric));set.records.filter(r=>!set.byId.get(r.mouse_id).excluded&&set.groups.includes(set.byId.get(r.mouse_id)[panel.grouping]||'Not specified')).forEach(r=>rows.push({...r,panel:index+1,experiment:set.byId.get(r.mouse_id).experiment,weeks:set.byId.get(r.mouse_id).weeks,selection_mode:graphStudy,experiment_type:data.experiment_types?.[set.byId.get(r.mouse_id).experiment]||'unclassified',metric:metric?.name,organ:metric?.organ,gate:metric?.gate,unit:metric?.unit,group:set.byId.get(r.mouse_id)[panel.grouping],synthetic:example,selection_preview:!!sampleChanges.size}));});download('figures-data.csv',csv(rows,['panel','mouse_id','experiment','weeks','selection_mode','experiment_type','group','metric_id','metric','organ','gate','unit','timepoint','replicate','value','missing_reason','synthetic','selection_preview']),'text/csv');};
$('#search').oninput=()=>{pageIndex=0;renderData()};$('#table-kind').onchange=()=>{pageIndex=0;renderData()};$('#prev').onclick=()=>{pageIndex--;renderData()};$('#next').onclick=()=>{pageIndex++;renderData()};
$('#data-json').onclick=async()=>{try{download('mouse-lab-data.json',JSON.stringify(await api('/export'),null,2),'application/json')}catch(e){notice(e.message)}};
$('#data-csv').onclick=()=>{const rows=data.measurements.map(r=>({...r,metric:fullMetricLabel(data.metrics.find(m=>m.id===r.metric_id)),excluded:data.mice.find(m=>m.mouse_id===r.mouse_id).excluded}));download('measurements.csv',csv(rows,['id','mouse_id','metric','timepoint','replicate','value','missing_reason','excluded','version','upload_id','source_row']),'text/csv')};
function openEdit(kind,id){const r=kind==='mouse'?data.mice.find(m=>m.mouse_id===id):data.measurements.find(m=>m.id===id);editing={kind,id,version:r.version};$('#edit-title').textContent=kind==='mouse'?'Mouse '+id:'Measurement Edit · Mouse '+r.mouse_id;$('#edit-reason').value='';$('#edit-error').textContent='';
 if(kind==='mouse')$('#edit-fields').innerHTML=`<div class="info">Mouse IDs cannot be changed. Exclusions apply to every metric, organ and gate.</div>`+[['group_name','Group'],['experiment','Experiment'],['weeks','Age (weeks)'],['diet','Diet'],['note','Notes']].map(([k,l])=>`<label>${l}<input data-field="${k}" value="${esc(r[k])}" ${k==='group_name'?'required':''}></label>`).join('')+`<label class="inline"><input type="checkbox" data-field="excluded" ${r.excluded?'checked':''}> Exclude this mouse from all analyses</label>`;
 else{const m=data.metrics.find(m=>m.id===r.metric_id);$('#edit-fields').innerHTML=`<div class="info">${esc(metricLabel(m))} · Timepoint ${esc(r.timepoint)} · Replicate ${esc(r.replicate)} · Version ${r.version}</div><label>Value (blank = missing)<input data-field="value" type="number" step="any" value="${r.value===null?'':r.value}"></label><label>Missing reason (leave blank when a value exists)<input data-field="missing_reason" value="${esc(r.missing_reason)}"></label>`;}
 $('#editor').showModal();}
$('#close-editor').onclick=()=>$('#editor').close();$('#edit-form').onsubmit=async e=>{e.preventDefault();const payload={version:editing.version,reason:$('#edit-reason').value};document.querySelectorAll('[data-field]').forEach(i=>payload[i.dataset.field]=i.type==='checkbox'?i.checked:i.value);try{await api((editing.kind==='mouse'?'/mice/':'/measurements/')+encodeURIComponent(editing.id),'PATCH',payload);$('#editor').close();await sync(true);notice('Changes and audit history saved to the server.')}catch(e){$('#edit-error').textContent=e.message;await sync(true)}};
const removeDialog=$('#remove-import');
$('#uploads').addEventListener('click',event=>{
 const button=event.target.closest('[data-remove-upload]');
 if(!button)return;
 const id=button.dataset.removeUpload, upload=data.uploads.find(item=>item.id===id);
 if(!upload)return;
 const count=data.measurements.filter(row=>row.upload_id===id).length;
 removeDialog.dataset.uploadId=id;
 const ko=document.documentElement.lang==='ko';
 $('#remove-import-info').textContent=ko?`${upload.filename} · 측정값 ${count}건을 활성 데이터에서 제외합니다. 마우스 명단과 원본 파일은 보존합니다.`:`Remove ${upload.filename} and its ${count} measurements from active data? The mouse roster and original file are preserved.`;
 $('#remove-import-reason').value='';$('#remove-import-error').textContent='';
 removeDialog.showModal();$('#remove-import-reason').focus();
});
$('#remove-import-cancel').onclick=()=>removeDialog.close();
$('#remove-import-form').onsubmit=async event=>{
 event.preventDefault();
 const reason=$('#remove-import-reason'), error=$('#remove-import-error');
 if(!reason.value.trim()){error.textContent=document.documentElement.lang==='ko'?'삭제 사유를 입력하세요.':'Enter a reason for removal.';reason.focus();return}
 const submit=event.submitter;if(submit)submit.disabled=true;
 try{
  const result=await api('/import/remove','POST',{upload_id:removeDialog.dataset.uploadId,reason:reason.value.trim()});
  removeDialog.close();await sync(true);
  notice(document.documentElement.lang==='ko'?`측정값 ${result.removed}건을 제외했습니다.`:`Removed ${result.removed} measurements.`);
 }catch(e){error.textContent=e.message}finally{if(submit)submit.disabled=false}
};
function renderAudit(){const q=$('#audit-search').value.toLowerCase(),tr=I18n.t;$('#events').innerHTML=audit.filter(e=>(JSON.stringify(e)+' '+I18n.reason(e.reason)+' '+tr(e.action)+' '+tr(e.entity)).toLowerCase().includes(q)).slice(0,300).map(e=>{const display=I18n.reason(e.reason),untranslated=I18n.language==='en'&&/[가-힣]/.test(display);return `<article class="event" data-original><b>${esc(tr(e.action))} · ${esc(tr(e.entity))} ${esc(e.entity_id)}</b><div class="meta">${esc(e.username)} · ${esc(new Date(e.created_at).toLocaleString(I18n.language==='ko'?'ko-KR':'en-GB'))} · #${e.id}</div>${untranslated?`<small>${esc(tr('Original note (not translated)'))}</small>`:''}<p>${esc(display)}</p>${display!==e.reason?`<details><summary>${esc(tr('Original note'))}</summary><p>${esc(e.reason)}</p></details>`:''}<details><summary>${esc(tr('View before and after'))}</summary><pre>${esc(JSON.stringify({before:JSON.parse(e.before_json),after:JSON.parse(e.after_json)},null,2))}</pre></details></article>`;}).join('')||'<p>'+esc(tr('No history found.'))+'</p>';}
document.addEventListener('languagechange',()=>{if(data)renderAudit();});
$('#audit-search').oninput=renderAudit;$('#audit-export').onclick=()=>download('audit.json',JSON.stringify(audit,null,2),'application/json');
let accountRows=[],renamingUser=null,accountExpectedName='';
let loginHistoryRows=[],loginHistoryCursor=null;
function paintLoginHistory(){const t=I18n.t;$('#login-history-results').innerHTML=loginHistoryRows.length?table([t('Time'),t('Username'),t('Result')],loginHistoryRows.map(r=>[esc(new Date(r.created_at).toLocaleString(I18n.language==='ko'?'ko-KR':'en-GB',{timeZone:'Europe/Berlin'})),esc(r.username),esc(t({success:'Successful login',failure:'Failed login',blocked:'Rate limited'}[r.outcome]))])):'<p>'+esc(t('No login records yet.'))+'</p>';$('#login-history-more').hidden=!loginHistoryCursor;}
async function loadLoginHistory(more=false){if(user?.role!=='admin')return;try{const result=await api('/login-history'+(more&&loginHistoryCursor?'?before='+loginHistoryCursor:''));loginHistoryRows=more?[...loginHistoryRows,...result.rows]:result.rows;loginHistoryCursor=result.next_before;paintLoginHistory();}catch(e){notice(e.message);}}
$('#login-history-refresh').onclick=()=>loadLoginHistory();$('#login-history-more').onclick=()=>loadLoginHistory(true);
document.addEventListener('languagechange',()=>{if(user?.role==='admin')paintLoginHistory();});
async function renderUsers(){await loadLoginHistory();accountRows=await api('/users');$('#user-list').innerHTML=table(['User','Role','Created',''],accountRows.map(u=>[esc(u.username),esc(u.role),esc(new Date(u.created_at).toLocaleString('en-GB')),`<button type="button" data-rename-user="${u.id}">Rename</button>`]))}
$('#user-list').onclick=e=>{const button=e.target.closest('[data-rename-user]');if(!button)return;renamingUser=accountRows.find(u=>u.id===Number(button.dataset.renameUser));if(!renamingUser)return;$('#rename-username').value=renamingUser.username;$('#rename-error').textContent='';$('#rename-dialog').showModal()};
$('#rename-close').onclick=()=>$('#rename-dialog').close();
$('#rename-form').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const result=await api('/users/'+renamingUser.id,'PATCH',{username:$('#rename-username').value,expected_username:renamingUser.username});if(result.id===user.id){user.username=result.username;$('#account').textContent=result.username}$('#rename-dialog').close();await renderUsers();notice('Username updated. Use the new username to sign in.')}catch(error){$('#rename-error').textContent=error.message}finally{button.disabled=false}};
$('#my-account').onclick=async()=>{try{const state=await api('/me');if(!state.user){location.reload();return}user=state.user;accountExpectedName=user.username;$('#account').textContent=user.username;$('#account-username').value=user.username;$('#account-password-form').reset();$('#account-message').textContent='';$('#account-dialog').showModal()}catch(error){notice(error.message)}};
$('#account-close').onclick=()=>$('#account-dialog').close();
$('#account-dialog').addEventListener('close',()=>$('#account-password-form').reset());
$('#account-name-form').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const result=await api('/account','PATCH',{username:$('#account-username').value,expected_username:accountExpectedName});user.username=result.username;accountExpectedName=result.username;$('#account').textContent=result.username;$('#account-message').textContent='Username saved. Use it the next time you sign in.';if(user.role==='admin')await renderUsers()}catch(error){$('#account-message').textContent=error.message}finally{button.disabled=false}};
$('#account-password-form').onsubmit=async e=>{e.preventDefault();if($('#account-new-password').value!==$('#confirm-password').value){$('#account-message').textContent='The new passwords do not match.';return}const button=e.submitter;button.disabled=true;try{await api('/account/password','POST',{current_password:$('#current-password').value,new_password:$('#account-new-password').value});$('#account-password-form').reset();$('#account-dialog').close();user=null;await start();$('#username').value=accountExpectedName;$('#auth-description').textContent='Password changed. Sign in with your new password.'}catch(error){$('#account-message').textContent=error.message}finally{button.disabled=false}};

$('#new-user').onsubmit=async e=>{e.preventDefault();try{await api('/users','POST',{username:$('#new-username').value,password:$('#new-password').value,role:$('#new-role').value});$('#new-password').value='';await renderUsers();notice('User account created.')}catch(e){notice(e.message)}};
let importKind='meta';const importDrafts={meta:null,facs:null},emptyImportMarkup=$('#mapping').innerHTML;
function renderImportKind(){
 const facs=importKind==='facs';
 $('#import-description').textContent=facs?'Import gate-level FACS results.':'Import mouse metadata and general measurements.';
 $('#import-kind-help').textContent=facs?'Upload FlowJo Count / Frequency / MFI Excel summaries, or a table with one gate result per column. Review organ, full gate path, parent gate and denominator. Raw .fcs files and .wsp workspaces belong in the FACS menu.':'Upload mouse IDs, groups, Exp and diet information alongside measurements such as body weight, OGTT, ITT and histology. Choose metadata-only registration to add mice before measurements are available.';
 $('#import-upload-help').textContent=facs?'For FlowJo Excel, select the correct sheet/table and confirm sample-to-mouse mapping. For custom tables, define each metric and its units; Frequency must specify its parent population.':'Use column headers in the first row. Map OGTT_0, OGTT_15, etc. to one metric with different timepoints. Convert formulas to values in a copy before uploading.';
 $('#metadata-only-label').hidden=facs;$('#metadata-only-help').hidden=facs;
 $('#template').textContent=facs?'FACS example CSV':'META example CSV';
 $('#import-current-file').textContent=stage?'Selected file: '+(stage.display_filename||'Uploaded file')+' · measurements not saved':'';
 for(const button of document.querySelectorAll('[data-import-kind]')){const active=button.dataset.importKind===importKind;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;}
 $('#import-panel').setAttribute('aria-labelledby','import-'+importKind+'-tab');updateMetadataMode();
}
function selectImportKind(kind){
 if(busy||kind===importKind)return;
 importDrafts[importKind]={stage,markup:$('#mapping').innerHTML,controls:[...$('#mapping').querySelectorAll('input,select,textarea')].map(el=>({value:el.value,checked:el.checked}))};
 importFieldError('#file','#import-file-error','');importKind=kind;const draft=importDrafts[kind];stage=draft?.stage||null;$('#mapping').innerHTML=draft?.markup||emptyImportMarkup;
 if(draft)[...$('#mapping').querySelectorAll('input,select,textarea')].forEach((el,i)=>{el.value=draft.controls[i].value;if(el.type==='checkbox')el.checked=draft.controls[i].checked;});
 $('#mapping').hidden=!stage;$('#file').value='';$('#sheet').onchange=changeImportSheet;invalidateImportReview();$('#validate-import').onclick=validateImport;$('#commit-import').onclick=commitImport;renderImportKind();
}
for(const button of document.querySelectorAll('[data-import-kind]')){button.onclick=()=>selectImportKind(button.dataset.importKind);button.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();selectImportKind(importKind==='meta'?'facs':'meta');document.querySelector('[data-import-kind="'+importKind+'"]').focus()}}}
renderImportKind();
function importFieldError(field, message, text) {
 const input=$(field), hint=$(message);
 if(text)input.setAttribute('aria-invalid','true');else input.removeAttribute('aria-invalid');
 hint.textContent=text;hint.hidden=!text;
}
$('#file').onchange=async e=>{
 const file=e.target.files[0];if(!file||busy)return;
 importFieldError('#file','#import-file-error','');
 stage=null;$('#mapping').hidden=true;renderImportKind();
 try{
  busy=true;
  if(file.size>10*1024*1024)throw Error('Maximum file size is 10 MB.');
  $('#import-current-file').textContent='Reading '+file.name+'…';
  const bytes=new Uint8Array(await file.arrayBuffer());let binary='';
  for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  stage=await api('/upload','POST',{filename:file.name,content:btoa(binary)});
  stage.display_filename=file.name;showMapping();renderImportKind();
  notice('Review the preview and select columns to import. Measurements have not been saved yet.');
 }catch(error){
  stage=null;$('#mapping').hidden=true;renderImportKind();$('#file').value='';
  importFieldError('#file','#import-file-error',file.name+' — '+error.message);
 }finally{busy=false}
};
function showMapping(){invalidateImportReview();importFieldError('#import-reason','#import-reason-error','');$('#import-allow-new').checked=false;const h=stage.headers;$('#mapping').hidden=false;options($('#sheet'),stage.sheets.length?stage.sheets:['CSV'],'',stage.sheet);$('#sheet').disabled=!stage.sheets.length;for(const id of ['id-col','group-col','exp-col','weeks-col','diet-col','rep-col'])options($('#'+id),h,'Not selected');const aliases={'id-col':/^(mouse[_ ]?(id|number)|id)$/i,'group-col':/^(group|group_name|그룹)$/i,'exp-col':/^(experiment|exp|실험)$/i,'weeks-col':/^(weeks|주차)$/i,'diet-col':/^(diet|식이)$/i,'rep-col':/^(replicate|반복)$/i};for(const [id,re] of Object.entries(aliases)){const v=h.find(x=>re.test(x));if(v)$('#'+id).value=v;}
 $('#panel-classification').hidden=importKind!=='facs';$('#import-panel-name').value='';
 $('#row-count').textContent=`${stage.row_count} rows (first 8 shown)`;$('#preview').innerHTML=table(h,stage.rows.map(r=>r.map(esc)));
 $('#column-mapping').innerHTML=table(['Select','Source column','Metric name','Unit','Fixed timepoint','Timepoint column (optional)','Organ','Graph classification (optional)','FACS definition (optional)'],h.map((col,i)=>{const weightWeek=/^(?:body[ _-]*)?weight[ _-]+((?:week|wk|w)[ _-]*\d+|\d+[ ]*(?:weeks?|wk|w))$/i.exec(col),detected=/^(OGTT|ITT)[_ ]?(\d+)$/i.exec(col),name=weightWeek?'Body weight':detected?detected[1].toUpperCase():col,unit=/body.?weight|tissue|weight/i.test(col)?'g':/cholesterol|LDL|HDL|triglycer|glucose|OGTT|ITT/i.test(col)?'mg/dL':'';return [`<input type="checkbox" data-map="enabled" data-index="${i}">`,esc(col),`<input data-map="name" data-index="${i}" value="${esc(name)}">`,`<input data-map="unit" data-index="${i}" value="${unit}">`,`<input data-map="timepoint" data-index="${i}" value="${weightWeek?Figure.weekNumber(weightWeek[1]):detected?detected[2]:'endpoint'}">`,`<select data-map="time_column" data-index="${i}"><option value="">Use fixed timepoint</option>${h.map(v=>`<option>${esc(v)}</option>`).join('')}</select>`,`<input data-map="organ" data-index="${i}" placeholder="e.g. Liver">`,`<label>${importKind==='facs'?'Panel':'qPCR pathway'}<input data-map="${importKind==='facs'?'panel':'pathway'}" data-index="${i}" placeholder="${importKind==='facs'?'e.g. T Cell Panel':'e.g. Fibrosis'}" list="${importKind==='facs'?'panel-names':'pathway-names'}"></label>`,`<details><summary>Gate / Parent gate / Denominator</summary>${['gate','parent_gate','denominator'].map(k=>`<input data-map="${k}" data-index="${i}" placeholder="${k}">`).join('')}</details>`]}));showFacs();
 if(stage.confirmed_histology && importKind==='meta'){
  $('#metadata-only').checked=false;$('#exp-col').value='';
  for(const col of ['PSR','HE']){
   const i=h.indexOf(col);if(i<0)continue;
   const field=key=>document.querySelector(`[data-index="${i}"][data-map="${key}"]`);
   field('enabled').checked=true;field('unit').value=stage.confirmed_histology.unit;field('organ').value=stage.confirmed_histology.organ;
  }
 }
}
function showFacs(){
 const box=$('#facs-review');box.hidden=!stage.facs;if(!stage.facs)return;
 const f=stage.facs,samples=f.samples.filter(r=>r.kind==='sample');$('#id-col').value=stage.headers[0];
 const ids=samples.map(r=>r.mouse_id),duplicates=ids.length-new Set(ids).size;
 box.innerHTML=`<h3>Review FACS samples · ${samples.length} rows</h3><p>${esc(f.notice)}</p><p>Excluded ${f.samples.filter(r=>r.kind==='control / unmapped').length} control/unmapped rows and ${f.samples.filter(r=>r.kind==='summary').length} summary rows · ${duplicates} potential duplicate IDs · ${f.percent_cells_converted} cells converted to percentages</p>${f.needs_statistic?'<p><b>This is a later table block and may contain calculated values. Specify the statistic name and units.</b></p><label>Statistic name<input id="facs-statistic" placeholder="Enter after verifying the calculation"></label><label>Unit<input id="facs-unit" placeholder="e.g. cells/µL (verify units)"></label>':''}<div class="table-scroll" style="max-height:320px">${table(['Select','Source row','Sample filename','Organ','Mouse ID','Group (required for new mice)'],samples.map(r=>[`<input type="checkbox" data-sample-row="${r.row}" checked>`,r.row,esc(r.sample),esc(r.organ),`<input data-sample-id="${r.row}" value="${esc(r.mouse_id)}">`,`<input data-sample-group="${r.row}" placeholder="Leave blank for existing mice">`]))}</div><details><summary>View excluded control, unmapped and summary rows</summary>${table(['Source row','Filename','Classification'],f.samples.filter(r=>r.kind!=='sample').map(r=>[r.row,esc(r.sample),esc(r.kind)]))}</details><label><input type="checkbox" id="facs-reviewed"> I have verified the sheet/table and sample-to-mouse ID mapping.</label>`;
 f.specs.forEach(spec=>{const i=stage.headers.indexOf(spec.column);Object.entries(spec).forEach(([key,value])=>{const input=document.querySelector(`[data-index="${i}"][data-map="${key}"]`);if(input)input.value=value;});document.querySelector(`[data-index="${i}"][data-map="enabled"]`).checked=spec.has_values!==false;});
 if(f.confirmed_definition){$('#facs-statistic').value=f.confirmed_definition.statistic;$('#facs-unit').value=f.confirmed_definition.unit;}
}
async function changeImportSheet(){if(busy)return;try{busy=true;const filename=stage.display_filename;stage=await api('/preview','POST',{upload_id:stage.upload_id,sheet:$('#sheet').value});stage.display_filename=filename;showMapping();renderImportKind()}catch(e){$('#sheet').value=stage.sheet;invalidateImportReview();$('#sheet').setAttribute('aria-invalid','true');$('#import-validation').classList.add('has-errors');$('#import-validation').textContent=e.message;$('#import-validation').scrollIntoView({block:'nearest'})}finally{busy=false}}
$('#sheet').onchange=changeImportSheet;
let importReview=null;
function importMapping(){const measurements=[];stage.headers.forEach((col,i)=>{const fields=[...document.querySelectorAll(`[data-index="${i}"]`)];if(!fields.find(f=>f.dataset.map==='enabled').checked)return;const spec={column:col};fields.filter(f=>f.dataset.map!=='enabled').forEach(f=>spec[f.dataset.map]=f.value);if(importKind==='facs'&&!spec.panel)spec.panel=$('#import-panel-name').value.trim();measurements.push(spec)});const mapping={sheet:stage.sheet,id_column:$('#id-col').value,group_column:$('#group-col').value,experiment_column:$('#exp-col').value,weeks_column:$('#weeks-col').value,diet_column:$('#diet-col').value,replicate_column:$('#rep-col').value,measurements};if(stage.facs){mapping.facs_reviewed=$('#facs-reviewed').checked;mapping.sample_rows=[...document.querySelectorAll('[data-sample-row]:checked')].map(el=>({row:Number(el.dataset.sampleRow),mouse_id:document.querySelector(`[data-sample-id="${el.dataset.sampleRow}"]`).value,group:document.querySelector(`[data-sample-group="${el.dataset.sampleRow}"]`).value}));mapping.facs_statistic=$('#facs-statistic')?.value;mapping.facs_unit=$('#facs-unit')?.value;}mapping.metadata_only=importKind==='meta'&&$('#metadata-only').checked;if(mapping.metadata_only)mapping.measurements=[];mapping.allow_new_mice=$('#import-allow-new').checked;return mapping;}
function invalidateImportReview(event){
 if(event?.target.id==='import-reason'){
  if(event.target.value.trim())importFieldError('#import-reason','#import-reason-error','');
  return;
 }
 $('#import-validation').classList.remove('has-errors');
 for(const el of $('#mapping').querySelectorAll('[aria-invalid="true"]:not(#import-reason)'))el.removeAttribute('aria-invalid');
 importReview=null;$('#commit-import').disabled=true;$('#import-validation').innerHTML='<p>Run validation after choosing columns and sample IDs.</p>';}
$('#mapping').addEventListener('input',invalidateImportReview);
$('#mapping').addEventListener('change',invalidateImportReview);
async function validateImport(){
 if(!stage||busy)return;const uid=stage.upload_id;
 try{busy=true;$('#validate-import').disabled=true;importReview=null;$('#commit-import').disabled=true;
 const mapping=importMapping(),signature=JSON.stringify(mapping);
 const requiredFields=[['#id-col',!mapping.id_column,'Select the Mouse ID column.'],
  ['#facs-statistic',stage.facs?.needs_statistic&&!mapping.facs_statistic?.trim(),'Enter the calculated statistic name.'],
  ['#facs-unit',stage.facs?.needs_statistic&&!mapping.facs_unit?.trim(),'Enter the calculated statistic unit.']];
 const missing=requiredFields.filter(([,invalid])=>invalid);
 if(missing.length){
  for(const [selector] of missing)$(selector).setAttribute('aria-invalid','true');
  $(missing[0][0]).focus();
  throw Error(missing.map(([, ,message])=>message).join(' '));
 }
 const r=await api('/import/review','POST',{upload_id:uid,mapping});
 if(!stage||stage.upload_id!==uid||signature!==JSON.stringify(importMapping())){invalidateImportReview();return}
 $('#import-validation').innerHTML=`<h3>${r.ok?'Ready to import':'Resolve issues before importing'}</h3><p>${r.rows_reviewed} mouse rows · ${r.observations} measurements · ${r.new_mouse_count} new mice · ${r.missing_count} blank values · ${r.issue_count} issues</p>`+
 (r.issues.length?table(['Issue','Source row','Column','Mouse ID','Details'],r.issues.map(x=>[esc(({duplicate_file:'Duplicate in file',duplicate_database:'Already in database',unknown_mouse:'Unknown Mouse ID',mouse_id:'Invalid Mouse ID',roster_mismatch:'Roster mismatch',group_mismatch:'Group mismatch',invalid_value:'Invalid value',definition:'Metric definition',mapping:'Sample mapping',timepoint:'Missing timepoint',empty:'Empty selection'})[x.code]||x.code),x.row??'—',esc(x.column),esc(x.mouse_id),esc(x.message)]))+(r.issue_count>300?'<p>First 300 issues shown. Correct these and validate again.</p>':''):'')+
 (r.new_mice.length?'<h4>IDs not found in the current roster</h4>'+table(['Source row','Mouse ID','Group','Similar IDs (suggestions only)'],r.new_mice.map(x=>[x.row,esc(x.mouse_id),esc(x.group),esc(x.suggestions.join(', '))])):'')+
 '<h4>Normalized import preview (first 100 observations)</h4>'+table(['Source row','Mouse ID','Metric','Unit','Timepoint','Replicate','Value'],r.preview.map(x=>[x.row,esc(x.mouse_id),esc(x.metric),esc(x.unit),esc(x.timepoint),esc(x.replicate),x.value===null?'Missing':esc(x.value)]));
 $('#import-validation').classList.toggle('has-errors',!r.ok);
 for(const issue of r.issues){
  const index=stage.headers.indexOf(issue.column);
  let field=null;
  if(issue.code==='mapping')field=$('#facs-reviewed');
  else if(issue.row && ['mouse_id','unknown_mouse','group_mismatch','roster_mismatch'].includes(issue.code)){
   const attr=issue.column==='group'?'data-sample-group':'data-sample-id';
   field=document.querySelector('['+attr+'="'+Number(issue.row)+'"]');
  }else if(issue.code==='definition' && index>=0){
   const fields=document.querySelectorAll('[data-index="'+index+'"][data-map]');
   for(const el of fields)if(['unit','name','organ'].includes(el.dataset.map)&&!el.value.trim())el.setAttribute('aria-invalid','true');
  }
  if(field)field.setAttribute('aria-invalid','true');
 }
 if(!r.ok)$('#import-validation').scrollIntoView({block:'nearest'});
 if(r.ok)importReview={token:r.review_token,signature,uid};$('#commit-import').disabled=!importReview;
 }catch(e){$('#import-validation').classList.add('has-errors');$('#import-validation').textContent=e.message;$('#import-validation').scrollIntoView({block:'nearest'})}finally{busy=false;$('#validate-import').disabled=false}
};
$('#validate-import').onclick=validateImport;
async function commitImport(){
 if(!stage||busy||!importReview)return;
 if(!$('#import-reason').value.trim()){
  const text=document.documentElement.lang==='ko'?'저장하려면 가져오기 사유를 입력하세요.':'Enter an import reason before saving.';
  importFieldError('#import-reason','#import-reason-error',text);$('#import-reason').focus();return;
 }
 try{const mapping=importMapping();if(importReview.uid!==stage.upload_id||importReview.signature!==JSON.stringify(mapping)){invalidateImportReview();return}
 busy=true;$('#commit-import').disabled=true;
 const result=await api('/import','POST',{upload_id:stage.upload_id,mapping,reason:$('#import-reason').value,review_token:importReview.token});
 stage=null;importReview=null;importDrafts[importKind]=null;$('#import-reason').value='';renderImportKind();$('#mapping').hidden=true;$('#file').value='';if(example)switchExample(false);await sync(true);notice(`Saved ${result.new_mice} new mice and ${result.measurements} measurements.`)
 }catch(e){invalidateImportReview();$('#import-validation').classList.add('has-errors');$('#import-validation').textContent=e.message;$('#import-validation').scrollIntoView({block:'nearest'})}finally{busy=false;$('#commit-import').disabled=!importReview}
};
$('#commit-import').onclick=commitImport;
$('#template').onclick=()=>{if(importKind==='facs'){download('facs-example-template.csv',csv([{mouse_id:'NEW-001',group:'Group A','CD4_Frequency':'','Treg_Absolute_Count':'','CD25_MFI':''}],['mouse_id','group','CD4_Frequency','Treg_Absolute_Count','CD25_MFI']),'text/csv');return}if($('#metadata-only').checked){download('mouse-metadata-template.csv',csv([{mouse_id:'NEW-001',experiment:'Exp11',diet:'Chow',weeks:'36',group:''}],['mouse_id','experiment','diet','weeks','group']),'text/csv');return}download('example-template.csv',csv([{mouse_id:'NEW-001',group:'Group A',experiment:'Exp11',weeks:'',diet:'',body_weight:'',OGTT_0:'',OGTT_15:'',OGTT_30:'',ITT_0:'',ITT_15:'',liver_weight:'',total_cholesterol:'',LDL_C:'',HDL_C:'',triglycerides:'',fasting_glucose:''}],['mouse_id','group','experiment','weeks','diet','body_weight','OGTT_0','OGTT_15','OGTT_30','ITT_0','ITT_15','liver_weight','total_cholesterol','LDL_C','HDL_C','triglycerides','fasting_glucose']),'text/csv');};
start().catch(e=>{$('#auth-error').textContent=e.message});setInterval(()=>{if(user&&!busy&&!$('#editor').open&&!$('#account-dialog').open&&!$('#rename-dialog').open&&!stage&&!sampleChanges.size)sync(true)},15000);

function renderHomeSummary(dataset){
 const recorded=dataset.measurements.filter(hasRecordedValue);
 const mouseIds=new Set(recorded.map(row=>row.mouse_id));
 const experiments=new Set(dataset.mice.filter(mouse=>mouseIds.has(mouse.mouse_id)).map(mouse=>mouse.experiment).filter(Boolean));
 const cards=[['Mice',mouseIds.size],['Experiments',experiments.size],['Metrics',new Set(recorded.map(row=>row.metric_id)).size],['Recorded values',recorded.length]];
 $('#home-summary').innerHTML=cards.map(([label,n])=>`<section class="home-card"><span>${esc(label)}</span><strong class="home-number">${n.toLocaleString()}</strong></section>`).join('');
}
async function renderHome(){
 if(!user||!data)return;
 renderHomeSummary(data);
 $('#home-fcs').hidden=!user.fcs_access;
 $('#home-recent-fcs').hidden=user.username!=='qa_admin';
 $('#home-files').textContent=user.fcs_access?'Loading…':'FACS is currently limited to QA accounts.';
 if(user.fcs_access)try{const c=await api('/fcs/library');$('#home-fcs-summary').textContent=`${c.files.filter(f=>f.kind==='fcs').length} FCS files · ${c.runs.filter(r=>r.status==='done').length} completed analyses in recent history`;
 $('#home-files').innerHTML=user.username!=='qa_admin'?'':c.files.slice(0,8).map(f=>`<div class="home-file"><b>${esc(f.filename)}</b><span>${esc(f.username||'')} · ${esc(new Date(f.created_at).toLocaleString('en-GB'))}</span></div>`).join('')||'No FCS files yet.';
 }catch(e){$('#home-files').textContent=e.message}
}
$('#home-refresh').onclick=async()=>{await sync(true);await renderHome()};

let experimentRequest=0,experimentView=null;
async function renderExperiments(){
 const request=++experimentRequest,selected=$('#workspace-experiment').value;
 $('#experiment-message').textContent='Loading…';
 try{const d=await api('/experiments?experiment='+encodeURIComponent(selected));if(request!==experimentRequest)return;experimentView=d;
 options($('#workspace-experiment'),d.experiments,'Select an experiment',selected);
 $('#experiment-link-panel').hidden=!d.experiment||!d.fcs_enabled||user.role==='viewer';
 $('#experiment-message').textContent=d.experiment?`${d.mice.length} mice · ${d.spreadsheets.length} spreadsheets`: 'Select an experiment. Register mouse metadata in Import to add a new Exp.';
 if(!d.experiment){$('#experiment-content').replaceChildren();return}
 const fileName=id=>d.available_files?.find(f=>f.id===id)?.filename||id;
 $('#experiment-content').innerHTML='<h3>Mice</h3>'+table(['Mouse ID','Group','Diet','Weeks'],d.mice.map(m=>[esc(m.mouse_id),esc(m.group_name),esc(m.diet),esc(m.weeks)]))+
 '<h3>Source spreadsheets</h3>'+ (d.spreadsheets.length?table(['File','Imported'],d.spreadsheets.map(f=>[`<a href="/api/source/${esc(f.id)}">${esc(f.filename)}</a>`,esc(new Date(f.created_at).toLocaleString('en-GB'))])):'<p>No linked imported spreadsheets yet.</p>')+
 (d.fcs_enabled?'<h3>FCS / WSP files</h3>'+(d.files.length?table(['File','Type'],d.files.map(f=>[`<a href="/api/fcs/source/${esc(f.id)}">${esc(f.filename)}</a>`,esc(f.kind.toUpperCase())])):'<p>No linked FCS/WSP files. Use Link a file below.</p>')+
 '<h3>Analyses</h3><p>Combined analyses may include mice from other experiments.</p>'+(d.analyses.length?table(['Sample / Combine','Mouse ID','Organ','Status',''],d.analyses.map(a=>[esc(a.combined_name||fileName(a.fcs_id)),esc(a.mouse_id||'Not linked'),esc(a.organ),esc(a.status),`<button data-open-analysis="${esc(a.id)}">Open in FACS</button>`])):'<p>No related analyses.</p>')+
 '<h3>Manual file links</h3>'+ (d.links.length?table(['File','Mouse ID',''],d.links.map(l=>[esc(fileName(l.file_id)),esc(l.mouse_id||'Whole experiment'),user.role==='viewer'?'':`<button data-remove-link="${l.id}">Remove link</button>`])):'<p>No manual links.</p>'):'<p>FACS files and analyses are restricted to QA accounts.</p>');
 if(d.fcs_enabled){options($('#experiment-file'),d.available_files.map(f=>({value:f.id,label:f.filename+' · '+f.id.slice(0,8)})),'Select a file');options($('#experiment-mouse'),d.mice.map(m=>m.mouse_id),'Whole experiment (no individual mouse)');}
 }catch(e){$('#experiment-message').textContent=e.message}
}
$('#workspace-experiment').onchange=renderExperiments;$('#experiments-refresh').onclick=renderExperiments;
$('#experiment-link-save').onclick=async()=>{const b=$('#experiment-link-save');b.disabled=true;try{await api('/fcs/experiment-link','POST',{experiment:$('#workspace-experiment').value,file_id:$('#experiment-file').value,mouse_id:$('#experiment-mouse').value,reason:$('#experiment-link-reason').value});await renderExperiments();$('#experiment-message').textContent='File linked. Original unchanged.'}catch(e){$('#experiment-message').textContent=e.message}finally{b.disabled=false}};
$('#experiment-content').onclick=async e=>{try{const open=e.target.closest('[data-open-analysis]');if(open){document.querySelector('nav [data-page="fcs"]').click();await fcsRefresh();if(![...$('#fcs-runs').options].some(o=>o.value===open.dataset.openAnalysis)){const run=await api('/fcs/runs/'+open.dataset.openAnalysis);fcsCatalog.runs.unshift(run);$('#fcs-runs').add(new Option('Analysis '+run.id,run.id));}$('#fcs-runs').value=open.dataset.openAnalysis;await fcsLoadRun();return}const remove=e.target.closest('[data-remove-link]');if(remove){const link=experimentView.links.find(l=>String(l.id)===remove.dataset.removeLink);await api('/fcs/experiment-link','POST',{...link,remove:true,reason:$('#experiment-link-reason').value});await renderExperiments()}}catch(error){$('#experiment-message').textContent=error.message}};
function updateMetadataMode(){const only=importKind==='meta'&&$('#metadata-only').checked;$('#column-mapping').hidden=only;}
$('#mapping').addEventListener('change',updateMetadataMode);
