// Prototype + test for betweenness (Brandes) and Louvain community detection.

// ---- Betweenness centrality (Brandes, unweighted, undirected) ----
function betweenness(nodeIds, adjMap){
  const bc = {}; nodeIds.forEach(v=>bc[v]=0);
  for(const s of nodeIds){
    const S=[], P={}, sigma={}, dist={};
    nodeIds.forEach(v=>{P[v]=[];sigma[v]=0;dist[v]=-1;});
    sigma[s]=1; dist[s]=0;
    const Q=[s];
    while(Q.length){
      const v=Q.shift(); S.push(v);
      for(const w of (adjMap.get(v)||[])){
        if(dist[w]<0){ dist[w]=dist[v]+1; Q.push(w); }
        if(dist[w]===dist[v]+1){ sigma[w]+=sigma[v]; P[w].push(v); }
      }
    }
    const delta={}; nodeIds.forEach(v=>delta[v]=0);
    while(S.length){
      const w=S.pop();
      for(const v of P[w]){ delta[v]+= (sigma[v]/sigma[w])*(1+delta[w]); }
      if(w!==s) bc[w]+=delta[w];
    }
  }
  // undirected: divide by 2
  nodeIds.forEach(v=>bc[v]=bc[v]/2);
  return bc;
}

// ---- Louvain community detection ----
function louvain(nodeIds, edgeList){
  // edgeList: [[a,b,w]] undirected, deduped
  const origIndex = new Map(nodeIds.map((id,i)=>[id,i]));
  // membership[originalIndex] = current super-node id
  let membership = nodeIds.map((_,i)=>i);

  // current-level graph
  let N = nodeIds.length;
  let adj = Array.from({length:N},()=>new Map());
  let self = new Array(N).fill(0);
  let m2 = 0;
  for(const [a,b,w0] of edgeList){
    const w=w0||1; const ia=origIndex.get(a), ib=origIndex.get(b);
    if(ia===ib){ self[ia]+=w; m2+=2*w; continue; }
    adj[ia].set(ib,(adj[ia].get(ib)||0)+w);
    adj[ib].set(ia,(adj[ib].get(ia)||0)+w);
    m2+=2*w;
  }
  if(m2===0){ return Object.fromEntries(nodeIds.map(id=>[id,0])); }

  function oneLevel(adj, self, N){
    let comm=[...Array(N).keys()];
    let k=new Array(N).fill(0), tot=new Array(N).fill(0);
    for(let i=0;i<N;i++){ let d=self[i]*2; adj[i].forEach(w=>d+=w); k[i]=d; tot[i]=d; }
    let improved=true, anyMove=false;
    while(improved){
      improved=false;
      for(let i=0;i<N;i++){
        const ci=comm[i];
        const wComm=new Map();
        adj[i].forEach((w,j)=>{ const cj=comm[j]; wComm.set(cj,(wComm.get(cj)||0)+w); });
        tot[ci]-=k[i];
        let bestC=ci, bestGain= (wComm.get(ci)||0) - tot[ci]*k[i]/m2;
        wComm.forEach((wic,C)=>{
          if(C===ci) return;
          const gain = wic - tot[C]*k[i]/m2;
          if(gain>bestGain){ bestGain=gain; bestC=C; }
        });
        tot[bestC]+=k[i]; comm[i]=bestC;
        if(bestC!==ci){ improved=true; anyMove=true; }
      }
    }
    return {comm, anyMove};
  }

  let level=0;
  while(true){
    const {comm, anyMove} = oneLevel(adj, self, N);
    // renumber communities 0..C-1
    const remap=new Map(); let c=0;
    const newComm=comm.map(x=>{ if(!remap.has(x)) remap.set(x,c++); return remap.get(x); });
    // update membership of original nodes
    membership = membership.map(sn=>newComm[sn]);
    if(!anyMove || c===N){ break; }
    // aggregate into c super-nodes
    const nAdj=Array.from({length:c},()=>new Map());
    const nSelf=new Array(c).fill(0);
    for(let i=0;i<N;i++){
      const ci=newComm[i];
      nSelf[ci]+=self[i];
      adj[i].forEach((w,j)=>{
        const cj=newComm[j];
        if(ci===cj){ nSelf[ci]+=w/2; } // each internal edge counted twice across i,j
        else { nAdj[ci].set(cj,(nAdj[ci].get(cj)||0)+w); }
      });
    }
    adj=nAdj; self=nSelf; N=c;
    if(++level>50) break;
  }
  return Object.fromEntries(nodeIds.map((id,i)=>[id, membership[i]]));
}

// ---- Build edges from sample data (work+school+region combined) ----
const d = require('./data.json');
function pairs(groups){ const out=[]; const seen=new Set();
  for(const k in groups){ const m=[...groups[k]];
    for(let i=0;i<m.length;i++)for(let j=i+1;j<m.length;j++){
      const a=Math.min(m[i],m[j]),b=Math.max(m[i],m[j]),key=a+'-'+b;
      if(!seen.has(key)){seen.add(key);out.push([a,b,1]);}
    }} return out; }

let g={}; d.workExperience.forEach(w=>{if(w.institution){(g[w.institution]=g[w.institution]||new Set()).add(w.personId);}});
const work=pairs(g);
g={}; d.people.forEach(p=>{if(p.school){(g[p.school]=g[p.school]||[]).push(p.id);}});
const school=pairs(g);
g={}; d.people.forEach(p=>{if(p.region){(g[p.region]=g[p.region]||[]).push(p.id);}});
const region=pairs(g);

// combine all, dedupe by pair for the simple graph used in metrics
const all=new Map();
[...work,...school,...region].forEach(([a,b])=>{ all.set(a+'-'+b,[a,b,1]); });
const edges=[...all.values()];
const ids=d.people.map(p=>p.id);

// adjacency
const adjMap=new Map(ids.map(id=>[id,[]]));
edges.forEach(([a,b])=>{ adjMap.get(a).push(b); adjMap.get(b).push(a); });

const bc=betweenness(ids,adjMap);
const comm=louvain(ids,edges);

console.log('EDGES ('+edges.length+'):',edges.map(e=>e[0]+'-'+e[1]).join(', '));
console.log('BETWEENNESS:'); ids.forEach(id=>console.log('  p'+id+':',bc[id].toFixed(2)));
console.log('COMMUNITIES:'); const byC={}; ids.forEach(id=>{(byC[comm[id]]=byC[comm[id]]||[]).push(id);});
Object.keys(byC).forEach(c=>console.log('  community '+c+':',byC[c].map(x=>'p'+x).join(', ')));
