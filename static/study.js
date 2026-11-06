(function(root){
'use strict';
function candidates(data){const groups=new Map();for(const m of data.mice){if(data.experiment_types?.[m.experiment]!=='basic')continue;const diet=String(m.diet||m.group_name||'').trim();if(!/^(chow|western)( diet)?$/i.test(diet))continue;const key=JSON.stringify([m.experiment,String(m.weeks||''),diet]);if(!groups.has(key))groups.set(key,{key,experiment:m.experiment,weeks:String(m.weeks||''),diet,ids:[]});groups.get(key).ids.push(m.mouse_id);}return [...groups.values()].sort((a,b)=>a.experiment.localeCompare(b.experiment,undefined,{numeric:true})||a.weeks.localeCompare(b.weeks,undefined,{numeric:true})||a.diet.localeCompare(b.diet));}
function selection(data,study,keys=[]){const chosen=new Set(keys),extra=new Set(study==='di'?candidates(data).filter(g=>chosen.has(g.key)).flatMap(g=>g.ids):[]);return data.mice.filter(m=>data.experiment_types?.[m.experiment]===study||extra.has(m.mouse_id)).map(m=>m.mouse_id);}
const api={candidates,selection};if(typeof module!=='undefined')module.exports=api;else root.StudyScope=api;
})(globalThis);
