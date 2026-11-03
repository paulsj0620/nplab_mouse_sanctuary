'use strict';
let fcsCatalog={files:[],runs:[]},fcsRun=null,fcsGate=-1,fcsPlot=null,fcsBusy=false,fcsPlotRequest=0,fcsRunRequest=0,fcsScreenPoints=[];
function fcsTreeOrder(gates,parent=-1){return gates.filter(g=>g.parent_index===parent).flatMap(g=>[g,...fcsTreeOrder(gates,g.index)])}
function fcsRunLabel(r){let spec={};try{spec=JSON.parse(r.edit_spec||'{}')}catch{}return spec.combine_name?('Combined · '+spec.combine_name):(fcsCatalog.files.find(f=>f.id===r.fcs_id)?.filename||'Sample')}
const fcsEl=id=>document.getElementById(id);
function fcsStatus(message){fcsEl('fcs-run-status').textContent=message;fcsEl('fw-analysis-message').textContent=message;}
async function fcsRefresh(){
 if(fcsDraft){fcsStatus('Save or cancel the gate edit before refreshing.');return;}
 const selectedRun=fcsEl('fcs-runs').value;const catalog=await api('/fcs/library');fcsCatalog=catalog;
 fcsEl('fcs-backup').textContent=catalog.backup;
 const mine=fcsEl('fcs-mine').checked;
 fcsEl('fcs-library').innerHTML=table(['Original file','Storage','Uploaded by','Uploaded','Size','SHA-256',''],catalog.files.filter(f=>!mine||f.owner===user.id).map(f=>[esc(f.filename),f.storage==='smb'?'SMB original (linked)':'Local copy',esc(f.username),esc(new Date(f.created_at).toLocaleString('en-GB')),(f.size/1024/1024).toFixed(1)+' MB',`<span class="fcs-hash">${esc(f.sha256)}</span>`,`<a class="button" href="/api/fcs/source/${f.id}">Download original</a>`]));
 options(fcsEl('fcs-sample'),catalog.files.filter(f=>f.kind==='fcs').map(f=>({value:f.id,label:f.filename+' · '+f.username})),'Select an FCS file');
 options(fcsEl('fcs-workspace'),catalog.files.filter(f=>f.kind==='wsp').map(f=>({value:f.id,label:f.filename})),'Acquisition channels only');
 options(fcsEl('fcs-runs'),catalog.runs.map(r=>({value:r.id,label:fcsRunLabel(r)+' · '+r.status+' · '+new Date(r.created_at).toLocaleString('en-GB')+' · '+r.username})),'Select an analysis',selectedRun);
 const reference=fcsEl('fw-reference-workspace').value;
 options(fcsEl('fw-reference-workspace'),catalog.files.filter(f=>f.kind==='wsp').map(f=>({value:f.id,label:f.filename})),'Select a WSP file',reference);
 fwRenderSamples();
}
document.querySelector('[data-page="fcs"]').addEventListener('click',()=>fcsRefresh().catch(e=>fcsStatus(e.message)));
fcsEl('fcs-refresh').onclick=()=>fcsRefresh().catch(e=>fcsStatus(e.message));fcsEl('fcs-mine').onchange=()=>fcsRefresh().catch(e=>fcsStatus(e.message));
fcsEl('fcs-upload').onclick=async()=>{
 if(fcsBusy)return;const files=[...fcsEl('fcs-files').files];if(!files.length){fcsEl('fcs-upload-status').textContent='Select FCS or WSP files first.';return}
 fcsBusy=true;fcsEl('fcs-upload').disabled=true;
 try{for(const file of files){
  const key='fcs-transfer:'+JSON.stringify([user.id,file.name,file.size,file.lastModified]);let transfer=null;
  const old=localStorage.getItem(key);if(old){try{transfer=await api('/fcs/transfers/'+old)}catch(e){if(e.status!==404)throw e;localStorage.removeItem(key)}}
  if(!transfer){transfer=await api('/fcs/transfers','POST',{filename:file.name,size:file.size});localStorage.setItem(key,transfer.id)}
  let offset=transfer.received;
  while(offset<file.size){
   const body=file.slice(offset,Math.min(offset+2*1024*1024,file.size));
   const response=await fetch('/api/fcs/chunks/'+transfer.id+'?offset='+offset,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-CSRF-Token':user.csrf},body});
   const result=await response.json();if(!response.ok)throw Error(result.error||'Upload failed. Select the same file again to resume.');offset=result.received;
   fcsEl('fcs-progress').value=100*offset/file.size;fcsEl('fcs-upload-status').textContent=`${file.name}: ${(offset/1024/1024).toFixed(1)} / ${(file.size/1024/1024).toFixed(1)} MB`;
  }
  fcsEl('fcs-upload-status').textContent=file.name+': verifying original and local mirror…';
  await api('/fcs/finish','POST',{id:transfer.id});localStorage.removeItem(key);
 }
 fcsEl('fcs-upload-status').textContent=`${files.length} original file(s) preserved and available to QA accounts.`;fcsEl('fcs-files').value='';await fcsRefresh();
 }catch(e){fcsEl('fcs-upload-status').textContent=e.message+' Original files on your computer are unchanged. Reselect the same file to resume.'}
 finally{fcsBusy=false;fcsEl('fcs-upload').disabled=false}
};
fcsEl('fcs-analyze').onclick=async()=>{if(fcsBusy)return;fcsEl('fcs-analyze').disabled=true;try{
 const r=await api('/fcs/analyze','POST',{fcs_id:fcsEl('fcs-sample').value,wsp_id:fcsEl('fcs-workspace').value,mouse_id:fcsEl('fcs-mouse').value.trim(),organ:fcsEl('fcs-organ').value.trim()});
 fcsEl('fw-analysis-dialog').close();await fcsRefresh();fcsEl('fcs-runs').value=r.id;await fcsLoadRun();
 }catch(e){fcsStatus(e.message)}finally{fcsEl('fcs-analyze').disabled=false}};
fcsEl('fcs-runs').onchange=()=>fcsLoadRun().catch(e=>fcsStatus(e.message));
async function fcsLoadRun(){
 if(fcsDraft){fcsStatus('Save or cancel the gate edit before changing analysis.');return}
 fcsCancelEdit();
 const id=fcsEl('fcs-runs').value,request=++fcsRunRequest;++fcsPlotRequest;fcsEl('fcs-results').hidden=true;fcsRun=null;fcsPlot=null;fwPlotLayout();fwCollapsed.clear();fwRenderTree();fwUpdate();
 if(!id)return;
 const r=await api('/fcs/runs/'+id);if(request!==fcsRunRequest)return;fcsRun=r;fwUpdate();
 fcsStatus(r.status==='done'?'Analysis complete. Original files and existing summary data are unchanged.':r.status==='failed'?r.error:r.status==='running'?'Analyzing all events…':'Queued for analysis…');
 if(r.status!=='done')return;
 fcsGate=-1;fwShowRun(r);
 await fcsDrawRequest();
}
function fwShowRun(r){
 const result=r.result;fcsEl('fcs-results').hidden=false;
 fcsEl('fcs-provenance').textContent=`${result.engine} · ${result.events.toLocaleString('en-GB')} events · ${result.base_channel_count} original channels · Mouse ${r.mouse_id||'not linked'} · ${r.organ} · ${result.space}`;
 fcsEl('fcs-comparison').textContent=r.wsp_id?`${result.gates.length} gates · ${result.gates.filter(g=>g.flowjo_count!==null).length} unchanged gates with FlowJo references · ${result.different_gate_counts} reference counts differ. Review these differences before using recomputed results. WSP internal sample ID: ${result.workspace_sample_id} (${result.workspace_sample_count} samples referenced; only this FCS analyzed).`:'No workspace attached. Acquisition coordinates are used; no WSP compensation or transforms are applied.';
 fcsEl('fcs-notes').innerHTML=result.notes.filter(n=>!n.includes('Combined FlowJo WSP export is not supported')).map(n=>'<li>'+esc(n)+'</li>').join('')+`<li>FCS SHA-256: ${esc(result.source_fcs_sha256)}</li><li>WSP SHA-256: ${esc(result.source_wsp_sha256||'None')}</li>`;
 if(result.combined){fcsEl('fcs-comparison').textContent=`Combined: ${result.sources.length} FCS files · common gates from template analysis ${result.template_run}. No single-sample FlowJo count comparison.`;fcsEl('fcs-notes').innerHTML=result.notes.filter(n=>!n.includes('Combined FlowJo WSP export is not supported')).map(n=>'<li>'+esc(n)+'</li>').join('')+result.sources.map(s=>`<li>${esc(s.filename)} · ${s.events.toLocaleString()} events · SHA-256 ${esc(s.sha256)}</li>`).join('')}
 if(result.gate_edit?.base_run)fcsEl('fcs-comparison').textContent+=' QA edited version. Changed gates and descendants have no FlowJo reference comparison. Based on analysis '+result.gate_edit.base_run+'.';
 const choices=result.channels.map((c,i)=>({value:String(i),label:c.label}));options(fcsEl('fcs-x'),choices,'','0');options(fcsEl('fcs-y'),choices,'','3');
 fwRenderTree();fwUpdate();
 fcsEl('fcs-counts').innerHTML=table(['Gate path','Recomputed events','FlowJo stored events','Difference','% of parent'],result.gates.map(g=>[esc([...g.path.slice(1),g.name].join(' / ')),g.count,g.flowjo_count??'—',g.difference??'—',g.frequency_parent?.toFixed(3)??'—']));
}
fcsEl('fcs-gates').onclick=async e=>{const toggle=e.target.closest('[data-fw-toggle]');if(toggle){const i=Number(toggle.dataset.fwToggle);fwCollapsed.has(i)?fwCollapsed.delete(i):fwCollapsed.add(i);fwRenderTree();return}const button=e.target.closest('[data-fcs-gate]');if(!button||!fcsRun)return;if(fcsDraft){fcsStatus('Save or cancel the gate edit before changing population.');return}fcsGate=Number(button.dataset.fcsGate);const gate=fcsRun.result.gates[fcsGate];document.querySelectorAll('[data-fcs-gate]').forEach(b=>b.classList.toggle('selected',b===button));if(gate){fcsEl('fcs-x').value=String(gate.axes[0]);if(gate.axes.length>1){fcsEl('fcs-y').value=String(gate.axes[1]);if(fcsEl('fcs-mode').value==='histogram')fcsEl('fcs-mode').value='scatter'}else fcsEl('fcs-mode').value='histogram'}try{await fcsDrawRequest()}catch(error){fcsStatus(error.message)}};
for(const id of ['fcs-x','fcs-y'])fcsEl(id).onchange=()=>fcsDrawRequest().catch(e=>fcsStatus(e.message));fcsEl('fcs-mode').onchange=()=>{if(fcsPlot)fcsDraw()};
async function fcsDrawRequest(parentOnly=false){
 if(!fcsRun||fcsRun.status!=='done')return false;
 const request=++fcsPlotRequest;fcsEl('fcs-plot-status').textContent='Preparing plot…';let timer;
 try{
  const plot=await Promise.race([
   api('/fcs/plot','POST',{id:fcsRun.id,gate:fcsGate,parent_only:parentOnly,x:Number(fcsEl('fcs-x').value),y:Number(fcsEl('fcs-y').value)}),
   new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Plot preparation timed out. Please try again.')),30000)})
  ]);
  if(request!==fcsPlotRequest)return false;
  fcsPlot=plot;fcsDraw();fwUpdate();return true;
 }catch(e){if(request===fcsPlotRequest)fcsEl('fcs-plot-status').textContent=e.message;throw e}
 finally{clearTimeout(timer)}
}
function fcsDraw(){
 const p=fcsPlot,canvas=fcsEl('fcs-canvas'),ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=86,R=W-32,T=50,B=H-90,mode=fcsEl('fcs-mode').value,gate=p.gate;
 const xi=Number(fcsEl('fcs-x').value),yi=Number(fcsEl('fcs-y').value);fcsScreenPoints=[];ctx.clearRect(0,0,W,H);ctx.fillStyle='white';ctx.fillRect(0,0,W,H);
 const extent=arr=>{let lo=Infinity,hi=-Infinity;for(const n of arr){if(Number.isFinite(n)){lo=Math.min(lo,n);hi=Math.max(hi,n)}}if(!Number.isFinite(lo))return[0,1];const pad=(hi-lo||1)*.05;return[lo-pad,hi+pad]};
 const geometryX=[],geometryY=[];if(gate&&gate.axes[0]===xi&&(mode==='histogram'||gate.axes[1]===yi)){if(gate.vertices&&mode!=='histogram'){for(const v of gate.vertices){geometryX.push(v[0]);geometryY.push(v[1])}}else{for(const n of gate.bounds[0]||[])if(n!==null)geometryX.push(n);for(const n of gate.bounds[1]||[])if(n!==null)geometryY.push(n)}}
 const [xmin,xmax]=extent([...p.x,...geometryX]),[ymin,ymax]=extent([...p.y,...geometryY]),X=x=>L+(x-xmin)/(xmax-xmin)*(R-L),Y=y=>B-(y-ymin)/(ymax-ymin)*(B-T);
 fcsView={X,Y,invX:px=>xmin+(px-L)/(R-L)*(xmax-xmin),invY:py=>ymin+(B-py)/(B-T)*(ymax-ymin)};
 ctx.strokeStyle='#222';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(L,T);ctx.lineTo(L,B);ctx.lineTo(R,B);ctx.stroke();ctx.font='12px Arial';ctx.fillStyle='#333';ctx.textAlign='center';
 const fmt=n=>Math.abs(n)>=10000||Math.abs(n)>0&&Math.abs(n)<.001?n.toExponential(1):Number(n.toPrecision(4)).toString();
 for(let i=0;i<=5;i++){let x=xmin+(xmax-xmin)*i/5;ctx.fillText(fmt(x),X(x),B+20);if(mode!=='histogram'){let y=ymin+(ymax-ymin)*i/5;ctx.textAlign='right';ctx.fillText(fmt(y),L-10,Y(y)+4);ctx.textAlign='center'}}
 ctx.font='14px Arial';ctx.fillText(p.x_label,(L+R)/2,H-37);ctx.save();ctx.translate(19,(T+B)/2);ctx.rotate(-Math.PI/2);ctx.fillText(mode==='histogram'?'Displayed event count':p.y_label,0,0);ctx.restore();ctx.font='bold 15px Arial';ctx.fillText(gate?gate.name:'All events',(L+R)/2,26);
 ctx.save();ctx.beginPath();ctx.rect(L,T,R-L,B-T);ctx.clip();
 if(mode==='histogram'){
  const bins=80,all=new Array(bins).fill(0),hits=new Array(bins).fill(0);for(let i=0;i<p.x.length;i++){const b=Math.min(bins-1,Math.max(0,Math.floor((p.x[i]-xmin)/(xmax-xmin)*bins)));all[b]++;if(p.hit[i])hits[b]++}
  const max=Math.max(1,...all);for(let i=0;i<bins;i++){let x=L+i*(R-L)/bins,w=(R-L)/bins;ctx.fillStyle='#ddd';ctx.fillRect(x,B-all[i]/max*(B-T),w,all[i]/max*(B-T));ctx.fillStyle='#333';ctx.fillRect(x,B-hits[i]/max*(B-T),w,hits[i]/max*(B-T))}
  ctx.restore();ctx.font='12px Arial';ctx.textAlign='right';for(let i=0;i<=5;i++)ctx.fillText(Math.round(max*i/5),L-10,B-i/5*(B-T)+4);ctx.save();ctx.beginPath();ctx.rect(L,T,R-L,B-T);ctx.clip();
 }else{
  const bins=new Map();if(mode==='density')for(let i=0;i<p.x.length;i++){const k=Math.floor(X(p.x[i])/5)+','+Math.floor(Y(p.y[i])/5);bins.set(k,(bins.get(k)||0)+1)}const max=Math.max(1,...bins.values());
  for(let pass=0;pass<2;pass++)for(let i=0;i<p.x.length;i++){if(p.hit[i]!==pass)continue;let x=X(p.x[i]),y=Y(p.y[i]);ctx.fillStyle=pass?'rgba(25,65,95,.55)':'rgba(150,150,150,.25)';if(mode==='density'){const n=bins.get(Math.floor(x/5)+','+Math.floor(y/5))||1;ctx.fillStyle=`hsl(${240-240*Math.log1p(n)/Math.log1p(max)},75%,45%)`}ctx.fillRect(x,y,1.5,1.5);fcsScreenPoints.push({x,y,i})}
 }
 const axisMatch=gate&&gate.axes[0]===xi&&(mode==='histogram'||gate.axes[1]===yi);
 if(axisMatch){ctx.strokeStyle='#bd3333';ctx.lineWidth=2;ctx.setLineDash([6,3]);
  if(gate.kind==='PolygonGate'&&mode!=='histogram'){ctx.beginPath();gate.vertices.forEach((v,i)=>i?ctx.lineTo(X(v[0]),Y(v[1])):ctx.moveTo(X(v[0]),Y(v[1])));ctx.closePath();ctx.stroke()}
  else if(gate.kind==='RectangleGate'){const bounds=gate.bounds;let x0=bounds[0][0]??xmin,x1=bounds[0][1]??xmax,y0=mode==='histogram'?ymin:bounds[1]?.[0]??ymin,y1=mode==='histogram'?ymax:bounds[1]?.[1]??ymax;ctx.strokeRect(X(x0),Y(y1),X(x1)-X(x0),Y(y0)-Y(y1))}
 }
 ctx.restore();ctx.setLineDash([]);ctx.font='11px Arial';ctx.fillStyle='#555';ctx.textAlign='left';ctx.fillText(`Preview: ${p.displayed.toLocaleString()} / ${p.parent_count.toLocaleString()} parent events · seed ${p.seed} · ${mode}`,L,H-12);
 fcsPaintDraft();
 fwSavePlot();
 fcsEl('fcs-plot-status').textContent=`Showing ${p.displayed.toLocaleString()} of ${p.parent_count.toLocaleString()} parent events (maximum 20,000). Gate counts use all events. ${p.space}. ${gate&&!axisMatch?'Gate boundary hidden: choose the gate’s own axes to show it.':''} ${p.nonfinite_in_preview?'Nonfinite preview coordinates omitted: '+p.nonfinite_in_preview:''}`;
}
fcsEl('fcs-canvas').onmousemove=e=>{if(!fcsPlot)return;const c=e.currentTarget,r=c.getBoundingClientRect(),x=(e.clientX-r.left)*c.width/r.width,y=(e.clientY-r.top)*c.height/r.height;let best=null,distance=64;for(const point of fcsScreenPoints){const d=(point.x-x)**2+(point.y-y)**2;if(d<distance){best=point;distance=d}}fcsEl('fcs-point').textContent=best?`${fcsEventLabel(fcsPlot.indices[best.i])} · X=${fcsPlot.x[best.i].toPrecision(6)} · Y=${fcsPlot.y[best.i].toPrecision(6)} · ${fcsPlot.hit[best.i]?'Selected population':'Parent only'}`:''};
fcsEl('fcs-png').onclick=()=>{if(!fcsPlot)return;fcsEl('fcs-canvas').toBlob(blob=>{const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='fcs-'+fcsRun.id+'.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})};
fcsEl('fcs-csv').onclick=()=>{if(!fcsRun?.result)return;if(fcsRun.result.combined){const rows=fcsRun.result.gates.flatMap(g=>[{gate:[...g.path.slice(1),g.name].join(' / '),source:'All combined',run_id:fcsRun.id,count:g.count},...(g.source_counts||[]).map(s=>({gate:[...g.path.slice(1),g.name].join(' / '),source:s.filename,run_id:s.run_id,count:s.count}))]);download('combined-gates-'+fcsRun.id+'.csv',csv(rows,['gate','source','run_id','count']));return;}const r=fcsRun.result,rows=r.gates.map(g=>({gate_path:[...g.path.slice(1),g.name].join(' / '),count:g.count,flowjo_stored_count:g.flowjo_count,difference:g.difference,frequency_parent:g.frequency_parent,parent_count:g.parent_count,mouse_id:fcsRun.mouse_id,organ:fcsRun.organ,analysis_id:fcsRun.id,engine:r.engine,fcs_sha256:r.source_fcs_sha256,wsp_sha256:r.source_wsp_sha256}));download('fcs-gates-'+fcsRun.id+'.csv',csv(rows,['gate_path','count','flowjo_stored_count','difference','frequency_parent','parent_count','mouse_id','organ','analysis_id','engine','fcs_sha256','wsp_sha256']))};
setInterval(async()=>{if(!user?.fcs_access||fcsEl('fcs').hidden||fcsBusy)return;try{if(fcsRun&&['queued','running'].includes(fcsRun.status)){await fcsRefresh();await fcsLoadRun()}}catch(e){fcsStatus(e.message)}},2500);

let fcsDraft=null,fcsView=null,fcsDrag=null,fcsEditStarting=false;
function fcsCancelEdit(){fcsDraft=null;fcsDrag=null;fcsEl('fcs-edit-panel').hidden=true;fcsEl('fcs-cancel-edit').hidden=true;for(const id of ['fcs-x','fcs-y','fcs-mode','fcs-runs'])fcsEl(id).disabled=false;if(fcsPlot)fcsDraw();fwUpdate()}
function fcsPaintDraft(){if(!fcsDraft||!fcsView)return;const ctx=fcsEl('fcs-canvas').getContext('2d'),v=fcsDraft.vertices,{X,Y}=fcsView;ctx.save();ctx.strokeStyle='#1463ad';ctx.fillStyle='#1463ad';ctx.lineWidth=2;ctx.setLineDash([]);if(v.length){ctx.beginPath();v.forEach((p,i)=>i?ctx.lineTo(X(p[0]),Y(p[1])):ctx.moveTo(X(p[0]),Y(p[1])));if(v.length>=3)ctx.closePath();ctx.stroke();for(const p of v){ctx.fillRect(X(p[0])-4,Y(p[1])-4,8,8)}}ctx.restore()}
async function fcsBeginEdit(kind,editing=false){
 if(!fcsRun||fcsRun.status!=='done')return;
 if(fcsDraft||fcsEditStarting){fcsStatus('Finish the current gate operation first.');return}
 const selected=fcsRun.result.gates[fcsGate];
 if(editing&&(!selected||selected.axes.length!==2)){fcsStatus('Select a 2D gate to edit.');return}
 fcsCancelEdit();
 if(editing){kind=selected.kind;fcsEl('fcs-x').value=selected.axes[0];fcsEl('fcs-y').value=selected.axes[1]}
 const axes=[Number(fcsEl('fcs-x').value),Number(fcsEl('fcs-y').value)];if(axes[0]===axes[1]){fcsStatus('Select two different axes.');return}
 fcsEl('fcs-mode').value='scatter';
 const context={run:fcsRun.id,gate:fcsGate,slot:fwActivePlot};
 fcsEditStarting=true;fcsStatus('Preparing gate editor…');
 let ready;
 try{ready=await fcsDrawRequest(!editing)}finally{fcsEditStarting=false}
 if(!ready||fcsRun?.id!==context.run||fcsGate!==context.gate||fwActivePlot!==context.slot)return;
 let vertices=[];
 if(editing){if(kind==='PolygonGate')vertices=selected.vertices.map(v=>[...v]);else{const b=selected.bounds;if(b.flat().some(x=>x===null)){fcsStatus('This gate has an open boundary. Draw a new finite rectangle instead.');return}vertices=[[b[0][0],b[1][0]],[b[0][1],b[1][0]],[b[0][1],b[1][1]],[b[0][0],b[1][1]]]}}
 fcsDraft={run:fcsRun.id,target:editing?fcsGate:-1,parent_index:editing?selected.parent_index:fcsGate,kind,axes,vertices};
 fcsEl('fcs-gate-name').value=editing?selected.name:'';fcsEl('fcs-edit-reason').value='';fcsEl('fcs-edit-panel').hidden=false;fcsEl('fcs-cancel-edit').hidden=false;
 for(const id of ['fcs-x','fcs-y','fcs-mode','fcs-runs'])fcsEl(id).disabled=true;
 fcsEl('fcs-edit-help').textContent=(kind==='RectangleGate'?'Drag to draw a rectangle; drag its corner handles to resize.':'Click to add vertices; drag square handles to move them. Save closes the polygon.')+' Parent: '+(fcsRun.result.gates[fcsDraft.parent_index]?.name||'All events')+'. All events will be recalculated; this preview is sampled.';
 fcsDraw();fwUpdate();fcsStatus('Gate editor ready. Draw on the selected plot; save when finished.');
}
fcsEl('fcs-new-rect').onclick=()=>fcsBeginEdit('RectangleGate').catch(e=>fcsStatus(e.message));
fcsEl('fcs-new-poly').onclick=()=>fcsBeginEdit('PolygonGate').catch(e=>fcsStatus(e.message));
fcsEl('fcs-edit-gate').onclick=()=>fcsBeginEdit(null,true).catch(e=>fcsStatus(e.message));
fcsEl('fcs-cancel-edit').onclick=()=>{fcsCancelEdit();fcsDrawRequest().catch(e=>fcsStatus(e.message))};
function fcsPointer(e){const c=fcsEl('fcs-canvas'),r=c.getBoundingClientRect(),px=(e.clientX-r.left)*c.width/r.width,py=(e.clientY-r.top)*c.height/r.height;return {px,py,value:[fcsView.invX(Math.max(86,Math.min(c.width-32,px))),fcsView.invY(Math.max(50,Math.min(c.height-90,py)))]}}
const editorCanvas=fcsEl('fcs-canvas');
editorCanvas.addEventListener('pointerdown',e=>{if(!fcsDraft||!fcsView)return;const p=fcsPointer(e);if(p.px<86||p.px>editorCanvas.width-32||p.py<50||p.py>editorCanvas.height-90)return;const v=fcsDraft.vertices;let i=v.findIndex(a=>Math.hypot(fcsView.X(a[0])-p.px,fcsView.Y(a[1])-p.py)<12);if(i>=0){fcsDrag={i,opposite:fcsDraft.kind==='RectangleGate'?[...v[(i+2)%4]]:null}}else if(fcsDraft.kind==='RectangleGate'){fcsDrag={i:2,opposite:p.value};fcsDraft.vertices=[p.value,p.value,p.value,p.value]}else if(v.length<128){v.push(p.value);fcsDrag={i:v.length-1}}
 editorCanvas.setPointerCapture(e.pointerId);fcsDraw();e.preventDefault()});
editorCanvas.addEventListener('pointermove',e=>{if(!fcsDraft||!fcsDrag)return;const p=fcsPointer(e).value;if(fcsDrag.opposite){const o=fcsDrag.opposite,x0=Math.min(o[0],p[0]),x1=Math.max(o[0],p[0]),y0=Math.min(o[1],p[1]),y1=Math.max(o[1],p[1]);fcsDraft.vertices=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]}else fcsDraft.vertices[fcsDrag.i]=p;fcsDraw()});
editorCanvas.addEventListener('pointerup',()=>{fcsDrag=null});editorCanvas.addEventListener('pointercancel',()=>{fcsDrag=null});
fcsEl('fcs-save-edit').onclick=async()=>{if(!fcsDraft)return;const button=fcsEl('fcs-save-edit');button.disabled=true;try{const d=fcsDraft,v=d.vertices;if(v.length<3)throw Error('Draw a gate first.');const change={target:d.target,parent_index:d.parent_index,name:fcsEl('fcs-gate-name').value,kind:d.kind,axes:d.axes,vertices:v,bounds:d.kind==='RectangleGate'?[[Math.min(...v.map(p=>p[0])),Math.max(...v.map(p=>p[0]))],[Math.min(...v.map(p=>p[1])),Math.max(...v.map(p=>p[1]))]]:null};const r=await api('/fcs/edit','POST',{base_run:d.run,reason:fcsEl('fcs-edit-reason').value,change});fcsCancelEdit();await fcsRefresh();fcsEl('fcs-runs').value=r.id;await fcsLoadRun()}catch(e){fcsStatus(e.message)}finally{button.disabled=false}};

// Cytometry workspace navigation; stored analyses and gate coordinates are unchanged.
const fwCollapsed=new Set();
function fwRenderSamples(){const query=fcsEl('fw-sample-search').value.toLowerCase();const files=fcsCatalog.files.filter(f=>f.kind==='fcs');fcsEl('fw-sample-count').textContent=files.length;fcsEl('fw-samples').innerHTML=files.filter(f=>f.filename.toLowerCase().includes(query)).map(f=>{const runs=fcsCatalog.runs.filter(r=>r.fcs_id===f.id),latest=runs.find(r=>r.status==='done'&&r.wsp_id)||runs.find(r=>r.status==='done')||runs[0];return `<button class="fw-sample ${fcsRun?.fcs_id===f.id?'selected':''}" data-fw-file="${esc(f.id)}" role="listitem" title="${esc(f.filename)}"><span>♧</span><span><strong>${esc(f.filename)}</strong><small>${esc(f.username)} · ${(f.size/1048576).toFixed(1)} MB</small></span><span class="fw-ready">${latest?esc(latest.status):'Not analyzed'}</span></button>`}).join('')||'<p class="help">No matching samples.</p>'}
function fwRenderTree(){if(!fcsRun?.result){fcsEl('fcs-gates').innerHTML='<p class="help">Select a completed analysis.</p>';return}const gates=fcsRun.result.gates;function row(g,depth){const children=gates.filter(x=>x.parent_index===g.index),open=!fwCollapsed.has(g.index);return `<div class="fw-tree-row" style="--depth:${depth}"><button class="fw-disclosure" ${children.length?`data-fw-toggle="${g.index}" aria-expanded="${open}" aria-label="${open?'Collapse':'Expand'} ${esc(g.name)}"`:'disabled aria-hidden="true" tabindex="-1"'}>${children.length?(open?'▾':'▸'):'·'}</button><button class="fw-gate ${fcsGate===g.index?'selected':''}" data-fcs-gate="${g.index}" title="${esc([...g.path,g.name].join(' / '))}"><span>${esc(g.name)}</span><span class="fw-gate-count">${g.count.toLocaleString()}<small>${g.frequency_parent===null?'—':g.frequency_parent.toFixed(2)+'%'}</small></span></button></div>${children.length?`<div class="fw-tree-children" ${open?'':'hidden'}>${children.map(c=>row(c,depth+1)).join('')}</div>`:''}`}
 fcsEl('fcs-gates').innerHTML=`<div class="fw-tree-row"><button class="fw-gate ${fcsGate<0?'selected':''}" data-fcs-gate="-1"><span>All events</span><span class="fw-gate-count">${fcsRun.result.events.toLocaleString()}<small>100.00%</small></span></button></div>`+gates.filter(g=>g.parent_index<0).map(g=>row(g,0)).join('')}
function fwSelectGate(index){if(fcsDraft){fcsStatus('Save or cancel your gate edit first.');return}const g=fcsRun?.result?.gates[index];if(g){let parent=g.parent_index;while(parent>=0){fwCollapsed.delete(parent);parent=fcsRun.result.gates[parent].parent_index}}fwRenderTree();fcsEl('fcs-gates').querySelector(`[data-fcs-gate="${index}"]`)?.click()}
function fwUpdate(){
 fcsEl('fw-edit-banner').hidden=!fcsDraft;
 fcsEl('fcs-canvas').dataset.editing=String(!!fcsDraft);
 if(fcsDraft)fcsEl('fw-edit-message').textContent=fcsDraft.target>=0?'Editing gate — drag square handles; change its name below.':fcsDraft.kind==='RectangleGate'?'Rectangle ready — drag on the selected plot.':'Polygon ready — click vertices on the selected plot.';
 const r=fcsRun?.status==='done'?fcsRun.result:null,g=r?.gates[fcsGate],file=fcsCatalog.files.find(f=>f.id===fcsRun?.fcs_id);fcsEl('fw-empty').hidden=!!r;fcsEl('fw-sample-title').textContent=r?.combined?r.combined_name:file?file.filename:'No sample selected';fcsEl('fw-gate-title').textContent=g?.name||'All events';
 for(const id of ['fcs-new-rect','fcs-new-poly','fw-parent','fw-root','fcs-png','fcs-csv'])fcsEl(id).disabled=!r||!!fcsDraft;
 fcsEl('fcs-wsp-export').disabled=!r||!fcsRun?.wsp_id||!!fcsDraft||fcsExportBusy;fcsEl('fcs-delete-gate').disabled=!g||!!fcsDraft;fcsEl('fcs-edit-gate').disabled=!g||g.axes.length!==2||!['RectangleGate','PolygonGate'].includes(g.kind)||!!fcsDraft;fcsEl('fw-parent').disabled=!g||!!fcsDraft;
 for(const [id,kind] of [['fcs-new-rect','RectangleGate'],['fcs-new-poly','PolygonGate']])fcsEl(id).setAttribute('aria-pressed',String(fcsDraft?.kind===kind&&fcsDraft.target<0));fcsEl('fcs-edit-gate').setAttribute('aria-pressed',String(!!fcsDraft&&fcsDraft.target>=0));fcsEl('fw-pointer').setAttribute('aria-pressed',String(!fcsDraft));
 const path=[];let cursor=g;while(cursor){path.unshift(cursor);cursor=r.gates[cursor.parent_index]}
 fcsEl('fw-breadcrumb').innerHTML=r?`<button data-fw-jump="-1">${esc(file?.filename||'All events')}</button>`+path.map(p=>`<span>›</span><button data-fw-jump="${p.index}">${esc(p.name)}</button>`).join(''):'Select a sample';
 fcsEl('fw-statistics').innerHTML=r?`<p>${esc(g?.name||'All events')}</p><div class="fw-stat"><span>Events</span><strong>${(g?.count??r.events).toLocaleString()}</strong></div><div class="fw-stat"><span>% of parent</span><strong>${g?(g.frequency_parent===null?'—':g.frequency_parent.toFixed(2)+'%'):'100.00%'}</strong></div><div class="fw-stat"><span>Parent events</span><strong>${(g?.parent_count??r.events).toLocaleString()}</strong></div><div class="fw-stat"><span>Definition</span><strong>${g?(g.edited?'Edited version':'Imported gate'):'Sample'}</strong></div>`:'';
 fwRenderSamples();
}
fcsEl('fw-samples').onclick=async e=>{const b=e.target.closest('[data-fw-file]');if(!b)return;if(fcsDraft){fcsStatus('Save or cancel your gate edit before changing samples.');return}const id=b.dataset.fwFile,runs=fcsCatalog.runs.filter(r=>r.fcs_id===id),r=runs.find(r=>r.status==='done'&&r.wsp_id)||runs.find(r=>r.status==='done')||runs[0];if(r){fcsEl('fcs-runs').value=r.id;try{await fcsLoadRun()}catch(e){fcsStatus(e.message)}}else{fcsEl('fcs-sample').value=id;fcsEl('fw-analysis-dialog').showModal()}};
fcsEl('fw-sample-search').oninput=fwRenderSamples;
fcsEl('fw-breadcrumb').onclick=e=>{const b=e.target.closest('[data-fw-jump]');if(b)fwSelectGate(Number(b.dataset.fwJump))};
fcsEl('fw-parent').onclick=()=>{const g=fcsRun?.result?.gates[fcsGate];fwSelectGate(g?.parent_index??-1)};fcsEl('fw-root').onclick=()=>fwSelectGate(-1);
fcsEl('fw-collapse').onclick=()=>{for(const g of fcsRun?.result?.gates||[])fwCollapsed.add(g.index);fwRenderTree()};fcsEl('fw-expand').onclick=()=>{fwCollapsed.clear();fwRenderTree()};
fcsEl('fw-pointer').onclick=()=>{if(fcsDraft)fcsEl('fcs-cancel-edit').click()};
for(const name of ['library','analysis']){fcsEl(`fw-${name}-open`).onclick=()=>{if(fcsDraft){fcsStatus('Save or cancel your gate edit first.');return}fcsEl(`fw-${name}-dialog`).showModal()};fcsEl(`fw-${name}-close`).onclick=()=>fcsEl(`fw-${name}-dialog`).close()}
fcsEl('fw-empty-open').onclick=()=>fcsEl('fw-library-dialog').showModal();
fwUpdate();


let fcsExportBusy=false,fwReferenceRows=[],fwReferenceWorkspace='',fwReferenceBusy=false,fwReferenceRequest=0,fwReferenceStop=false;
fcsEl('fw-export-close').onclick=()=>fcsEl('fw-export-dialog').close();
fcsEl('fcs-wsp-export').onclick=async()=>{
 if(!fcsRun||fcsDraft||fcsExportBusy)return;
 const run=fcsRun.id;fcsExportBusy=true;fwUpdate();
 fcsEl('fw-export-links').replaceChildren();fcsEl('fw-export-status').textContent='Creating WSP. Combined analyses recheck all events in every original FCS; this may take several minutes…';fcsEl('fw-export-dialog').showModal();
 try{
  const result=await api('/fcs/export','POST',{id:run});
  await fcsRefresh();
  fcsEl('fw-export-status').textContent=result.report.selected_sample+' · '+result.report.gates_verified+' gates verified. Export saved to the original-file library.';
  fcsEl('fw-export-links').innerHTML='<p><a class="button" href="/api/fcs/source/'+esc(result.file.id)+'">Download FlowJo WSP</a></p>'+ (result.sources?.length?result.sources:[result.fcs]).map(f=>'<p><a href="/api/fcs/source/'+esc(f.id)+'">'+esc(f.filename)+'</a></p>').join('');
 }catch(e){fcsEl('fw-export-status').textContent=e.message}
 finally{fcsExportBusy=false;fwUpdate()}
};
function fwRenderReferences(){
 const available=fwReferenceRows.filter(r=>r.status==='Available'&&!r.imported);
 const bulk=fcsEl('fw-reference-all');bulk.disabled=fwReferenceBusy||!available.length;
 bulk.textContent='Link all available ('+available.length+')';
 fcsEl('fw-reference-stop').disabled=!fwReferenceBusy||fwReferenceStop;

 fcsEl('fw-reference-files').innerHTML=table(['Sample','Original WSP path','Mac path / status','Library',''],fwReferenceRows.map((r,i)=>({r,i})).filter(({r})=>r.name.toLowerCase().includes(fcsEl('fw-reference-search').value.toLowerCase())).map(({r,i})=>[
  esc(r.name)+'<br><small>'+r.events.toLocaleString()+' events</small>',
  '<span class="fcs-hash">'+esc(r.original_uri||'No path recorded')+'</span>',
  '<span class="fcs-hash">'+esc(r.server_path||'No configured mapping')+'</span><br>'+esc(r.status),
  r.imported?'Linked · SMB original':r.importError?esc(r.importError):r.uploaded_name_matches.length+' name match(es)',
  '<button data-reference-import="'+i+'" '+(r.status!=='Available'||fwReferenceBusy||r.imported?'disabled':'')+'>Link SMB original</button>'
 ]));
}
fcsEl('fw-reference-workspace').onchange=()=>{++fwReferenceRequest;fwReferenceRows=[];fwReferenceWorkspace='';fwRenderReferences();fcsEl('fw-reference-status').textContent=''};
fcsEl('fw-reference-load').onclick=async()=>{
 const id=fcsEl('fw-reference-workspace').value;if(!id||fwReferenceBusy)return;
 const request=++fwReferenceRequest;fcsEl('fw-reference-status').textContent='Checking workspace references on the mounted share…';fcsEl('fw-reference-load').disabled=true;
 try{
  const result=await api('/fcs/workspace-files/'+id);
  if(request!==fwReferenceRequest)return;
  fwReferenceRows=result.samples;fwReferenceWorkspace=id;fwRenderReferences();
  fcsEl('fw-reference-status').textContent=result.samples.length+' references · '+result.samples.filter(r=>r.status==='Available').length+' available on SMB.';
 }catch(e){if(request===fwReferenceRequest)fcsEl('fw-reference-status').textContent=e.message}
 finally{fcsEl('fw-reference-load').disabled=false}
};
async function fwImportReferences(rows){
 if(fwReferenceBusy||!rows.length)return;
 const workspace=fwReferenceWorkspace;
 fwReferenceBusy=true;fwReferenceStop=false;
 fcsEl('fw-reference-load').disabled=true;fcsEl('fw-reference-workspace').disabled=true;
 const progress=fcsEl('fw-reference-progress');progress.max=rows.length;progress.value=0;
 let completed=0,failed=0,lastFile=null;const errors=[];
 fwRenderReferences();
 try{
  for(const row of rows){
   if(fwReferenceStop)break;
   fcsEl('fw-reference-status').textContent=`${completed+failed} / ${rows.length} processed · Reading ${row.name}… Keep this tab open.`;
   try{
    const file=await api('/fcs/link-reference','POST',{wsp_id:workspace,sample_id:row.sample_id});
    row.imported=true;row.importError='';row.uploaded_name_matches.push(file.id);lastFile=file;completed++;
   }catch(e){
    failed++;row.importError=e.message;errors.push(row.name+': '+e.message);
    // Stop on authorization, capacity or SMB timeout errors; preserve completed files.
    if([401,403,507,504].includes(e.status))fwReferenceStop=true;
   }
   progress.value=completed+failed;fwRenderReferences();
  }
  fcsEl('fw-reference-status').textContent=`${fwReferenceStop?'Stopped':'Finished'} · ${completed} linked · ${failed} failed · ${rows.length-completed-failed} remaining. `+(errors.length?errors.join(' | '):'Select New analysis to apply the WSP gates.');
  try{await fcsRefresh()}catch(e){fcsEl('fw-reference-status').textContent+=' Library refresh failed: '+e.message}
  if(lastFile){fcsEl('fcs-sample').value=lastFile.id;fcsEl('fcs-workspace').value=workspace}
 }finally{
  fwReferenceBusy=false;fwReferenceStop=false;fwRenderReferences();
  fcsEl('fw-reference-load').disabled=false;fcsEl('fw-reference-workspace').disabled=false;
 }
}
fcsEl('fw-reference-files').onclick=e=>{
 const button=e.target.closest('[data-reference-import]');if(!button)return;
 const row=fwReferenceRows[Number(button.dataset.referenceImport)];
 if(row&&row.status==='Available'&&!row.imported)fwImportReferences([row]);
};
fcsEl('fw-reference-all').onclick=()=>fwImportReferences(fwReferenceRows.filter(r=>r.status==='Available'&&!r.imported));
fcsEl('fw-reference-stop').onclick=()=>{fwReferenceStop=true;fwRenderReferences();fcsEl('fw-reference-status').textContent='Stopping after the current file is linked…'};
window.addEventListener('beforeunload',e=>{if(fwReferenceBusy){e.preventDefault();e.returnValue=''}});

fcsEl('fw-reference-search').oninput=fwRenderReferences;

// One live editor canvas; inactive cards retain their own plot data and rendered image.
let fwPlotSlots=[],fwActivePlot=0;
function fwSavePlot(){
 if(!fcsPlot)return;
 const canvas=fcsEl('fcs-canvas');
 const slot=fwPlotSlots[fwActivePlot]||{};
 Object.assign(slot,{run:fcsRun,plot:fcsPlot,gate:fcsGate,x:fcsEl('fcs-x').value,y:fcsEl('fcs-y').value,mode:fcsEl('fcs-mode').value});
 if(!slot.image){slot.image=document.createElement('canvas');slot.image.width=canvas.width;slot.image.height=canvas.height}
 slot.image.getContext('2d').drawImage(canvas,0,0);fwPlotSlots[fwActivePlot]=slot;
 // Initialize additional views from the first plot. Subsequent changes are independent.
 const count=Number(fcsEl('fw-plot-count').value);
 for(let i=0;i<count;i++)if(!fwPlotSlots[i]){
  const image=document.createElement('canvas');image.width=canvas.width;image.height=canvas.height;image.getContext('2d').drawImage(canvas,0,0);
  fwPlotSlots[i]={...slot,image};
 }
 fwPlotLayout();
}
function fwPlotLayout(){
 const row=fcsEl('fw-plot-row'),canvas=fcsEl('fcs-canvas'),count=Number(fcsEl('fw-plot-count').value);
 row.style.setProperty('--plot-count',Math.min(count,4));
 // Keep the live canvas attached while drawing to preserve pointer capture.
 if(row.children.length!==count||!row.querySelector('[data-plot-card]')){
  const fragment=document.createDocumentFragment();
  for(let i=0;i<count;i++){
   const card=document.createElement('section');card.dataset.plotCard=i;
   const button=document.createElement('button');button.type='button';button.onclick=()=>fwSelectPlot(i);card.append(button);
   const select=document.createElement('select');select.setAttribute('aria-label','Plot '+(i+1)+' analysis');
   select.onchange=async()=>{if(fcsDraft){fwPlotLayout();fcsStatus('Save or cancel the gate edit first.');return}const runId=select.value;if(!runId){fwPlotLayout();return}fwSelectPlot(i);fcsEl('fcs-runs').value=runId;try{await fcsLoadRun()}catch(e){fcsStatus(e.message)}};
   card.append(select);
   const body=document.createElement('div');body.className='fw-plot-body';card.append(body);fragment.append(card);
  }
  row.replaceChildren(fragment);
 }
 for(let i=0;i<count;i++){
  const card=row.children[i],slot=fwPlotSlots[i],active=i===fwActivePlot;
  card.classList.toggle('active',active);const button=card.firstChild;
  button.textContent=`Plot ${i+1} · ${slot?.plot.gate?.name||'All events'}`;button.setAttribute('aria-pressed',String(active));
  const select=card.children[1];
  const choices=fcsCatalog.runs.filter(r=>r.status==='done').map(r=>({value:r.id,label:fcsRunLabel(r)+' · '+new Date(r.created_at).toLocaleString('en-GB')}));
  options(select,choices,'Choose completed analysis',slot?.run?.id||'');select.disabled=!!fcsDraft;
  const body=card.lastChild,node=active?canvas:slot?.image;
  if(node&&body.firstChild!==node)body.replaceChildren(node);
  body.onclick=()=>{if(fcsDraft)return;fwSelectPlot(i);fwZoomPlot(true)};
 }
 fcsEl('fw-active-plot').textContent='Selected: Plot '+(fwActivePlot+1);
}
function fwSelectPlot(index){
 if(index===fwActivePlot)return;
 if(fcsDraft){fcsStatus('Save or cancel the gate edit before selecting another plot.');return}
 ++fcsPlotRequest;++fcsRunRequest;fwActivePlot=index;
 const slot=fwPlotSlots[index];
 if(!slot){fwPlotLayout();return}
 fcsRun=slot.run;fcsGate=slot.gate;fcsPlot=slot.plot;fcsEl('fcs-runs').value=fcsRun.id;fwCollapsed.clear();fwShowRun(fcsRun);
 fcsEl('fcs-x').value=slot.x;fcsEl('fcs-y').value=slot.y;fcsEl('fcs-mode').value=slot.mode;
 fwPlotLayout();fcsDraw();fwRenderTree();fwUpdate();
}
fcsEl('fw-plot-count').onchange=()=>{
 if(fcsDraft){fcsEl('fw-plot-count').value=fcsEl('fw-plot-row').children.length;fcsStatus('Save or cancel the gate edit before changing the layout.');return}
 if(fwActivePlot>=Number(fcsEl('fw-plot-count').value))fwSelectPlot(0);
 if(fcsPlot)fwSavePlot();else fwPlotLayout();
};
fwPlotLayout();

fcsEl('fw-edit-exit').onclick=()=>{fcsCancelEdit();fcsStatus('Gate edit cancelled.');fcsDrawRequest().catch(e=>fcsStatus(e.message))};

function fwZoomPlot(open){
 fcsEl('fcs-results').classList.toggle('fw-zoom',open);
 fcsEl('fw-zoom-close').hidden=!open;
}
fcsEl('fw-zoom-close').onclick=()=>fwZoomPlot(false);
document.addEventListener('keydown',e=>{if(e.key==='Escape')fwZoomPlot(false)});

let fcsDeleteContext=null;
fcsEl('fcs-delete-gate').onclick=()=>{
 if(fcsDraft||!fcsRun?.result||fcsGate<0)return;
 const gates=fcsRun.result.gates,removed=new Set([fcsGate]);let size;
 do{size=removed.size;gates.forEach((g,i)=>{if(removed.has(g.parent_index))removed.add(i)})}while(size!==removed.size);
 fcsDeleteContext={run:fcsRun.id,target:fcsGate};
 fcsEl('fcs-delete-description').textContent=`Remove “${gates[fcsGate].name}” and ${removed.size-1} descendant gates from a new analysis version?`;
 fcsEl('fcs-delete-reason').value='';fcsEl('fcs-delete-error').textContent='';fcsEl('fcs-delete-dialog').showModal();
};
fcsEl('fcs-delete-cancel').onclick=()=>fcsEl('fcs-delete-dialog').close();
fcsEl('fcs-delete-confirm').onclick=async()=>{
 const button=fcsEl('fcs-delete-confirm'),context=fcsDeleteContext,reason=fcsEl('fcs-delete-reason').value.trim();
 if(!context||!reason){fcsEl('fcs-delete-error').textContent='Enter a reason.';return}
 button.disabled=true;
 try{const r=await api('/fcs/edit','POST',{base_run:context.run,reason,change:{operation:'delete',target:context.target}});fcsEl('fcs-delete-dialog').close();await fcsRefresh();fcsEl('fcs-runs').value=r.id;await fcsLoadRun()}
 catch(e){fcsEl('fcs-delete-error').textContent=e.message}finally{button.disabled=false}
};

function fcsEventLabel(index){const source=(fcsPlot.sources||[]).find(s=>index>=s.start&&index<s.stop);return source?`${source.filename} · Original event #${index-source.start+1}`:`Original event #${index+1}`}
fcsEl('fcs-combine-open').onclick=async()=>{
 if(fcsDraft){fcsStatus('Save or cancel the gate edit first.');return}
 try{await fcsRefresh();const runs=fcsCatalog.runs.filter(r=>r.status==='done'&&!JSON.parse(r.edit_spec||'{}').combine_runs);
 options(fcsEl('fcs-combine-template'),runs.map(r=>({value:r.id,label:fcsRunLabel(r)+' · '+new Date(r.created_at).toLocaleString('en-GB')})),'Select template');
 fcsEl('fcs-combine-list').innerHTML=runs.map(r=>`<label class="inline"><input type="checkbox" value="${esc(r.id)}">${esc(fcsRunLabel(r))} · ${esc(new Date(r.created_at).toLocaleString('en-GB'))}</label>`).join('');
 fcsEl('fcs-combine-error').textContent='';fcsEl('fcs-combine-dialog').showModal();}catch(e){fcsStatus(e.message)}
};
fcsEl('fcs-combine-cancel').onclick=()=>fcsEl('fcs-combine-dialog').close();
fcsEl('fcs-combine-submit').onclick=async()=>{
 const template=fcsEl('fcs-combine-template').value,ids=[template,...[...fcsEl('fcs-combine-list').querySelectorAll('input:checked')].map(x=>x.value).filter(x=>x!==template)],button=fcsEl('fcs-combine-submit');
 if(!template||ids.length<2||ids.length>8){fcsEl('fcs-combine-error').textContent='Choose a template and 1–7 additional analyses.';return}
 button.disabled=true;try{const r=await api('/fcs/combine','POST',{name:fcsEl('fcs-combine-name').value,run_ids:ids});fcsEl('fcs-combine-dialog').close();await fcsRefresh();fcsEl('fcs-runs').value=r.id;await fcsLoadRun()}catch(e){fcsEl('fcs-combine-error').textContent=e.message}finally{button.disabled=false}
};
