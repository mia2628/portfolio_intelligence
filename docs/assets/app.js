const $=id=>document.getElementById(id);
const money=n=>n==null?"비공개":new Intl.NumberFormat("ko-KR").format(n)+"원";
const score=n=>n==null?"--":Number(n).toFixed(1);
const pct=n=>n==null?"--":Number(n).toFixed(2)+"%";
const colors=["#5aa7ff","#54d98c","#f3c95f","#9c86ff","#ff9b66","#ff7373"];

function niceAsset(a){
  const m={Bond:"채권",Domestic_Equity:"국내주식",Foreign_Equity:"해외주식",Gold:"금",Cash:"유동성",Other:"기타"};
  return m[a]||a||"--";
}

async function boot(){
  const res=await fetch("./data/dashboard.json?ts="+Date.now());
  const d=await res.json();

  $("updated").textContent="업데이트 "+new Date(d.meta.generated_at).toLocaleString("ko-KR");
  $("privacyText").textContent=d.meta.privacy_amounts?"금액 표시":"금액 비공개";

  $("riskScore").textContent=score(d.risk.score);
  $("riskLabel").textContent=d.risk.label||"--";

  const top=(d.opportunity||[])[0]||{};
  $("oppAsset").textContent=niceAsset(top.asset);
  $("oppScore").textContent=score(top.score);

  $("healthScore").textContent=score(d.health.score);
  $("healthLabel").textContent=d.health.label||"--";

  const conf=d.confidence||{};
  $("confidencePill").textContent=conf.score==null?"DATA --":`DATA ${score(conf.score)} ${conf.label||""}`;

  const rb=d.rebalance||{};
  $("actionBadge").textContent=rb.available?(rb.decision||"CHECK"):"STATUS";
  $("finalRecommendation").textContent=
    d.recommendation?.final ||
    rb.reason ||
    "현재 유지 가능한 포트폴리오 상태입니다.";

  renderPortfolio(d.portfolio?.items||[]);
  renderScenario(d.allocation||{});
  renderWhy(d);
}

function renderPortfolio(items){
  const list=$("portfolioList");
  list.innerHTML="";
  let start=0;
  const seg=[];

  items.forEach((x,i)=>{
    const w=Number(x.weight||0);
    const end=start+w;
    seg.push(`${colors[i%colors.length]} ${start}% ${end}%`);
    start=end;

    const row=document.createElement("div");
    row.className="asset-row";
    row.innerHTML=`
      <div>
        <div class="asset-name">${x.name||niceAsset(x.asset)}</div>
        <div class="bar"><i style="width:${Math.min(100,w)}%;background:${colors[i%colors.length]}"></i></div>
      </div>
      <div class="asset-value">
        ${pct(w)}
        <div class="muted">${money(x.amount)}</div>
      </div>`;
    list.appendChild(row);
  });

  if(seg.length)$("donut").style.background=`conic-gradient(${seg.join(",")})`;
}

function renderScenario(a){
  if(!a.available){
    $("scenarioPanel").style.display="none";
    return;
  }
  $("scenarioSummary").textContent=`가정한 신규자금 ${money(a.input_amount)} 기준`;
  const box=$("scenarioList");
  box.innerHTML="";

  (a.items||[]).filter(x=>Number(x.share)>0).forEach(x=>{
    const row=document.createElement("div");
    row.className="scenario-row";
    row.innerHTML=`
      <div>
        <b>${niceAsset(x.asset)}</b>
        <div class="bar"><i style="width:${x.share}%;background:#f3c95f"></i></div>
      </div>
      <div class="asset-value">${pct(x.share)}<div class="muted">${money(x.amount)}</div></div>`;
    box.appendChild(row);
  });
}

function renderWhy(d){
  const gp=d.health?.gold_policy||{};
  $("whySummary").innerHTML=`
    <div class="why-row">
      <div>
        <b>금 정책 상태</b>
        <small>현재 ${pct(gp.current)} · 허용 ${gp.lower??"--"}~${gp.upper??"--"}%</small>
      </div>
      <div class="asset-value">${gp.status||"--"}</div>
    </div>`;

  const rc=$("riskContributors");
  rc.innerHTML="";
  (d.risk?.contributors||[]).forEach(x=>{
    const row=document.createElement("div");
    row.className="why-row";
    row.innerHTML=`
      <div><b>${x.indicator}</b><small>${x.explanation||""}</small></div>
      <div class="asset-value">${score(x.adjusted)}</div>`;
    rc.appendChild(row);
  });

  const oc=$("oppComponents");
  oc.innerHTML="";
  const top=(d.opportunity||[])[0];
  if(top){
    const labels={target:"Target",macro:"Macro",risk_adj:"Risk Adj",history:"History",drawdown:"Drawdown"};
    Object.entries(top.components||{}).forEach(([k,v])=>{
      const row=document.createElement("div");
      row.className="why-row";
      row.innerHTML=`<div>${labels[k]||k}</div><div class="asset-value">${score(v)}</div>`;
      oc.appendChild(row);
    });
  }

  const hc=$("healthComponents");
  hc.innerHTML="";
  (d.health?.components||[]).forEach(x=>{
    const row=document.createElement("div");
    row.className="health-row";
    row.innerHTML=`
      <div><b>${x.name}</b><small>${x.status||""}</small></div>
      <div class="asset-value">${score(x.score)}</div>`;
    hc.appendChild(row);
  });
}

$("toggleWhy").addEventListener("click",()=>{
  $("whyDetails").classList.toggle("hidden");
  $("toggleWhy").textContent=$("whyDetails").classList.contains("hidden")?"자세히 보기":"접기";
});

boot().catch(err=>{
  $("updated").textContent="데이터 로딩 실패";
  console.error(err);
});
