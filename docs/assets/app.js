const money=n=>n==null?"비공개":new Intl.NumberFormat("ko-KR").format(n)+"원";
const pct=n=>n==null?"--":Number(n).toFixed(2)+"%";
const score=n=>n==null?"--":Number(n).toFixed(1);
const $=id=>document.getElementById(id);
const colors=["#4ca3ff","#43d17a","#f4c451","#9d7cff","#ff8d5c","#ff6b6b"];

async function boot(){
  const res=await fetch("./data/dashboard.json?ts="+Date.now());
  const d=await res.json();
  $("updated").textContent="업데이트 "+new Date(d.meta.generated_at).toLocaleString("ko-KR");
  $("privacyText").textContent=d.meta.privacy_amounts?"금액 표시":"금액 비공개";

  $("riskScore").textContent=score(d.risk.score); $("riskLabel").textContent=d.risk.label;
  const top=d.opportunity?.[0]||{};
  $("oppAsset").textContent=top.asset||"--"; $("oppScore").textContent=score(top.score);
  $("healthScore").textContent=score(d.health.score); $("healthLabel").textContent=d.health.label;

  const conf=d.confidence||{};
  $("confidencePill").textContent=conf.score==null?"DATA --":`DATA ${score(conf.score)} ${conf.label||""}`;

  const rb=d.rebalance||{};
  $("actionBadge").textContent=rb.available?(rb.decision||"CHECK"):"STATUS";
  $("finalRecommendation").textContent=d.recommendation.final||rb.reason||"현재 권고 문구를 생성할 수 없습니다.";

  renderPortfolio(d.portfolio.items||[]);
  renderScenario(d.allocation||{});
  renderWhy(d);
}
function renderPortfolio(items){
  const list=$("portfolioList"); list.innerHTML="";
  let start=0, seg=[];
  items.forEach((x,i)=>{
    const end=start+Number(x.weight||0); seg.push(`${colors[i%colors.length]} ${start}% ${end}%`); start=end;
    const row=document.createElement("div"); row.className="asset-row";
    row.innerHTML=`<div><div class="asset-name">${x.name}</div><div class="bar"><i style="width:${Math.min(100,x.weight)}%;background:${colors[i%colors.length]}"></i></div></div><div class="asset-value">${pct(x.weight)}<br><span class="muted">${money(x.amount)}</span></div>`;
    list.appendChild(row);
  });
  if(seg.length)$("donut").style.background=`conic-gradient(${seg.join(",")})`;
}
function renderScenario(a){
  if(!a.available){$("scenarioPanel").style.display="none";return;}
  $("scenarioSummary").textContent=`가정한 신규자금 ${money(a.input_amount)} 배분안`;
  const box=$("scenarioList");box.innerHTML="";
  (a.items||[]).filter(x=>x.share>0).forEach(x=>{
    const row=document.createElement("div");row.className="scenario-row";
    row.innerHTML=`<div>${x.asset}<div class="bar"><i style="width:${x.share}%"></i></div></div><div class="asset-value">${pct(x.share)}<br><span class="muted">${money(x.amount)}</span></div>`;
    box.appendChild(row);
  });
}
function renderWhy(d){
  const summary=$("whySummary");
  const gp=d.health.gold_policy||{};
  summary.innerHTML=`<div class="why-row"><div><b>금 정책</b><small>현재 ${pct(gp.current)} · 허용 ${gp.lower??"--"}~${gp.upper??"--"}%</small></div><div class="asset-value">${gp.status||"--"}</div></div>`;
  const rc=$("riskContributors");rc.innerHTML="";
  (d.risk.contributors||[]).forEach(x=>{
    const r=document.createElement("div");r.className="why-row";
    r.innerHTML=`<div><b>${x.indicator}</b><small>${x.explanation||""}</small></div><div>${score(x.adjusted)}</div>`;rc.appendChild(r);
  });
  const oc=$("oppComponents");oc.innerHTML="";
  const top=d.opportunity?.[0];
  if(top){Object.entries(top.components||{}).forEach(([k,v])=>{const r=document.createElement("div");r.className="why-row";r.innerHTML=`<div>${k}</div><div>${score(v)}</div>`;oc.appendChild(r);});}
  const hc=$("healthComponents");hc.innerHTML="";
  (d.health.components||[]).forEach(x=>{const r=document.createElement("div");r.className="health-row";r.innerHTML=`<div>${x.name}<small>${x.status||""}</small></div><div>${score(x.score)}</div>`;hc.appendChild(r);});
}
$("toggleWhy").addEventListener("click",()=>{$("whyDetails").classList.toggle("hidden");$("toggleWhy").textContent=$("whyDetails").classList.contains("hidden")?"자세히":"접기";});
boot().catch(e=>{$("updated").textContent="데이터 로딩 실패";console.error(e);});
