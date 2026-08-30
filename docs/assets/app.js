
const APP_TITLE="포트폴리오 정책 자동화";
const AMOUNT_VISIBILITY_KEY="portfolio_amount_visibility_v1";
let amountVisible = localStorage.getItem(AMOUNT_VISIBILITY_KEY)==="visible";
let latestDashboardData=null;

function syncAppTitle(){
  document.title=APP_TITLE;
  const h1=document.querySelector(".app-header h1");
  if(h1) h1.textContent=APP_TITLE;
}

function setAmountVisibility(visible){
  amountVisible=Boolean(visible);
  localStorage.setItem(AMOUNT_VISIBILITY_KEY, amountVisible ? "visible" : "hidden");
  const toggle=document.getElementById("amountVisibilityToggle");
  const label=document.getElementById("privacyLabel");
  if(toggle) toggle.checked=amountVisible;
  if(label) label.textContent=amountVisible ? "금액 공개" : "금액 비공개";
  document.body.classList.toggle("amounts-hidden", !amountVisible);
}

const $=id=>document.getElementById(id);
const money=n=>n==null?"--":(!amountVisible?"••••••":new Intl.NumberFormat("ko-KR").format(n)+"원");
const score=n=>n==null?"--":Number(n).toFixed(1);
const pct=n=>n==null?"--":Number(n).toFixed(2)+"%";

function nominalizeKo(text){
  if(!text)return "";
  let t=String(text).trim();
  t=t.replace(/합니다\.$/,"함.")
     .replace(/됩니다\.$/,"됨.")
     .replace(/입니다\.$/,"임.")
     .replace(/있습니다\.$/,"있음.")
     .replace(/없습니다\.$/,"없음.")
     .replace(/권고합니다\.$/,"권고함.");
  return t;
}

const colors=["#5aa7ff","#54d98c","#f3c95f","#9c86ff","#ff9b66","#ff7373"];

function niceAsset(a){
  const m={Bond:"채권",Domestic_Equity:"국내주식",Foreign_Equity:"해외주식",Gold:"금",Cash:"유동성",Other:"기타"};
  return m[a]||a||"--";
}

async function boot(){
  syncAppTitle();
  setAmountVisibility(amountVisible);
  const [res,tres,ares]=await Promise.all([
    fetch("./data/dashboard.json?ts="+Date.now()),
    fetch("./data/trend.json?ts="+Date.now()).catch(()=>null),
    fetch("./data/alerts.json?ts="+Date.now()).catch(()=>null)
  ]);
  const d=await res.json();
  latestDashboardData=d;
  const trend=tres ? await tres.json().catch(()=>({points:[]})) : {points:[]};
  const alerts=ares ? await ares.json().catch(()=>({active:[],count:0})) : {active:[],count:0};

  $("updated").textContent="업데이트 "+new Date(d.meta.generated_at).toLocaleString("ko-KR");
  $("privacyText").textContent=amountVisible?"금액 공개":"금액 비공개";

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
  $("finalRecommendation").textContent=nominalizeKo(
    d.recommendation?.final ||
    rb.reason ||
    "현재 유지 가능한 포트폴리오 상태임."
  );

  $("portfolioTotal").textContent = money(d.portfolio?.total_invested);
  renderPortfolio(d.portfolio?.items||[]);
  renderScenario(d.allocation||{});
  renderWhy(d);
  renderTrend(trend);
  renderAlerts(alerts);
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

function renderAlerts(a){
  const list=$("alertList"), empty=$("alertEmpty"), count=$("alertCount"), level=$("alertLevel");
  const items=a?.active||[];
  count.textContent=String(items.length);
  const hasHigh=items.some(x=>(x.severity||"").toUpperCase()==="HIGH");
  level.textContent=hasHigh?"HIGH":items.length?"MEDIUM":"NORMAL";
  level.style.color=hasHigh?"#ff8f98":items.length?"#f1cb68":"#65d697";
  list.innerHTML="";
  if(!items.length){
    empty.style.display="block";
    return;
  }
  empty.style.display="none";
  items.forEach(x=>{
    const row=document.createElement("div");
    const sev=(x.severity||"MEDIUM").toLowerCase();
    row.className=`alert-item ${sev}`;
    row.innerHTML=`
      <div class="alert-item-title">
        <span>${x.title||"정책 경보"}</span>
        <span class="alert-severity">${x.severity||"MEDIUM"}</span>
      </div>
      <div class="alert-message">${nominalizeKo(x.message||"")}</div>`;
    list.appendChild(row);
  });
}

let trendData={points:[]};
let trendDays=7;

function renderTrend(t,days=trendDays){
  trendData=t||{points:[]};
  trendDays=days;
  const all=(trendData?.points||[]).filter(x=>x.date);
  const pts=all.slice(-days);
  const svg=$("trendChart"), empty=$("trendEmpty"), insight=$("trendInsight");

  document.querySelectorAll(".range-btn").forEach(b=>{
    b.classList.toggle("active",Number(b.dataset.days)===days);
  });

  if(pts.length<2){
    svg.innerHTML="";
    empty.style.display="grid";
    insight.textContent=pts.length===1
      ?"첫 기준점 저장됨. 다음 일자부터 변화 방향 확인 가능함."
      :"누적 데이터 없음.";
    return;
  }

  empty.style.display="none";
  const W=640,H=210,padX=18,padY=18;
  const y=v=>padY+(100-Math.max(0,Math.min(100,Number(v))))*(H-padY*2)/100;
  const x=i=>padX+i*(W-padX*2)/(pts.length-1);
  let markup="";

  [25,50,75].forEach(v=>{
    markup+=`<line class="trend-grid" x1="${padX}" y1="${y(v)}" x2="${W-padX}" y2="${y(v)}"/>`;
  });

  const series=[
    ["risk","trend-risk"],
    ["health","trend-health"],
    ["opportunity_score","trend-opp"]
  ];

  series.forEach(([key,cls])=>{
    const valid=pts.map((p,i)=>({v:p[key],i})).filter(o=>o.v!=null);
    if(valid.length<2)return;
    const path=valid.map((o,j)=>`${j===0?"M":"L"} ${x(o.i).toFixed(1)} ${y(o.v).toFixed(1)}`).join(" ");
    markup+=`<path class="trend-line ${cls}" d="${path}"/>`;
    const last=valid[valid.length-1];
    markup+=`<circle cx="${x(last.i)}" cy="${y(last.v)}" r="4" fill="currentColor" class="${cls}"/>`;
  });

  svg.innerHTML=markup;

  const first=pts[0],last=pts[pts.length-1];
  const delta=(a,b)=>(a==null||b==null)?null:Number(b)-Number(a);
  const fmt=v=>v==null?"--":`${v>=0?"+":""}${v.toFixed(1)}`;
  insight.textContent=`${pts.length}개 기준점 · Risk ${fmt(delta(first.risk,last.risk))} · Health ${fmt(delta(first.health,last.health))} · 최고기회 ${niceAsset(last.opportunity_asset)} ${score(last.opportunity_score)}임.`;
}

document.querySelectorAll(".range-btn").forEach(btn=>{
  btn.addEventListener("click",()=>renderTrend(trendData,Number(btn.dataset.days)));
});

$("toggleWhy").addEventListener("click",()=>{
  $("whyDetails").classList.toggle("hidden");
  $("toggleWhy").textContent=$("whyDetails").classList.contains("hidden")?"자세히 보기":"접기";
});


const amountToggle=document.getElementById("amountVisibilityToggle");
if(amountToggle){
  amountToggle.addEventListener("change",()=>{
    setAmountVisibility(amountToggle.checked);
    if(latestDashboardData){
      $("portfolioTotal").textContent=money(latestDashboardData.portfolio?.total_invested);
      renderPortfolio(latestDashboardData.portfolio?.items||[]);
      renderScenario(latestDashboardData.allocation||{});
    }
  });
}

boot().catch(err=>{
  $("updated").textContent="데이터 로딩 실패";
  console.error(err);
});
