const assert=require('node:assert/strict'),test=require('node:test'),F=require('../../../static/chart.js');
const d={mice:[{mouse_id:'1',group_name:'A',excluded:0},{mouse_id:'2',group_name:'A',excluded:0}],metrics:[{id:1,name:'Body weight',unit:'g'}],measurements:[{mouse_id:'1',metric_id:1,timepoint:'0',replicate:'1',value:10},{mouse_id:'2',metric_id:1,timepoint:'0',replicate:'1',value:20},{mouse_id:'1',metric_id:1,timepoint:'15',replicate:'1',value:30}]};
const c={metric:1,timepoint:'0',replicate:'1',type:'bar',error:'SD',grouping:'group_name',ymin:'',ymax:'',styles:{}};
test('SD and SEM use independent mouse count and sample SD',()=>{const s=F.stats([10,20]);assert.equal(s.mean,15);assert.equal(s.sd,Math.sqrt(50));assert.equal(s.sem,5);assert.equal(F.stats([10]).sd,null);assert.equal(F.stats([]).mean,null)});
test('all values and grouping respond to global mouse exclusion',()=>{const x=structuredClone(d);x.mice[0].excluded=1;assert.equal(F.dataset(x,c).summaries[0].n,1);assert.equal(F.dataset(x,c).summaries[0].mean,20);const curves=F.dataset(x,{...c,type:'line'});assert.equal(curves.summaries[1].n,0)});
test('technical replicate mixing is rejected',()=>{const x=structuredClone(d);x.measurements.push({...x.measurements[0],replicate:'2'});assert.throws(()=>F.dataset(x,{...c,replicate:''}),/replicate/)});
test('rendered SVG includes axes, symbols, mean and selected error label',()=>{const r=F.render(d,c);assert.match(r.svg,/data-mouse="1"/);assert.match(r.svg,/Mean ± SD/);assert.match(F.render(d,{...c,error:'SEM'}).svg,/Mean ± SEM/);assert.match(r.svg,/<g data-mouse[^>]+><title>/)});
test('invalid ranges are blocked and legacy manual labels are ignored',()=>{assert.throws(()=>F.render(d,{...c,ymax:15}),/range|between/);assert.doesNotMatch(F.render(d,{...c,annotations:'A | A | p=0.01',annotationMethod:'legacy'}).svg,/p=0.01/)});
test('OGTT curves use numeric timepoints and preserve missing n',()=>{const ogtt={...d,metrics:[{...d.metrics[0],name:'OGTT'}]};const r=F.render(ogtt,{...c,type:'line'});assert.equal(r.summary[1].n,1);assert.match(r.svg,/Time \(min\)/);assert.throws(()=>F.render({...ogtt,measurements:[{...d.measurements[0],timepoint:'endpoint'}]},{...c,type:'line'}),/numeric/)});
test('sample selector keeps excluded, missing and zero values and respects filters',()=>{const x=structuredClone(d);x.mice[0].excluded=1;x.mice[0].experiment='E1';x.mice[0].weeks='36';x.mice.push({mouse_id:'3',group_name:'A',excluded:0});x.measurements[0].value=0;x.measurements[1].value=null;const rows=F.sampleRows(x,c);assert.equal(rows.length,3);assert.equal(rows[0].rows[0].value,0);assert.equal(rows[0].mouse.excluded,1);assert.equal(rows[1].rows[0].value,null);assert.equal(rows[2].rows.length,0);assert.equal(F.sampleRows(x,{...c,experiment:'E1',weeks:'36'}).length,1);assert.equal(F.sampleRows(x,{...c,type:'line'})[0].rows.length,2);assert.equal(F.sampleRows(x,{...c,replicate:'2'})[0].rows.length,0)});
test('hierarchy joins visible graphs by ID and separates Exp/Diet with numeric mouse ordering',()=>{
 const data={mice:[{mouse_id:'10',experiment:'Exp2',diet:'Chow',excluded:0},{mouse_id:'2',experiment:'Exp2',diet:'Chow',excluded:1},{mouse_id:'3',experiment:'Exp10',diet:'Chow',excluded:0},{mouse_id:'4',experiment:'Exp2',diet:'Western',excluded:0}],measurements:[{mouse_id:'10',metric_id:1,timepoint:'0',replicate:'1',value:0},{mouse_id:'2',metric_id:2,timepoint:'0',replicate:'1',value:null},{mouse_id:'3',metric_id:1,timepoint:'0',replicate:'1',value:5}]};
 const tree=F.sampleTree(data,[c,{...c,metric:2}]);assert.deepEqual(tree.map(e=>e.experiment),['Exp2','Exp10']);assert.deepEqual(tree[0].diets[0].samples.map(s=>s.mouse.mouse_id),['2','10']);assert.equal(tree[0].diets[0].samples[0].mouse.excluded,1);assert.equal(tree[0].diets[0].samples[1].panels.length,2);
 assert.equal(F.sampleTree(data,[c],{query:'Exp10'})[0].diets[0].samples[0].mouse.mouse_id,'3');
 assert.equal(F.sampleTree(data,[c],{showMissing:true})[0].diets.length,2);
 assert.equal(F.sampleTree(data,[{...c,experiment:'Exp2'}]).length,1);
});
test('one shared exclusion updates all eight graphs and combined SVG contains every panel',()=>{
 const data=structuredClone(d);data.metrics=Array.from({length:8},(_,i)=>({id:i+1,name:'Metric '+(i+1),unit:'u'}));data.measurements=data.metrics.flatMap(m=>d.measurements.map(r=>({...r,metric_id:m.id})));const configs=data.metrics.map(m=>({...c,metric:m.id}));
 const before=configs.map(cfg=>F.render(data,cfg));assert.ok(before.every(f=>f.summary[0].n===2));data.mice[0].excluded=1;const after=configs.map(cfg=>F.render(data,cfg));assert.ok(after.every(f=>f.summary[0].n===1&&f.summary[0].mean===20));assert.ok(after.every(f=>!f.svg.includes('data-mouse="1"')));
 const svg=F.composeFigures(after);assert.match(svg,/width="1600" height="2560"/);assert.equal((svg.match(/<svg\b/g)||[]).length,9);assert.match(svg,/>H<\/text>/);assert.throws(()=>F.composeFigures([...after,after[0]]),/Check/);assert.throws(()=>F.composeFigures([{svg:''}]),/at least one graph/);
});
test('reference group colors are stable across age, order and missing groups',()=>{assert.equal(F.defaultGroupStyle('36w Chow',9).color,'#000000');assert.equal(F.defaultGroupStyle('10w Western',0).color,'#fc225c');assert.equal(F.defaultGroupStyle('TRF 6:18',5).color,'#197274');assert.equal(F.defaultGroupStyle('TRF 10:14',1).color,'#64c3fa');assert.equal(F.defaultGroupStyle('ADF').color,'#3b0070');assert.equal(F.defaultGroupStyle('RC').color,F.defaultGroupStyle('Reverse').color)});
test('p-values use numeric formatting and explicit zero precision',()=>{assert.equal(F.formatP(.0019),'p = 0.0019');assert.equal(F.formatP(0),'p ≈ 0');assert.match(F.formatP(1e-8),/1\.00e-8/);assert.throws(()=>F.formatP(1.1),/range|between/)});
test('display thresholds use strict adjusted p bounds without changing the comparison family',()=>{
 const analysis={status:'ok',method:'One-way ANOVA + Tukey HSD',groups:['A','B','C','D'].map(group=>({group,n:2})),anova:{p:.012},pairs:[{a:'A',b:'B',p_adjusted:.0499},{a:'A',b:'C',p_adjusted:.05},{a:'A',b:'D',p_adjusted:.0999},{a:'B',b:'C',p_adjusted:.1},{a:'B',b:'D',p_adjusted:.8},{a:'C',b:'D',p_adjusted:0}]};
 const original=JSON.stringify(analysis),groups=['A','B','C','D'];
 assert.equal(F.comparisonLabels(analysis,{comparisonMode:'all'},groups).length,6);
 assert.deepEqual(F.comparisonLabels(analysis,{comparisonMode:'p10'},groups).map(p=>p.slice(0,2)),[['A','B'],['A','C'],['A','D'],['C','D']]);
 assert.deepEqual(F.comparisonLabels(analysis,{comparisonMode:'p05'},groups).map(p=>p.slice(0,2)),[['A','B'],['C','D']]);
 assert.equal(JSON.stringify(analysis),original);
 const x=structuredClone(d);x.mice.push(...['B','C','D'].map((group,i)=>({mouse_id:String(i+3),group_name:group,excluded:0})));x.measurements.push(...['3','4','5'].map((mouse_id,i)=>({...d.measurements[0],mouse_id,value:30+i*10})));
 const r=F.render(x,{...c,comparisonMode:'p05',analysis});assert.match(r.svg,/p = 0.0499/);assert.doesNotMatch(r.svg,/>p = 0.05</);assert.match(r.svg,/ANOVA p = 0.012/);assert.equal(r.analysis,analysis);
});
test('zero floor crops only error display and retains SD, zero observations and negative-value guards',()=>{const x=structuredClone(d);x.measurements[0].value=0;x.measurements[1].value=10;const r=F.render(x,c);assert.equal(r.axis.negativeMeasurements,0);assert.equal(r.axis.errorBelowZero,true);assert.equal(r.axis.min,0);assert.equal(r.axis.clippedLowerErrorBars,1);assert.equal(r.summary[0].mean,5);assert.equal(r.summary[0].sd,Math.sqrt(50));assert.match(r.svg,/clip-path="url\(#plot-clip-/);assert.match(r.svg,/error bars below 0 not shown/);assert.match(r.svg,/data-mouse="1"/);x.measurements[0].value=-1;assert.throws(()=>F.render(x,c),/range|between/);assert.equal(F.render(x,{...c,ymin:-10}).axis.negativeMeasurements,1)});
test('default p display is below 0.05 and explicit all-pairs remains selectable',()=>{const a={status:'ok',groups:['A','B','C'].map(group=>({group})),pairs:[{a:'A',b:'B',p_adjusted:.0499},{a:'A',b:'C',p_adjusted:.05},{a:'B',b:'C',p_adjusted:.09}]};assert.equal(F.comparisonLabels(a,{},['A','B','C']).length,1);assert.equal(F.comparisonLabels(a,{comparisonMode:'all'},['A','B','C']).length,3)});
test('MFI graph title preserves the original header and wraps long paths without losing content',()=>{const x=structuredClone(d);const title='Cells/Single Cells/Single Cells/Live cells/CD3+/CD4+/Foxp3- Teffs/GATA-3+ Teffs | Geometric Mean (GATA3)';x.metrics[0]={...x.metrics[0],name:'Geometric Mean (GATA3)',source_header:title,gate:'Cells/Live cells/GATA-3+ Teffs',unit:'a.u.'};const r=F.render(x,c);assert.equal(r.title,title);assert.ok((r.svg.match(/<tspan /g)||[]).length>1);assert.match(r.svg,/<title>Cells\/Single Cells\/Single Cells\/Live cells\/CD3\+\/CD4\+\/Foxp3- Teffs\/GATA-3\+ Teffs \| Geometric Mean \(GATA3\)<\/title>/);assert.equal(F.metricTitle({...x.metrics[0],source_header:undefined}),'Cells/Live cells/GATA-3+ Teffs | Geometric Mean (GATA3)')});
test('sample counts separate true missing values, unmeasured mice, exclusions and numeric zero',()=>{const x=structuredClone(d);x.mice=Array.from({length:5},(_,i)=>({mouse_id:String(i+1),group_name:'A',excluded:i===3?1:0}));x.measurements=[{...d.measurements[0],mouse_id:'1',value:0},{...d.measurements[0],mouse_id:'2',value:null},{...d.measurements[0],mouse_id:'4',value:8},{...d.measurements[0],mouse_id:'5',value:20}];const r=F.render(x,c);assert.deepEqual(r.coverage,{measured:['1','5'],missing:['2'],unmeasured:['3'],excluded:['4']});assert.equal(r.summary[0].n,2);assert.equal(r.summary[0].missing_values,1);assert.equal(r.summary[0].unmeasured,1);assert.equal(r.summary[0].excluded,1)});

test('empty groups disappear from graph while excluded and missing coverage remains available',()=>{const x=structuredClone(d);x.mice.push({mouse_id:'3',group_name:'Empty',excluded:1},{mouse_id:'4',group_name:'Missing',excluded:0});x.measurements.push({...d.measurements[0],mouse_id:'3',value:5},{...d.measurements[0],mouse_id:'4',value:null});const r=F.render(x,c);assert.doesNotMatch(r.svg,/>Empty<|>Missing</);assert.deepEqual(r.coverage.excluded,['3']);assert.deepEqual(r.coverage.missing,['4']);assert.match(F.render(x,{...c,showExcluded:true}).svg,/>Empty</);x.mice.forEach(m=>m.excluded=1);const empty=F.render(x,c);assert.equal(empty.svg,'');assert.equal(empty.coverage.excluded.length,4)});
test('hide p-value removes ANOVA and pair labels while preserving analysis for CSV',()=>{const a={status:'ok',method:'One-way ANOVA + Tukey',anova:{p:.001},groups:[{group:'A'}],pairs:[]};const r=F.render(d,{...c,comparisonMode:'none',analysis:a});assert.doesNotMatch(r.svg,/ANOVA|adjusted p|p =/);assert.equal(r.analysis,a)});
test('DI control scope adds only selected diet/age groups and keeps basic view separate',()=>{
 const S=require('../../../static/study.js');const x={experiment_types:{Exp1:'basic',Exp9:'di'},mice:[{mouse_id:'1',experiment:'Exp1',weeks:'36',diet:'Chow'},{mouse_id:'2',experiment:'Exp1',weeks:'36',diet:'Western'},{mouse_id:'3',experiment:'Exp1',weeks:'20',diet:'Chow'},{mouse_id:'4',experiment:'Exp9',diet:'ADF'},{mouse_id:'5',experiment:'Exp9',diet:'Chow'},{mouse_id:'6',experiment:'Unknown',diet:'Chow'}]};
 const key=S.candidates(x).find(g=>g.weeks==='36'&&g.diet==='Chow').key;
 assert.deepEqual(S.selection(x,'di'),['4','5']);assert.deepEqual(S.selection(x,'di',[key,key]),['1','4','5']);assert.deepEqual(S.selection(x,'basic',[key]),['1','2','3']);
 const cfg={...c,scope_mouse_ids:['2']};assert.deepEqual(F.sampleRows(d,cfg).map(s=>s.mouse.mouse_id),['2']);assert.equal(F.dataset(d,cfg).summaries[0].mean,20);assert.equal(F.sampleRows(d,{...c,scope_mouse_ids:[]}).length,0);
});

test('sparse exports compact the canvas and preserve board letters and errors',()=>{
 const empty={svg:''},figure=F.render(d,c);
 const svg=F.composeFigures([empty,empty,figure,empty]);
 assert.match(svg,/width="800" height="640"/);assert.match(svg,/>C<\/text>/);
 assert.throws(()=>F.composeFigures([figure,{error:true,message:'Invalid axis'}]),/Graph 2: Invalid axis/);
});
test('weekly trends distinguish means and medians and ignore endpoints and excluded mice',()=>{
 const x=structuredClone(d);x.mice.push({mouse_id:'3',group_name:'A',excluded:0});
 x.measurements[0].timepoint=x.measurements[1].timepoint='Week 2';
 x.measurements[2].timepoint='10w';
 x.measurements.push({...x.measurements[0],mouse_id:'3',value:90},{...x.measurements[0],timepoint:'endpoint',value:999});
 const render=trend=>F.render(x,{...c,type:'line',trend});
 assert.deepEqual(render('median').set.times,['2','10']);
 assert.equal(render('median').summary[0].median,20);assert.equal(render('mean').summary[0].mean,40);
 assert.notEqual(render('median').svg.match(/<path d="M130 [^"]+ L[^"]+/)[0],render('mean').svg.match(/<path d="M130 [^"]+ L[^"]+/)[0]);
 assert.doesNotMatch(render('off').svg,/<path d="M130 [^"]+ L/);
 x.mice[2].excluded=1;assert.equal(render('median').summary[0].median,15);
 assert.deepEqual(F.metricChoices(x,x.metrics).map(c=>c.view),['weekly','endpoint']);
});
test('hierarchy uses actual observations, panel provenance and qPCR pathway',()=>{
 const metrics=[{name:'HE',organ:'Liver'},{name:'PSR',organ:'Liver'},{name:'CD3',organ:'Gut',gate:'Live/CD3+'},{name:'Col1a1',organ:'Liver',identity:'{"pathway":"Fibrosis"}'},{name:'ITT'}].map((m,i)=>({...m,id:i+1}));
 const data={metrics,measurements:metrics.map(m=>({metric_id:m.id,upload_id:'u',value:m.id===2?null:0})),uploads:[{id:'u',filename:'T cell panel.xls'}]};
 assert.deepEqual(F.metricChoices(data,metrics).map(c=>c.path),[['Histology','Liver'],['Flow cytometry','Gut','T Cell Panel','CD3+'],['qPCR','Liver','Fibrosis'],['Metabolic outcome','ITT']]);
});

test('FACS picker skips ancestor folders while preserving populations and statistics',()=>{
 const gates=['Cells/SingleCell/SingleCell/CD3+','Cells/SingleCell/SingleCell/CD3+','Cells/Live/Tregs/CD25+','Cells/Live/Teffs/CD25+'];
 const metrics=gates.map((gate,i)=>({id:i+1,gate,organ:'Liver',name:i===1?'Frequency':'Count',identity:'{"panel":"T Cell Panel"}'}));
 const measurements=metrics.map(m=>({metric_id:m.id,value:2}));
 const choices=F.metricChoices({measurements},metrics);
 assert.deepEqual(choices.map(c=>c.path.at(-1)),['CD3+','CD3+','CD25+ (Cells / Live / Tregs)','CD25+ (Cells / Live / Teffs)']);
 assert.ok(choices.every(c=>c.path.length===4));
 assert.deepEqual(choices.map(c=>c.metric.gate),gates);
});

test('Histology offers measured stains directly under each organ',()=>{
 const metrics=['HE','PSR','HE','PSR'].map((name,i)=>({id:i+1,name,unit:'%',organ:i<2?'Liver':'Gut'}));
 const measurements=metrics.map(m=>({metric_id:m.id,value:m.id===4?null:0}));
 const choices=F.metricChoices({measurements},metrics);
 assert.deepEqual(choices.map(({path,metric})=>[...path,metric.name,metric.unit,metric.id]),[
  ['Histology','Liver','HE','%',1],['Histology','Liver','PSR','%',2],['Histology','Gut','HE','%',3]
 ]);
});


test('median identifies central mice, midpoint, ties, missing and exclusions',()=>{
 const sample=values=>({mice:values.map((v,i)=>({mouse_id:String(i+1),group_name:'A',excluded:0})),metrics:d.metrics,measurements:values.map((v,i)=>({mouse_id:String(i+1),metric_id:1,timepoint:'0',replicate:'1',value:v}))});
 let x=sample([10,30,20]);let summary=F.dataset(x,c).summaries[0];
 assert.equal(summary.median,20);assert.deepEqual(summary.median_mouse_ids,['3']);assert.equal(summary.median_is_midpoint,false);
 x=sample([10,40,20,30]);summary=F.dataset(x,c).summaries[0];
 assert.equal(summary.median,25);assert.deepEqual(summary.median_mouse_ids,['3','4']);assert.equal(summary.median_is_midpoint,true);
 x=sample([10,20,20,20,30]);summary=F.dataset(x,c).summaries[0];
 assert.deepEqual(summary.median_mouse_ids,['2','3','4']);assert.equal(summary.median_tied,true);
 x=sample([0,null,20,10]);x.mice[2].excluded=1;summary=F.dataset(x,c).summaries[0];
 assert.equal(summary.median,5);assert.deepEqual(summary.median_mouse_ids,['1','4']);
 x.mice[0].excluded=1;x.mice[3].excluded=1;summary=F.dataset(x,c).summaries[0];
 assert.equal(summary.median,null);assert.deepEqual(summary.median_mouse_ids,[]);
});

test('dated body weight appears in timeline and keeps real dates for mean/median/off',()=>{
 const x=structuredClone(d);x.mice.push({mouse_id:'3',group_name:'A',excluded:0});
 x.measurements=[...['2025-01-01','2025-01-15'].flatMap((timepoint,j)=>[10,20,60].map((value,i)=>({mouse_id:String(i+1),metric_id:1,timepoint,replicate:'1',value:value+j}))),{mouse_id:'1',metric_id:1,timepoint:'endpoint',replicate:'1',value:30}];
 const choices=F.metricChoices(x,x.metrics);assert(choices.some(v=>v.view==='dated'));assert(choices.some(v=>v.view==='endpoint'));
 const cfg={...c,type:'line',weightAxis:'date',comparisonMode:'none'};
 const mean=F.render(x,{...cfg,trend:'mean'}),median=F.render(x,{...cfg,trend:'median'}),off=F.render(x,{...cfg,trend:'off'});
 assert.deepEqual(mean.set.times,['2025-01-01','2025-01-15']);assert.equal(mean.set.records.length,6);assert.equal(mean.set.summaries[0].mean,30);assert.equal(mean.set.summaries[0].median,20);
 assert.notEqual(mean.svg,median.svg);assert.match(off.svg,/Date trend: off/);assert.match(mean.svg,/>Date</);assert.equal(F.dateNumber('2025-02-30'),null);
});
test('weight timelines require one experiment and allow individual points on demand',()=>{
 const x=structuredClone(d);x.mice[0].experiment='Exp2';x.mice[1].experiment='Exp3';
 assert.throws(()=>F.render(x,{...c,type:'line',trend:'mean'}),/Select one experiment/);
 const cfg={...c,type:'line',trend:'mean',experiment:'Exp2'};
 assert.doesNotMatch(F.render(x,cfg).svg,/data-mouse=/);
 assert.match(F.render(x,{...cfg,showIndividuals:true}).svg,/data-mouse="1"/);
 assert.match(F.render(x,cfg).svg,/Exp2/);
});
test('timeline gives every measured date a tick and keeps points aligned with dates',()=>{
 const x=structuredClone(d);x.measurements=x.measurements.map((r,i)=>({...r,timepoint:i<2?'2025-01-01':'2025-01-08'}));
 const r=F.render(x,{...c,type:'line',weightAxis:'date',trend:'mean',showIndividuals:true,styles:{A:{shape:'circle',color:'#000000'}}});
 assert.equal((r.svg.match(/data-axis-timepoint=/g)||[]).length,2);
 const axis=Number(r.svg.match(/data-axis-timepoint="2025-01-01" d="M([\d.]+)/)[1]);
 const point=r.svg.match(/<g data-mouse="1"[^>]*><title>[^<]*2025-01-01[^<]*<\/title><circle cx="([\d.]+)"/);
 assert(point);assert.equal(Number(point[1]),axis);assert.match(r.svg,/data-timepoint="2025-01-01"/);
});
