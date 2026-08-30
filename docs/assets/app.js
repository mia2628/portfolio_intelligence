
const INPUT_DRAFT_KEY="portfolio_input_draft_v1";

function cleanNumericInput(v){
  return String(v||"").replace(/[^0-9]/g,"");
}
function formatInputKRW(v){
  const n=Number(cleanNumericInput(v));
  return n>0 ? new Intl.NumberFormat("ko-KR").format(n)+"원" : "입력값 없음.";
}
function loadInputDraft(){
  try{return JSON.parse(localStorage.getItem(INPUT_DRAFT_KEY)||"{}");}
  catch{return {};}
}
function syncInputDraftUI(){
  const d=loadInputDraft();
  const s=$("scenarioAmountInput"), a=$("actualAmountInput");
  if(s && !s.value) s.value=d.scenario_amount||"";
  if(a && !a.value) a.value=d.actual_amount||"";
  if($("scenarioAmountPreview")) $("scenarioAmountPreview").textContent=formatInputKRW(s?.value);
  if($("actualAmountPreview")) $("actualAmountPreview").textContent=formatInputKRW(a?.value);
}
function saveInputDraft(){
  const s=cleanNumericInput($("scenarioAmountInput")?.value);
  const a=cleanNumericInput($("actualAmountInput")?.value);
  localStorage.setItem(INPUT_DRAFT_KEY,JSON.stringify({scenario_amount:s,actual_amount:a,saved_at:new Date().toISOString()}));
  syncInputDraftUI();
  const n=$("inputSavedNotice");
  if(n){n.classList.remove("hidden");setTimeout(()=>n.classList.add("hidden"),1800);}
}
function clearInputDraft(){
  localStorage.removeItem(INPUT_DRAFT_KEY);
  if($("scenarioAmountInput")) $("scenarioAmountInput").value="";
  if($("actualAmountInput")) $("actualAmountInput").value="";
  syncInputDraftUI();
}


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


function setText(id,value,fallback="--"){
  const el=$(id);
  if(el)el.textContent=(value===null||value===undefined||value==="")?fallback:value;
}
function markDataState(ok,message){
  const el=document.getElementById("dataStateBanner");
  if(!el)return;
  el.classList.toggle("hidden",ok);
  el.textContent=message||"";
}

function niceAsset(a){
  const m={Bond:"채권",Domestic_Equity:"국내주식",Foreign_Equity:"해외주식",Gold:"금",Cash:"유동성",Other:"기타"};
  return m[a]||a||"--";
}

async function boot(){
  syncAppTitle();
  setAmountVisibility(amountVisible);

  let d=null,trend={points:[]},alerts={active:[],count:0};
  try{
    const [res,tres,ares]=await Promise.all([
      fetch("./data/dashboard.json?ts="+Date.now(),{cache:"no-store"}),
      fetch("./data/trend.json?ts="+Date.now(),{cache:"no-store"}).catch(()=>null),
      fetch("./data/alerts.json?ts="+Date.now(),{cache:"no-store"}).catch(()=>null)
    ]);
    if(!res.ok)throw new Error(`dashboard HTTP ${res.status}`);
    d=await res.json();
    trend=tres ? await tres.json().catch(()=>({points:[]})) : {points:[]};
    alerts=ares ? await ares.json().catch(()=>({active:[],count:0})) : {active:[],count:0};
    latestDashboardData=d;
  }catch(err){
    markDataState(false,"STEP13 데이터 파일을 불러오지 못함. GitHub Pages 배포상태 확인 필요함.");
    console.error(err);
    return;
  }

  setText("updated","업데이트 "+(d.meta?.generated_at ? new Date(d.meta.generated_at).toLocaleString("ko-KR") : "정보 없음"));
  setText("privacyText",amountVisible?"금액 공개":"금액 비공개");

  const risk=d.risk||{};
  setText("riskScore",score(risk.score));
  setText("riskLabel",risk.label||"UNKNOWN");

  const top=(d.opportunity||[])[0]||{};
  setText("oppAsset",niceAsset(top.asset));
  setText("oppScore",score(top.score));

  const health=d.health||{};
  setText("healthScore",score(health.score));
  setText("healthLabel",health.label||"UNKNOWN");

  const conf=d.confidence||{};
  setText("confidencePill",conf.score==null?"DATA --":`DATA ${score(conf.score)} ${conf.label||""}`);

  const rb=d.rebalance||{};
  setText("actionBadge",rb.available?(rb.decision||"CHECK"):"STATUS");

  let final=d.recommendation?.final || rb.reason || "";
  const placeholder=/STEP13 데이터가 아직 생성되지 않았습니다/;
  if(!final || placeholder.test(final)){
    final=rb.reason || "현재 권고 데이터를 생성하지 못함.";
  }
  setText("finalRecommendation",nominalizeKo(final));

  // Each module renders independently: one failure cannot blank the whole dashboard.
  try{
    setText("portfolioTotal",money(d.portfolio?.total_invested));
    renderPortfolio(d.portfolio?.items||[]);
  }catch(e){console.error("portfolio render",e);}

  try{renderScenario(d.allocation||{});}catch(e){console.error("scenario render",e);}
  try{renderWhy(d);}catch(e){console.error("why render",e);}
  try{renderTrend(trend);}catch(e){console.error("trend render",e);}
  try{renderAlerts(alerts);}catch(e){console.error("alert render",e);}

  const live=
    d.meta?.data_state==="GENERATED" &&
    risk.score!=null &&
    health.score!=null &&
    (d.portfolio?.items||[]).length>0;

  markDataState(
    live,
    live ? "" : "일부 STEP13 데이터가 비어 있음. 최신 Actions 실행결과 확인 필요함."
  );
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



const GITHUB_REPO="mia2628/portfolio_intelligence";
const COMMAND_ISSUE_URL=`https://github.com/${GITHUB_REPO}/issues/new`;

function validAmount(v){
  const n=Number(cleanNumericInput(v));
  return Number.isSafeInteger(n) && n>0 && n<=1000000000 ? n : null;
}

function todayYYYYMMDD(){
  const d=new Date();
  const p=n=>String(n).padStart(2,"0");
  return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}`;
}

function showBridgeNotice(text,isError=false){
  const el=$("bridgeNotice");
  if(!el)return;
  el.textContent=text;
  el.classList.remove("hidden","error");
  if(isError)el.classList.add("error");
}

function buildIssueUrl(kind, amount){
  const nonce=`${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
  let title, body;
  if(kind==="scenario"){
    title="[PORTFOLIO_COMMAND] SCENARIO";
    body=[
      "PORTFOLIO_COMMAND_V1",
      "TYPE=SCENARIO",
      `AMOUNT=${amount}`,
      `LAST_REVIEW_DATE=${todayYYYYMMDD()}`,
      `NONCE=${nonce}`,
      "CONFIRM=SCENARIO"
    ].join("\n");
  }else{
    title="[PORTFOLIO_COMMAND] ACTUAL";
    body=[
      "PORTFOLIO_COMMAND_V1",
      "TYPE=ACTUAL",
      `AMOUNT=${amount}`,
      `NONCE=${nonce}`,
      "CONFIRM=CONFIRM_ACTUAL"
    ].join("\n");
  }
  const u=new URL(COMMAND_ISSUE_URL);
  u.searchParams.set("title",title);
  u.searchParams.set("body",body);
  return u.toString();
}

function runScenarioCommand(){
  const amount=validAmount($("scenarioAmountInput")?.value);
  if(!amount){
    showBridgeNotice("가상 시나리오 금액을 1원 이상 숫자로 입력해야 함.",true);
    return;
  }
  saveInputDraft();
  showBridgeNotice("GitHub 명령 작성 화면으로 이동함. 내용 확인 후 Issue를 제출해야 실행됨.");
  window.open(buildIssueUrl("scenario",amount),"_blank","noopener");
}

function runActualCommand(){
  const amount=validAmount($("actualAmountInput")?.value);
  const checked=$("actualConfirmCheck")?.checked;
  if(!amount){
    showBridgeNotice("실제 반영 금액을 1원 이상 숫자로 입력해야 함.",true);
    return;
  }
  if(!checked){
    showBridgeNotice("실제 투자금 반영 확인 체크가 필요함.",true);
    return;
  }
  saveInputDraft();
  showBridgeNotice("실제 반영 명령 작성 화면으로 이동함. 금액을 다시 확인한 후 Issue를 제출해야 함.");
  window.open(buildIssueUrl("actual",amount),"_blank","noopener");
}

["scenarioAmountInput","actualAmountInput"].forEach(id=>{
  const el=$(id);
  if(el){
    el.addEventListener("input",()=>{
      el.value=cleanNumericInput(el.value);
      syncInputDraftUI();
    });
  }
});

if($("runScenarioBtn")) $("runScenarioBtn").addEventListener("click",runScenarioCommand);
if($("runActualBtn")) $("runActualBtn").addEventListener("click",runActualCommand);
if($("actualConfirmCheck")){
  $("actualConfirmCheck").addEventListener("change",()=>{
    $("runActualBtn").disabled=!$("actualConfirmCheck").checked;
  });
}

if($("saveInputDraft")) $("saveInputDraft").addEventListener("click",saveInputDraft);
if($("clearInputDraft")) $("clearInputDraft").addEventListener("click",clearInputDraft);
syncInputDraftUI();

boot().catch(err=>{
  $("updated").textContent="데이터 로딩 실패";
  console.error(err);
});
