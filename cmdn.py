#!/usr/bin/env python3
"""Monitor two existing process groups on Windows or Linux and write CSV samples."""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import multiprocessing as mp
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    print("Missing dependency: install it with `python -m pip install psutil`.", file=sys.stderr)
    raise SystemExit(2)

VERSION = "3.0"

DASHBOARD_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Process Lab · Live comparison</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#121a2b;--panel2:#172237;--border:#26354c;--text:#e7eef9;--muted:#92a2b9;--cyan:#39d2c0;--violet:#a78bfa;--amber:#f6bd60;--red:#fb7185;--blue:#69a9ff;--green:#49d39a;--shadow:0 14px 34px #03071255}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top left,#13233c 0,transparent 40%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}button,select{font:inherit;color:inherit}header{max-width:1440px;margin:auto;padding:30px 30px 18px;display:flex;align-items:flex-end;justify-content:space-between;gap:20px}.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan);font-weight:750}.title{font-size:clamp(27px,3vw,38px);line-height:1.1;letter-spacing:-.04em;margin:8px 0}.subtitle{color:var(--muted);margin:0}.statusbar{display:flex;align-items:center;gap:11px;color:var(--muted);font-size:12px;text-align:right}.live-dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 16px var(--green);display:inline-block;margin-right:7px}.live-dot.off{background:var(--amber);box-shadow:0 0 12px var(--amber)}main{max-width:1440px;margin:auto;padding:0 30px 36px}.toolbar{background:linear-gradient(120deg,#17243a,#131d30);border:1px solid var(--border);border-radius:16px;padding:13px 16px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px;box-shadow:var(--shadow)}.targets{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.target{border:1px solid var(--border);background:#0f1728;border-radius:9px;padding:7px 11px;color:#c6d4e8}.target b{font-weight:700}.target.one b{color:var(--cyan)}.target.two b{color:var(--violet)}.controlset{display:flex;align-items:center;gap:8px}.controlset label{color:var(--muted);font-size:12px}.controlset select,.controlset button{background:#0d1524;border:1px solid var(--border);padding:7px 10px;border-radius:8px}.controlset button{cursor:pointer}.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin-bottom:16px}.card,.kpi{background:linear-gradient(155deg,#151f32,#111929);border:1px solid var(--border);border-radius:15px;box-shadow:var(--shadow)}.kpi{padding:15px 16px;min-height:103px}.k-label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.k-value{font-size:25px;font-weight:730;letter-spacing:-.04em;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.k-sub{font-size:11px;color:var(--muted);margin-top:3px}.cyan{color:var(--cyan)}.violet{color:var(--violet)}.amber{color:var(--amber)}.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.card{padding:16px 18px;min-width:0}.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}.card h2{font-size:15px;letter-spacing:-.01em;margin:0}.card p{font-size:11px;color:var(--muted);margin:3px 0 0}.chartbox{height:250px;position:relative}.wide{grid-column:1/-1}.chartbox.short{height:205px}.chart-unavailable{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:20px;color:#f6bd60;border:1px dashed #5a4a32;border-radius:10px;font-size:12px}.table-wrap{overflow:auto}.stats{width:100%;border-collapse:collapse;white-space:nowrap}.stats th,.stats td{text-align:right;padding:9px 10px;border-bottom:1px solid #26354c}.stats th:first-child,.stats td:first-child{text-align:left}.stats th{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:650}.stats td{font-variant-numeric:tabular-nums}.stats td:first-child{color:#d6e2f2}.callout{font-size:11px;color:var(--muted);border-left:2px solid var(--amber);padding:8px 10px;margin-top:11px;background:#f6bd600b}.empty{padding:18px 20px;border:1px dashed #41516c;border-radius:12px;color:var(--muted);margin:16px 0;display:none}.foot{display:flex;justify-content:space-between;gap:20px;color:var(--muted);font-size:11px;padding:16px 2px 0}.error{color:var(--red)}@media(max-width:1050px){.kpis{grid-template-columns:repeat(3,1fr)}}@media(max-width:760px){header{padding:23px 16px 14px;align-items:flex-start;flex-direction:column}main{padding:0 16px 28px}.statusbar{text-align:left}.toolbar{align-items:flex-start;flex-direction:column}.controlset{width:100%;justify-content:space-between}.charts{grid-template-columns:1fr}.wide{grid-column:auto}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.kpi{padding:12px;min-height:95px}.k-value{font-size:21px}.chartbox{height:225px}.foot{flex-direction:column}}
.lag-card{margin:0 0 14px}.lag-summary{padding:11px 13px;border-radius:9px;background:#0e1726;border:1px solid var(--border);color:#c9d7e8;font-variant-numeric:tabular-nums}.lag-summary.lag-alert{border-color:#7f3445;background:#fb718512;color:#ffb4c0}.lag-summary.lag-ok{border-color:#286350;background:#49d39a10;color:#9fe5c2}
[hidden]{display:none!important}nav{margin-bottom:1em}nav [aria-pressed=true]{border-color:var(--cyan)}dt{font-weight:bold;margin-top:1em}dd{margin:.3em 0;max-width:75ch;line-height:1.6}</style>
</head>
<body>
<header><div><div class="eyebrow">Process Lab / Runtime comparison</div><h1 class="title">Live resource comparison</h1><p class="subtitle">Synchronized process and host readings from the active CSV capture.</p></div><div class="statusbar"><span><i id="liveDot" class="live-dot off"></i><span id="liveLabel">Connecting</span></span><span id="updatedAt">—</span></div></header>
<main><nav aria-label="Dashboard views"><button id="graphsBtn" aria-pressed="true">Graphs</button> <button id="infoBtn" aria-pressed="false">Info</button></nav><div id="graphsView">
<section class="toolbar"><div class="targets"><span class="target one"><b id="labelP1">P1</b> <span id="pidsP1">—</span></span><span class="target two"><b id="labelP2">P2</b> <span id="pidsP2">—</span></span><span id="captureInfo" class="k-sub">Waiting for samples</span></div><div class="controlset"><label for="range">Time range</label><select id="range"><option value="60">Last 1 minute</option><option value="300">Last 5 minutes</option><option value="900">Last 15 minutes</option><option value="all" selected>All loaded</option></select><button id="refreshBtn" type="button">Pause updates</button></div></section>
<div id="empty" class="empty">Waiting for <code>process_comparison.csv</code>. Start the capture command in another terminal; this page will load it automatically.</div>
<section class="kpis">
 <div class="kpi"><div class="k-label">P1 average CPU</div><div class="k-value cyan" id="kCpu1">—</div><div class="k-sub" id="kCpu1Sub">one-core scale</div></div>
 <div class="kpi"><div class="k-label">P2 average CPU</div><div class="k-value violet" id="kCpu2">—</div><div class="k-sub" id="kCpu2Sub">one-core scale</div></div>
 <div class="kpi"><div class="k-label">P1 peak RSS</div><div class="k-value cyan" id="kMem1">—</div><div class="k-sub">resident memory</div></div>
 <div class="kpi"><div class="k-label">P2 peak RSS</div><div class="k-value violet" id="kMem2">—</div><div class="k-sub">resident memory</div></div>
 <div class="kpi"><div class="k-label">Host CPU</div><div class="k-value" id="kHostCpu">—</div><div class="k-sub">whole machine average</div></div>
 <div class="kpi"><div class="k-label">Samples shown</div><div class="k-value" id="kSamples">0</div><div class="k-sub" id="kDuration">—</div></div>
</section>
<section class="card lag-card"><div class="card-head"><div><h2>Lag check</h2><p>Only application response probes can flag measured response delays; CPU or memory differences alone do not prove user-visible lag.</p></div></div><div id="lagSummary" class="lag-summary">Waiting for capture data.</div></section>
<section class="charts">
 <article class="card"><div class="card-head"><div><h2>CPU usage</h2><p>Average per sample interval · one busy logical CPU = 100%</p></div></div><div class="chartbox"><canvas id="cpuChart"></canvas></div></article>
 <article class="card"><div class="card-head"><div><h2>Resident memory</h2><p>RSS for all matching PIDs · MiB</p></div></div><div class="chartbox"><canvas id="memoryChart"></canvas></div></article>
 <article class="card"><div class="card-head"><div><h2>Program reads and writes</h2><p>Read/write counters attributed to each matching process group · MiB/s</p></div></div><div class="chartbox"><canvas id="ioChart"></canvas></div></article>
 <article class="card"><div class="card-head"><div><h2>Disk activity · whole computer</h2><p>Read and write · MiB/s · includes other programs</p></div></div><p id="diskChartMissing" hidden>No measurements in this time range.</p><div class="chartbox"><canvas id="diskChart"></canvas></div></article>
 <article class="card"><div class="card-head"><div><h2>Network traffic · whole computer</h2><p>Received and sent · MiB/s · includes other programs</p></div></div><p id="netChartMissing" hidden>No measurements in this time range.</p><div class="chartbox"><canvas id="netChart"></canvas></div></article>
 <article class="card"><div class="card-head"><div><h2>Whole-computer CPU and memory</h2><p>Whole-machine CPU and used memory · percent</p></div></div><div class="chartbox"><canvas id="systemChart"></canvas></div></article>
 <article class="card"><div class="card-head"><div><h2>HTTP response probe</h2><p>Optional endpoint timing · ms · sampled at configured probe interval</p></div></div><div class="chartbox"><canvas id="probeChart"></canvas></div></article>
 <article class="card wide"><div class="card-head"><div><h2>Descriptive statistics</h2><p>Calculated for the selected time range. Poll rows describe this capture; they are not independent benchmark trials.</p></div></div><div class="table-wrap"><table class="stats"><thead><tr><th>Metric</th><th class="cyan" id="tableP1">P1</th><th class="violet" id="tableP2">P2</th><th>P1 − P2 mean</th></tr></thead><tbody id="statsBody"></tbody></table></div><div class="callout">Use these means, percentiles, and peaks to describe the observed capture. For a statistical claim about which build is faster, repeat matched trials and compare run-level results; do not count every polling row as a separate trial.</div></article>
</section>
<div class="foot"><span id="fileInfo">CSV: process_comparison.csv · refresh every 1 second</span><span>Chart.js line-chart patterns · no data is uploaded by this local dashboard</span></div>
</div><section class="card" id="infoView" hidden><h2>Reading the graphs</h2><dl><dt>Programs and PIDs</dt><dd>A PID identifies one running process. Each program line combines its matching PIDs. Whole-computer panels include all programs.</dd><dt>Elapsed time</dt><dd>The horizontal axis starts when capture begins. CPU and byte rates cover the time between samples, normally 0.25 seconds. Memory is a reading at one instant.</dd><dt>CPU (%)</dt><dd>100% on a program line means one logical CPU fully busy on average. A program using two can reach 200%. On the host graph, 100% means all logical CPUs are busy.</dd><dt>Memory (MiB)</dt><dd>RSS is RAM occupied by the matching processes. One MiB is 1,048,576 bytes. Adding processes can count shared RAM several times. Host memory % shows the share of system RAM used.</dd><dt>Reads and writes (MiB/s)</dt><dd>Program counters follow Windows or Linux I/O accounting. The disk graph shows whole-computer storage traffic. At 4 MiB/s for a quarter second, about 1 MiB moved.</dd><dt>Network (MiB/s)</dt><dd>Received and sent are totals across the computer’s network interfaces. The collector cannot assign those bytes to either program.</dd><dt>Response time (ms)</dt><dd>1,000 milliseconds equals one second. The optional HTTP checks time the supplied URLs. Positive P1 minus P2 means P1’s measured request took longer. Browser freezes require timing the browser action itself.</dd><dt>Summary and missing data</dt><dd>Mean is the average. Peak is the highest observed reading. p95 is the value at or below which at least 95% of readings fall. A gap means no reading. Zero means a measured zero.</dd></dl></section></main>
<script>
const COLORS={p1:'#39d2c0',p2:'#a78bfa',amber:'#f6bd60',blue:'#69a9ff',pink:'#fb7185',green:'#49d39a',muted:'#92a2b9'};
const $=id=>document.getElementById(id);let charts={},allRows=[],paused=false,lastSignature='',latestPayload={};
const fmt=(n,d=1)=>Number.isFinite(n)?new Intl.NumberFormat(undefined,{maximumFractionDigits:d}).format(n):'—';
const mib=b=>Number.isFinite(b)?b/1048576:null;
function quantile(values,q){if(!values.length)return null;const a=[...values].sort((x,y)=>x-y);return a[Math.max(0,Math.ceil(q*a.length)-1)]}
function stats(rows,key,convert=x=>x){const a=rows.map(r=>convert(r[key])).filter(Number.isFinite);return{mean:a.length?a.reduce((s,v)=>s+v,0)/a.length:null,p95:quantile(a,.95),max:a.length?Math.max(...a):null,count:a.length}}
function series(rows,key,convert=x=>x){return rows.map(r=>({x:Number(r.elapsed_s),y:Number.isFinite(convert(r[key]))?convert(r[key]):null}))}
function makeChart(id,label,sets,unit,extra={}){const datasets=sets.map(s=>({label:s.label,data:s.data,borderColor:s.color,backgroundColor:s.color,borderWidth:2,pointRadius:id==='probeChart'?3:0,pointHoverRadius:4,tension:0,spanGaps:false,borderDash:s.dash||[]}));if(charts[id]){charts[id].data.datasets=datasets;charts[id].options.scales.y.beginAtZero=extra.zero!==false;charts[id].update('none');return}const ctx=$(id);charts[id]=new Chart(ctx,{type:'line',data:{datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,parsing:false,normalized:true,interaction:{mode:'index',intersect:false},plugins:{decimation:{enabled:true,algorithm:'min-max',samples:1200},legend:{display:true,position:'bottom',labels:{color:'#a9b9cd',usePointStyle:true,pointStyle:'line',boxWidth:18,padding:15,font:{size:10}}},tooltip:{backgroundColor:'#101827',borderColor:'#35445a',borderWidth:1,titleColor:'#e7eef9',bodyColor:'#d1deef',callbacks:{label:c=>`${c.dataset.label}: ${fmt(c.parsed.y,2)} ${unit}`}}},scales:{x:{type:'linear',grid:{color:'#26354c66'},ticks:{color:'#92a2b9',maxTicksLimit:7,callback:v=>timeLabel(v)},title:{display:true,text:'Elapsed time',color:'#92a2b9',font:{size:10}}},y:{beginAtZero:extra.zero!==false,grid:{color:'#26354c66'},ticks:{color:'#92a2b9',callback:v=>fmt(v,1)},title:{display:true,text:unit,color:'#92a2b9',font:{size:10}}}},...extra.options}})}
function timeLabel(sec){sec=Number(sec);if(!Number.isFinite(sec))return '';const m=Math.floor(sec/60),s=Math.floor(sec%60);return m?`${m}:${String(s).padStart(2,'0')}`:`${s}s`}
function activeRows(){if($('range').value==='all'||!allRows.length)return allRows;const last=Number(allRows[allRows.length-1].elapsed_s)||0;const min=last-Number($('range').value);return allRows.filter(r=>Number(r.elapsed_s)>=min)}
function processDetails(raw){try{return JSON.parse(raw||'[]')}catch{return []}}
function processSummary(raw,fallback){const a=processDetails(raw);return a.length?a.map(p=>`${p.pid} ${p.name||'unknown'}`).join(', '):(fallback||'none')}
function updateDashboard(payload){latestPayload=payload;allRows=payload.rows||[];$('empty').style.display=allRows.length?'none':'block';$('liveDot').classList.toggle('off',!payload.collector_running||!allRows.length);$('liveLabel').textContent=payload.collector_running?(allRows.length?'Live capture':'Starting capture'):(allRows.length?'Capture stopped':'Collector stopped');$('updatedAt').textContent=payload.modified_at?`File updated ${new Date(payload.modified_at).toLocaleTimeString()}`:'—';$('fileInfo').textContent=`CSV: ${payload.data_file||'process_comparison.csv'} · refresh every 1 second${payload.truncated?' · showing latest '+payload.returned_rows.toLocaleString()+' of '+payload.total_rows.toLocaleString()+' rows':''}`;if(!allRows.length){$('empty').textContent=payload.message||'Waiting for samples.';return}
 const rows=activeRows(),first=allRows[0],last=allRows[allRows.length-1],name1=first.p1_search_term||'P1',name2=first.p2_search_term||'P2';$('labelP1').textContent=name1;$('labelP2').textContent=name2;$('tableP1').textContent=`${name1} · mean / p95 / peak`;$('tableP2').textContent=`${name2} · mean / p95 / peak`;$('pidsP1').textContent=`${last.p1_process_count||0} match(es): ${processSummary(last.p1_process_details,last.p1_pids)}`;$('pidsP1').title=processDetails(last.p1_process_details).map(p=>`PID ${p.pid} · ${p.exe||'executable unavailable'} · ${p.username||'user unavailable'}`).join('\n');$('pidsP2').textContent=`${last.p2_process_count||0} match(es): ${processSummary(last.p2_process_details,last.p2_pids)}`;$('pidsP2').title=processDetails(last.p2_process_details).map(p=>`PID ${p.pid} · ${p.exe||'executable unavailable'} · ${p.username||'user unavailable'}`).join('\n');$('captureInfo').textContent=`${rows.length.toLocaleString()} visible samples · ${fmt(last.sample_interval_actual_s,3)}s latest gap`;
 const absent=[!last.p1_process_count && name1,!last.p2_process_count && name2].filter(Boolean);if(absent.length){$('empty').style.display='block';$('empty').textContent='No matching process: '+absent.join(', ')+'. Open the program or check its process name. Other available readings appear below.'}
 const c1=stats(rows,'p1_cpu_pct_one_core'),c2=stats(rows,'p2_cpu_pct_one_core'),m1=stats(rows,'p1_rss_bytes'),m2=stats(rows,'p2_rss_bytes'),hc=stats(rows,'system_cpu_pct');$('kCpu1').textContent=c1.mean===null?'—':`${fmt(c1.mean,1)}%`;$('kCpu1Sub').textContent=`p95 ${fmt(c1.p95,1)}% · peak ${fmt(c1.max,1)}%`;$('kCpu2').textContent=c2.mean===null?'—':`${fmt(c2.mean,1)}%`;$('kCpu2Sub').textContent=`p95 ${fmt(c2.p95,1)}% · peak ${fmt(c2.max,1)}%`;$('kMem1').textContent=m1.max===null?'—':`${fmt(mib(m1.max),1)} MiB`;$('kMem2').textContent=m2.max===null?'—':`${fmt(mib(m2.max),1)} MiB`;$('kHostCpu').textContent=hc.mean===null?'—':`${fmt(hc.mean,1)}%`;$('kSamples').textContent=rows.length.toLocaleString();$('kDuration').textContent=`${timeLabel(Number(last.elapsed_s)||0)} captured · ${first.host_os||'unknown OS'}`;
 const q1=stats(rows,'p1_probe_latency_ms'),q2=stats(rows,'p2_probe_latency_ms'),qDiff=stats(rows,'probe_latency_difference_ms'),threshold=Number(last.lag_threshold_ms)||1000,hasQ1=q1.count>0,hasQ2=q2.count>0;let lagText='No application response probe was configured. Resource differences can point to pressure, but they do not prove user-visible lag. Add --probe-url1 and --probe-url2 to compare response times.';let lagClass='';if(hasQ1||hasQ2){const flags=rows.filter(r=>r.lag_suspected===true).length;if(hasQ1&&hasQ2){const slower=qDiff.count===0?'Unpaired':qDiff.mean>0?name1:qDiff.mean<0?name2:'Neither';lagText=`${slower==='Unpaired'?'No paired response times':slower==='Neither'?'Similar average endpoint times':`${slower} averaged ${fmt(Math.abs(qDiff.mean),1)} ms slower`} · ${name1} mean/p95 ${fmt(q1.mean,1)}/${fmt(q1.p95,1)} ms · ${name2} mean/p95 ${fmt(q2.mean,1)}/${fmt(q2.p95,1)} ms · ${flags} sample(s) at or above ${fmt(threshold,0)} ms.`}else{const label=hasQ1?name1:name2,probe=hasQ1?q1:q2;lagText=`${label} endpoint mean/p95 ${fmt(probe.mean,1)}/${fmt(probe.p95,1)} ms · ${flags} sample(s) at or above ${fmt(threshold,0)} ms. Configure both endpoints to compare the programs.`}lagClass=flags?'lag-alert':'lag-ok'}$('lagSummary').textContent=lagText;$('lagSummary').className=`lag-summary ${lagClass}`;
 if(typeof Chart==='undefined'){$('liveLabel').textContent='Charts need internet';document.querySelectorAll('.chartbox').forEach(box=>{if(!box.querySelector('.chart-unavailable')){const note=document.createElement('div');note.className='chart-unavailable';note.textContent='Chart.js could not load. Connect this browser to the internet and reload to see graphs.';box.appendChild(note)}})}else{
  makeChart('cpuChart','CPU',[{label:name1,data:series(rows,'p1_cpu_pct_one_core'),color:COLORS.p1},{label:name2,data:series(rows,'p2_cpu_pct_one_core'),color:COLORS.p2}],'%',{zero:true});
  makeChart('memoryChart','RSS',[{label:name1,data:series(rows,'p1_rss_bytes',mib),color:COLORS.p1},{label:name2,data:series(rows,'p2_rss_bytes',mib),color:COLORS.p2}],'MiB');
  makeChart('ioChart','Process I/O',[{label:`${name1} read`,data:series(rows,'p1_io_read_bytes_per_s',mib),color:COLORS.p1},{label:`${name1} write`,data:series(rows,'p1_io_write_bytes_per_s',mib),color:COLORS.p1,dash:[5,4]},{label:`${name2} read`,data:series(rows,'p2_io_read_bytes_per_s',mib),color:COLORS.p2},{label:`${name2} write`,data:series(rows,'p2_io_write_bytes_per_s',mib),color:COLORS.p2,dash:[5,4]}],'MiB/s');
  {const lines=[{label:'Read',data:series(rows,'system_disk_read_bytes_per_s',mib),color:COLORS.amber,dash:[]},{label:'write',data:series(rows,'system_disk_write_bytes_per_s',mib),color:COLORS.blue,dash:[5,4]}];const available=lines.some(line=>line.data.some(p=>Number.isFinite(p.y)));$('diskChartMissing').hidden=available;$('diskChart').parentElement.hidden=!available;if(available)makeChart('diskChart','Disk activity',lines,'MiB/s');}
  {const lines=[{label:'Received',data:series(rows,'system_net_recv_bytes_per_s',mib),color:COLORS.amber,dash:[]},{label:'sent',data:series(rows,'system_net_sent_bytes_per_s',mib),color:COLORS.blue,dash:[5,4]}];const available=lines.some(line=>line.data.some(p=>Number.isFinite(p.y)));$('netChartMissing').hidden=available;$('netChart').parentElement.hidden=!available;if(available)makeChart('netChart','Network traffic',lines,'MiB/s');}
  makeChart('systemChart','System',[{label:'Host CPU',data:series(rows,'system_cpu_pct'),color:COLORS.amber},{label:'Host memory used',data:series(rows,'system_memory_used_pct'),color:COLORS.blue}],'%',{zero:true});
  makeChart('probeChart','HTTP probe',[{label:`${name1} response`,data:series(rows,'p1_probe_latency_ms'),color:COLORS.p1},{label:`${name2} response`,data:series(rows,'p2_probe_latency_ms'),color:COLORS.p2},{label:`${name1} − ${name2}`,data:series(rows,'probe_latency_difference_ms'),color:COLORS.amber,dash:[5,4]}],'ms',{zero:false});
 }
 const statDefs=[['CPU · one-core %','p1_cpu_pct_one_core','p2_cpu_pct_one_core',x=>x,'%'],['RSS · MiB','p1_rss_bytes','p2_rss_bytes',mib,'MiB'],['Process read · MiB/s','p1_io_read_bytes_per_s','p2_io_read_bytes_per_s',mib,'MiB/s'],['Process write · MiB/s','p1_io_write_bytes_per_s','p2_io_write_bytes_per_s',mib,'MiB/s'],['HTTP response · ms','p1_probe_latency_ms','p2_probe_latency_ms',x=>x,'ms']];$('statsBody').innerHTML=statDefs.map(([label,k1,k2,conv,unit])=>{const a=stats(rows,k1,conv),b=stats(rows,k2,conv),d=a.mean===null||b.mean===null?null:a.mean-b.mean;return `<tr><td>${label}</td><td>${fmt(a.mean,2)} / ${fmt(a.p95,2)} / ${fmt(a.max,2)}</td><td>${fmt(b.mean,2)} / ${fmt(b.p95,2)} / ${fmt(b.max,2)}</td><td>${d===null?'—':`${d>0?'+':''}${fmt(d,2)} ${unit==='%'?'percentage points':unit}`}</td></tr>`}).join('');
}
for(const info of [true,false]){const button=$(info?'infoBtn':'graphsBtn');button.onclick=()=>{$('graphsView').hidden=info;$('infoView').hidden=!info;$('graphsBtn').setAttribute('aria-pressed',String(!info));$('infoBtn').setAttribute('aria-pressed',String(info));if(!info)Object.values(charts).forEach(c=>c.resize());};}
async function refresh(){try{const response=await fetch('/api/data',{cache:'no-store'});const payload=await response.json();const sig=`${payload.total_rows}:${payload.modified_at}:${payload.message}:${payload.collector_running}`;if(sig!==lastSignature){lastSignature=sig;updateDashboard(payload)}else{$('updatedAt').textContent=payload.modified_at?`File updated ${new Date(payload.modified_at).toLocaleTimeString()}`:'—'}}catch(e){$('liveDot').classList.add('off');$('liveLabel').textContent='Server unavailable';$('empty').style.display='block';$('empty').innerHTML='Could not reach the integrated dashboard. Check cmdn.py and reload this page.'}}
$('range').addEventListener('change',()=>updateDashboard({...latestPayload,rows:allRows}));$('refreshBtn').addEventListener('click',()=>{paused=!paused;$('refreshBtn').textContent=paused?'Resume updates':'Pause updates';$('liveLabel').textContent=paused?'Paused':(latestPayload.collector_running?'Live capture':'Capture stopped')});setInterval(()=>{if(!paused)refresh()},1000);refresh();
</script>
</body>
</html>
'''
SAMPLING_EXPLANATION = (
    "Sampling is periodic polling, not a continuous trace: the monitored program keeps running. "
    "At each tick the collector reads counters, then sleeps until the next tick. CPU percentages "
    "and disk/network rates describe activity since the previous tick; memory is a snapshot at "
    "the tick. Short spikes between ticks can be missed. Use the same interval on both operating "
    "systems. A shorter interval catches briefer changes but adds more monitoring overhead."
)

SAMPLE_FIELDS = [
    "timestamp_utc", "elapsed_s", "sample_interval_actual_s", "pid", "process_name", "process_count",
    "cpu_pct_one_core", "cpu_pct_host", "cpu_user_s", "cpu_system_s",
    "rss_bytes", "process_rss_pct_ram", "vms_bytes", "uss_bytes", "pss_bytes", "memory_footprint_sampled", "num_threads",
    "num_handles_or_fds", "ctx_switches_voluntary", "ctx_switches_involuntary",
    "process_io_read_bytes_total", "process_io_write_bytes_total",
    "process_io_read_bytes_per_s", "process_io_write_bytes_per_s",
    "system_cpu_pct", "system_memory_available_bytes", "system_memory_used_pct",
    "system_disk_read_bytes_per_s", "system_disk_write_bytes_per_s",
    "system_disk_read_latency_ms", "system_disk_write_latency_ms",
    "system_net_sent_bytes_per_s", "system_net_recv_bytes_per_s",
    "probe_latency_ms", "probe_status", "lag_suspected",
]


def delta(new: Any, old: Any) -> float | None:
    if not isinstance(new, (int, float)) or not isinstance(old, (int, float)):
        return None
    difference = new - old
    return float(difference) if difference >= 0 else None


def safe_call(obj: Any, method: str, default: Any = None) -> Any:
    try:
        return getattr(obj, method)()
    except (AttributeError, psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
        return default


def process_set(root: psutil.Process, include_children: bool) -> list[psutil.Process]:
    result = [root]
    if include_children:
        try:
            result.extend(root.children(recursive=True))
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    unique: dict[int, psutil.Process] = {}
    for proc in result:
        unique[proc.pid] = proc
    return list(unique.values())


def process_totals(procs: list[psutil.Process], detailed_memory: bool = True) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "cpu_pct": 0.0, "cpu_user_s": 0.0, "cpu_system_s": 0.0,
        "rss_bytes": 0, "vms_bytes": 0, "uss_bytes": 0, "pss_bytes": 0,
        "io_read": 0, "io_write": 0, "threads": 0, "handles": 0,
        "ctx_voluntary": 0, "ctx_involuntary": 0,
        "have_uss": False, "have_pss": False, "have_io": False,
    }
    count = 0
    for proc in procs:
        try:
            with proc.oneshot():
                cpu_pct = proc.cpu_percent(interval=None)
                cpu = proc.cpu_times()
                mem = proc.memory_info()
                totals["cpu_pct"] += cpu_pct
                totals["cpu_user_s"] += cpu.user
                totals["cpu_system_s"] += cpu.system
                totals["rss_bytes"] += mem.rss
                totals["vms_bytes"] += mem.vms
                totals["threads"] += proc.num_threads()
                handles = safe_call(proc, "num_handles")
                if handles is None:
                    handles = safe_call(proc, "num_fds")
                if handles is not None:
                    totals["handles"] += handles
                ctx = proc.num_ctx_switches()
                totals["ctx_voluntary"] += ctx.voluntary
                totals["ctx_involuntary"] += ctx.involuntary
                if detailed_memory:
                    # Prefer the current psutil API; support older psutil versions too.
                    full = safe_call(proc, "memory_footprint")
                    if full is None:
                        full = safe_call(proc, "memory_full_info")
                    if full is not None:
                        uss = getattr(full, "uss", None)
                        pss = getattr(full, "pss", None)
                        if uss is not None:
                            totals["uss_bytes"] += uss
                            totals["have_uss"] = True
                        if pss is not None:
                            totals["pss_bytes"] += pss
                            totals["have_pss"] = True
                io = safe_call(proc, "io_counters")
                if io is not None:
                    rb = getattr(io, "read_bytes", None)
                    wb = getattr(io, "write_bytes", None)
                    if rb is not None and wb is not None and rb >= 0 and wb >= 0:
                        totals["io_read"] += rb
                        totals["io_write"] += wb
                        totals["have_io"] = True
                count += 1
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            continue
    totals["process_count"] = count
    if not totals["have_uss"]:
        totals["uss_bytes"] = None
    if not totals["have_pss"]:
        totals["pss_bytes"] = None
    if not totals["have_io"]:
        totals["io_read"] = None
        totals["io_write"] = None
    return totals


def probe_url(url: str, timeout: float) -> tuple[float | None, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "cmdn/" + VERSION})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(256)
            status = str(response.status)
    except urllib.error.HTTPError as exc:
        status = str(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        status = "error:" + type(exc).__name__
    return (time.perf_counter() - start) * 1000.0, status


def output_paths(value: str) -> tuple[Path, Path, Path]:
    path = Path(value).expanduser()
    if path.suffix.lower() == ".csv":
        csv_path = path
        base = path.with_suffix("")
    else:
        base = path
        csv_path = Path(str(base) + ".csv")
    return csv_path, Path(str(base) + ".summary.json"), Path(str(base) + ".run.json")


def parse_start_at(value: str) -> float:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        when = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use an ISO-8601 timestamp, for example 2030-01-01T12:30:00Z") from exc
    if when.tzinfo is None:
        raise argparse.ArgumentTypeError("--start-at must include a timezone, for example 2030-01-01T12:30:00Z")
    timestamp = when.timestamp()
    if timestamp <= time.time():
        raise argparse.ArgumentTypeError("--start-at must be a future time")
    return timestamp


def wait_until(timestamp: float) -> None:
    while True:
        remaining = timestamp - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 0.5))


def mean_or_none(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percent / 100.0 * len(ordered)) - 1))
    return ordered[index]


def process_name_key(value: str) -> str:
    base = value.replace("\\", "/").rsplit("/", 1)[-1].casefold()
    return base[:-4] if base.endswith(".exe") else base


def run_monitor(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("Provide a program command after `--`.", file=sys.stderr)
        return 2
    if args.interval <= 0 or args.memory_detail_interval <= 0 or args.probe_interval <= 0 or args.probe_timeout <= 0:
        print("Sampling intervals and timeout must be greater than zero.", file=sys.stderr)
        return 2
    if args.max_duration is not None and args.max_duration <= 0:
        print("--max-duration must be greater than zero.", file=sys.stderr)
        return 2

    csv_path, summary_path, run_path = output_paths(args.out)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    if args.start_at:
        print("Waiting for scheduled start:", dt.datetime.fromtimestamp(args.start_at, dt.timezone.utc).isoformat())
        wait_until(args.start_at)

    launch_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        child = subprocess.Popen(command)
        root = psutil.Process(child.pid)
    except (OSError, psutil.Error) as exc:
        print(f"Could not launch or open program: {exc}", file=sys.stderr)
        return 1

    metadata = {
        "monitor_version": VERSION,
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "total_memory_bytes": psutil.virtual_memory().total,
        "command": command,
        "pid": child.pid,
        "target_mode": "launch",
        "pair_id": args.pair_id,
        "measurement_start_time_utc": launch_utc,
        "sample_interval_seconds": args.interval,
        "memory_detail_interval_seconds": args.memory_detail_interval,
        "sampling_model": "periodic polling; CPU and byte rates cover time since prior sample; memory is sampled at each tick; target process is not paused",
        "includes_child_processes": args.include_children,
        "probe_url": args.probe_url,
        "network_counter_scope": "whole system, all interfaces; not process-attributed",
        "disk_counter_scope": "whole system for system disk rates; process I/O counters are reported separately",
    }
    run_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Started PID {child.pid}; samples: {csv_path}")

    initial_procs = process_set(root, args.include_children)
    for proc in initial_procs:
        try:
            proc.cpu_percent(interval=None)  # Establish the CPU sampling baseline.
        except psutil.Error:
            pass

    previous = process_totals(initial_procs, detailed_memory=False)
    launch_baseline = previous.copy()
    previous_disk = psutil.disk_io_counters()
    previous_net = psutil.net_io_counters()
    psutil.cpu_percent(interval=None)  # Establish the system CPU baseline.
    previous_time = time.monotonic()
    begin_time = previous_time
    last_memory_detail_time = begin_time
    next_probe = begin_time
    cpu_count = max(1, psutil.cpu_count(logical=True) or 1)
    samples: list[dict[str, Any]] = []
    lag_samples = 0
    missed_samples = 0
    next_tick = begin_time + args.interval
    reason = "process_exited"

    try:
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=SAMPLE_FIELDS)
            writer.writeheader()
            while True:
                if child.poll() is not None:
                    break
                if args.max_duration and time.monotonic() - begin_time >= args.max_duration:
                    reason = "max_duration_reached"
                    break
                sleep_for = next_tick - time.monotonic()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                now = time.monotonic()
                dt_s = max(now - previous_time, 1e-9)
                try:
                    procs = process_set(root, args.include_children)
                except psutil.Error:
                    procs = []
                memory_detail_due = now - last_memory_detail_time >= args.memory_detail_interval
                if memory_detail_due:
                    last_memory_detail_time = now
                current = process_totals(procs, detailed_memory=memory_detail_due)
                disk_now = psutil.disk_io_counters()
                net_now = psutil.net_io_counters()
                sys_cpu = psutil.cpu_percent(interval=None)
                virtual = psutil.virtual_memory()

                probe_ms: float | None = None
                probe_status = "not_sampled" if args.probe_url else "not_configured"
                if args.probe_url and now >= next_probe:
                    probe_ms, probe_status = probe_url(args.probe_url, args.probe_timeout)
                    next_probe = now + args.probe_interval
                lag = bool(probe_ms is not None and probe_ms >= args.lag_threshold_ms)
                if lag:
                    lag_samples += 1

                disk_read_rate = disk_write_rate = None
                disk_read_latency = disk_write_latency = None
                if disk_now is not None and previous_disk is not None:
                    dr = delta(getattr(disk_now, "read_bytes", None), getattr(previous_disk, "read_bytes", None))
                    dw = delta(getattr(disk_now, "write_bytes", None), getattr(previous_disk, "write_bytes", None))
                    disk_read_rate = dr / dt_s if dr is not None else None
                    disk_write_rate = dw / dt_s if dw is not None else None
                    dreads = delta(getattr(disk_now, "read_count", None), getattr(previous_disk, "read_count", None))
                    dwrites = delta(getattr(disk_now, "write_count", None), getattr(previous_disk, "write_count", None))
                    drms = delta(getattr(disk_now, "read_time", None), getattr(previous_disk, "read_time", None))
                    dwms = delta(getattr(disk_now, "write_time", None), getattr(previous_disk, "write_time", None))
                    if dreads and drms is not None:
                        disk_read_latency = drms / dreads
                    if dwrites and dwms is not None:
                        disk_write_latency = dwms / dwrites

                net_sent_rate = net_recv_rate = None
                if net_now is not None and previous_net is not None:
                    sent = delta(net_now.bytes_sent, previous_net.bytes_sent)
                    recv = delta(net_now.bytes_recv, previous_net.bytes_recv)
                    net_sent_rate = sent / dt_s if sent is not None else None
                    net_recv_rate = recv / dt_s if recv is not None else None

                process_read_rate = process_write_rate = None
                if current["io_read"] is not None and previous["io_read"] is not None:
                    d = delta(current["io_read"], previous["io_read"])
                    process_read_rate = d / dt_s if d is not None else None
                if current["io_write"] is not None and previous["io_write"] is not None:
                    d = delta(current["io_write"], previous["io_write"])
                    process_write_rate = d / dt_s if d is not None else None

                try:
                    process_name = root.name()
                except psutil.Error:
                    process_name = Path(command[0]).name

                row = {
                    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "elapsed_s": round(now - begin_time, 4),
                    "sample_interval_actual_s": round(dt_s, 6), "pid": child.pid,
                    "process_name": process_name, "process_count": current["process_count"],
                    "cpu_pct_one_core": round(current["cpu_pct"], 4),
                    "cpu_pct_host": round(current["cpu_pct"] / cpu_count, 4),
                    "cpu_user_s": round(current["cpu_user_s"], 4),
                    "cpu_system_s": round(current["cpu_system_s"], 4),
                    "rss_bytes": current["rss_bytes"],
                    "process_rss_pct_ram": round(current["rss_bytes"] / virtual.total * 100.0, 6) if virtual.total else None,
                    "vms_bytes": current["vms_bytes"],
                    "uss_bytes": current["uss_bytes"], "pss_bytes": current["pss_bytes"],
                    "memory_footprint_sampled": memory_detail_due,
                    "num_threads": current["threads"], "num_handles_or_fds": current["handles"],
                    "ctx_switches_voluntary": current["ctx_voluntary"],
                    "ctx_switches_involuntary": current["ctx_involuntary"],
                    "process_io_read_bytes_total": current["io_read"],
                    "process_io_write_bytes_total": current["io_write"],
                    "process_io_read_bytes_per_s": process_read_rate,
                    "process_io_write_bytes_per_s": process_write_rate,
                    "system_cpu_pct": sys_cpu,
                    "system_memory_available_bytes": virtual.available,
                    "system_memory_used_pct": virtual.percent,
                    "system_disk_read_bytes_per_s": disk_read_rate,
                    "system_disk_write_bytes_per_s": disk_write_rate,
                    "system_disk_read_latency_ms": disk_read_latency,
                    "system_disk_write_latency_ms": disk_write_latency,
                    "system_net_sent_bytes_per_s": net_sent_rate,
                    "system_net_recv_bytes_per_s": net_recv_rate,
                    "probe_latency_ms": round(probe_ms, 3) if probe_ms is not None else None,
                    "probe_status": probe_status,
                    "lag_suspected": lag,
                }
                writer.writerow(row)
                csv_file.flush()
                samples.append(row)
                previous, previous_disk, previous_net, previous_time = current, disk_now, net_now, now
                next_tick += args.interval
                if next_tick <= now:
                    missed_samples += 1
                    next_tick = now + args.interval
    except KeyboardInterrupt:
        reason = "monitor_interrupted"

    if child.poll() is None and reason == "process_exited":
        reason = "monitor_stopped"
    wall_time = max((samples[-1]["elapsed_s"] if samples else 0.0), 0.0)
    cpu_values = [float(s["cpu_pct_one_core"]) for s in samples if s["cpu_pct_one_core"] is not None]
    host_cpu_values = [float(s["cpu_pct_host"]) for s in samples if s["cpu_pct_host"] is not None]
    rss_values = [int(s["rss_bytes"]) for s in samples if s["rss_bytes"] is not None]
    uss_values = [int(s["uss_bytes"]) for s in samples if s["uss_bytes"] is not None]
    pss_values = [int(s["pss_bytes"]) for s in samples if s["pss_bytes"] is not None]
    probe_values = [float(s["probe_latency_ms"]) for s in samples if s["probe_latency_ms"] is not None]
    probe_failures = sum(
        1 for s in samples
        if s["probe_status"].startswith("error:")
        or (s["probe_status"].isdigit() and int(s["probe_status"]) >= 400)
    )
    last = samples[-1] if samples else {}

    def total_difference(key: str) -> int | None:
        a, b = launch_baseline.get(key), last.get(key)
        return int(b - a) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b >= a else None

    def seconds_difference(key: str) -> float | None:
        a, b = launch_baseline.get(key), last.get(key)
        return float(b - a) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b >= a else None

    summary = {
        **metadata,
        "monitor_end_reason": reason,
        "process_exit_code": child.poll(),
        "samples": len(samples),
        "memory_footprint_sample_count": sum(1 for sample in samples if sample["memory_footprint_sampled"]),
        "missed_sampling_intervals": missed_samples,
        "measured_wall_seconds": wall_time,
        "lag_probe_threshold_ms": args.lag_threshold_ms,
        "lag_probe_samples_over_threshold": lag_samples,
        "probe_failures": probe_failures,
        "metrics": {
            "avg_process_cpu_pct_one_core": mean_or_none(cpu_values),
            "p95_process_cpu_pct_one_core": percentile(cpu_values, 95),
            "max_process_cpu_pct_one_core": max(cpu_values) if cpu_values else None,
            "avg_process_cpu_pct_host": mean_or_none(host_cpu_values),
            "max_process_cpu_pct_host": max(host_cpu_values) if host_cpu_values else None,
            "process_cpu_user_seconds_delta": seconds_difference("cpu_user_s"),
            "process_cpu_system_seconds_delta": seconds_difference("cpu_system_s"),
            "avg_rss_bytes": mean_or_none([float(x) for x in rss_values]),
            "peak_rss_bytes": max(rss_values) if rss_values else None,
            "avg_process_rss_pct_ram": mean_or_none([float(s["process_rss_pct_ram"]) for s in samples if s["process_rss_pct_ram"] is not None]),
            "peak_process_rss_pct_ram": max([float(s["process_rss_pct_ram"]) for s in samples if s["process_rss_pct_ram"] is not None], default=None),
            "avg_uss_bytes": mean_or_none([float(x) for x in uss_values]),
            "peak_uss_bytes": max(uss_values) if uss_values else None,
            "avg_pss_bytes": mean_or_none([float(x) for x in pss_values]),
            "peak_pss_bytes": max(pss_values) if pss_values else None,
            "process_io_read_bytes_delta": total_difference("process_io_read_bytes_total"),
            "process_io_write_bytes_delta": total_difference("process_io_write_bytes_total"),
            "avg_system_disk_read_bytes_per_s": mean_or_none([float(s["system_disk_read_bytes_per_s"]) for s in samples if s["system_disk_read_bytes_per_s"] is not None]),
            "avg_system_disk_write_bytes_per_s": mean_or_none([float(s["system_disk_write_bytes_per_s"]) for s in samples if s["system_disk_write_bytes_per_s"] is not None]),
            "avg_system_net_sent_bytes_per_s": mean_or_none([float(s["system_net_sent_bytes_per_s"]) for s in samples if s["system_net_sent_bytes_per_s"] is not None]),
            "avg_system_net_recv_bytes_per_s": mean_or_none([float(s["system_net_recv_bytes_per_s"]) for s in samples if s["system_net_recv_bytes_per_s"] is not None]),
            "probe_latency_mean_ms": mean_or_none(probe_values),
            "probe_latency_p95_ms": percentile(probe_values, 95),
            "probe_latency_max_ms": max(probe_values) if probe_values else None,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Finished: exit={child.poll()}, samples={len(samples)}")
    print(f"Raw data: {csv_path}")
    print(f"Run summary: {summary_path}")
    if args.probe_url:
        print(f"Probe samples over {args.lag_threshold_ms:g} ms: {lag_samples}; check probe latency and application logs for actual lag.")
    return 0


T_CRITICAL_95 = [
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
]


def t_critical(n: int) -> float:
    df = n - 1
    return T_CRITICAL_95[df - 1] if 1 <= df <= len(T_CRITICAL_95) else 1.96


def compare_summaries(args: argparse.Namespace) -> int:
    summaries = []
    for file in args.summaries:
        try:
            data = json.loads(Path(file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Cannot read summary {file}: {exc}", file=sys.stderr)
            return 2
        if not isinstance(data.get("metrics"), dict) or not data.get("os"):
            print(f"Not a monitor summary: {file}", file=sys.stderr)
            return 2
        data["summary_file"] = str(file)
        summaries.append(data)
    if not summaries:
        print("Supply at least one .summary.json file.", file=sys.stderr)
        return 2

    metric_names = sorted({key for item in summaries for key, value in item["metrics"].items() if isinstance(value, (int, float)) and math.isfinite(value)})
    platforms = sorted({item["os"] for item in summaries})
    rows: list[dict[str, Any]] = []
    for metric in metric_names:
        stats_by_os: dict[str, dict[str, Any]] = {}
        for os_name in platforms:
            values = [float(item["metrics"][metric]) for item in summaries if item["os"] == os_name and isinstance(item["metrics"].get(metric), (int, float))]
            if not values:
                continue
            n = len(values)
            avg = statistics.fmean(values)
            sd = statistics.stdev(values) if n > 1 else None
            margin = t_critical(n) * sd / math.sqrt(n) if sd is not None else None
            stats_by_os[os_name] = {"n": n, "mean": avg, "median": statistics.median(values), "sd": sd,
                                    "ci_low": avg - margin if margin is not None else None,
                                    "ci_high": avg + margin if margin is not None else None,
                                    "min": min(values), "max": max(values)}
        left = stats_by_os.get("Windows")
        right = stats_by_os.get("Linux")
        difference = left["mean"] - right["mean"] if left and right else None
        relative = (difference / right["mean"] * 100.0) if difference is not None and right["mean"] else None
        paired_values: dict[str, dict[str, float]] = {}
        for item in summaries:
            pair_id = item.get("pair_id")
            value = item["metrics"].get(metric)
            if pair_id and isinstance(value, (int, float)) and math.isfinite(value):
                paired_values.setdefault(str(pair_id), {})[item["os"]] = float(value)
        paired_diffs = [v["Windows"] - v["Linux"] for v in paired_values.values() if "Windows" in v and "Linux" in v]
        paired_n = len(paired_diffs)
        paired_mean = statistics.fmean(paired_diffs) if paired_diffs else None
        paired_sd = statistics.stdev(paired_diffs) if paired_n > 1 else None
        paired_margin = t_critical(paired_n) * paired_sd / math.sqrt(paired_n) if paired_sd is not None else None
        for os_name, values in stats_by_os.items():
            rows.append({
                "metric": metric, "os": os_name, "n_runs": values["n"],
                "mean": values["mean"], "median": values["median"], "standard_deviation": values["sd"],
                "mean_ci95_low": values["ci_low"], "mean_ci95_high": values["ci_high"],
                "min": values["min"], "max": values["max"],
                "windows_minus_linux_mean": difference,
                "windows_vs_linux_percent": relative,
                "paired_n": paired_n,
                "paired_difference_mean": paired_mean,
                "paired_difference_sd": paired_sd,
                "paired_difference_ci95_low": paired_mean - paired_margin if paired_margin is not None else None,
                "paired_difference_ci95_high": paired_mean + paired_margin if paired_margin is not None else None,
            })

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["metric", "os", "n_runs", "mean", "median", "standard_deviation", "mean_ci95_low", "mean_ci95_high", "min", "max", "windows_minus_linux_mean", "windows_vs_linux_percent", "paired_n", "paired_difference_mean", "paired_difference_sd", "paired_difference_ci95_low", "paired_difference_ci95_high"]
    with out_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Statistical comparison written to {out_path}")
    if len(platforms) < 2:
        print("Only one OS is represented so far; add summaries from the other OS to calculate the cross-OS difference.")
    print("95% confidence intervals use a t interval across independent run summaries; run-level samples, not one-second rows, are counted.")
    return 0


def find_process_matches(term: str, excluded_pids: set[int] | None = None) -> list[psutil.Process]:
    """Match every accessible process by a case-insensitive name substring."""
    needle = process_name_key(term)
    excluded = set(excluded_pids or ()) | {os.getpid()}
    found: list[psutil.Process] = []
    for proc in psutil.process_iter(attrs=["name", "exe"]):
        try:
            if proc.pid in excluded:
                continue
            candidates = [proc.info.get("name") or "", proc.info.get("exe") or ""]
            if any(needle in process_name_key(Path(c).name) for c in candidates if c):
                found.append(proc)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            continue
    return sorted({p.pid: p for p in found}.values(), key=lambda p: p.pid)


def collect_processes(args: argparse.Namespace, stop_event: Any = None, excluded_pids: set[int] | None = None) -> int:
    """Sample both process groups. This function runs in its own worker process."""
    if args.p1.casefold() == args.p2.casefold():
        print("-p1 and -p2 must use different search terms.", file=sys.stderr)
        return 2
    if args.interval <= 0 or args.memory_detail_interval <= 0 or args.probe_interval <= 0 or args.probe_timeout <= 0:
        print("Sampling intervals and probe timeout must be greater than zero.", file=sys.stderr)
        return 2
    if args.max_duration is not None and args.max_duration <= 0:
        print("--max-duration must be greater than zero.", file=sys.stderr)
        return 2

    terms = {"p1": args.p1, "p2": args.p2}

    def resolve_group(term: str) -> list[psutil.Process]:
        if term.isdecimal():
            try:
                proc = psutil.Process(int(term))
                proc.status()
                return [proc]
            except psutil.Error as exc:
                raise ValueError(f"PID {term} could not be opened: {exc}") from exc
        return find_process_matches(term, excluded_pids)

    pid_cache: dict[int, psutil.Process] = {}

    def current_group(term: str) -> list[psutil.Process]:
        if term.isdecimal():
            pid = int(term)
            proc = pid_cache.get(pid)
            if proc is None:
                try:
                    proc = psutil.Process(pid)
                    proc.status()
                    pid_cache[pid] = proc
                except psutil.Error:
                    return []
            else:
                try:
                    proc.status()
                except psutil.Error:
                    pid_cache.pop(pid, None)
                    return []
            return [proc]
        return find_process_matches(term, excluded_pids)

    try:
        groups = {key: resolve_group(term) for key, term in terms.items()}
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for key, group in groups.items():
        if not group:
            print(f"Waiting for {terms[key]!r}. Monitoring continues while this program is absent.", flush=True)

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "process_comparison.csv"
    run_path = out_dir / "run.json"
    cpu_count = max(1, psutil.cpu_count(logical=True) or 1)
    total_ram = psutil.virtual_memory().total
    # Prime psutil's per-process CPU counters before measuring the first interval.
    for group in groups.values():
        for proc in group:
            try:
                proc.cpu_percent(interval=None)
            except psutil.Error:
                pass
    previous = {key: process_totals(group, detailed_memory=False) for key, group in groups.items()}
    previous_disk = psutil.disk_io_counters()
    previous_net = psutil.net_io_counters()
    psutil.cpu_percent(interval=None)
    begin = previous_time = time.monotonic()
    last_memory_detail = begin
    next_tick = begin + args.interval
    next_probe = begin
    probe_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cmdn-http-probe")
    probe_futures: dict[str, Any] = {"p1": None, "p2": None}
    latest_probe: dict[str, tuple[float, float] | None] = {"p1": None, "p2": None}
    missed = samples = lag_samples = 0

    metric_names = [
        "process_count", "cpu_pct_one_core", "cpu_pct_host", "cpu_user_s", "cpu_system_s",
        "rss_bytes", "rss_pct_ram", "vms_bytes", "uss_bytes", "pss_bytes", "num_threads",
        "num_handles_or_fds", "ctx_switches_voluntary", "ctx_switches_involuntary",
        "io_read_bytes_total", "io_write_bytes_total", "io_read_bytes_per_s", "io_write_bytes_per_s", "pids", "process_details",
    ]
    fields = ["timestamp_utc", "elapsed_s", "sample_interval_actual_s", "host_os", "logical_cpu_count", "total_memory_bytes"]
    for key in terms:
        fields += [f"{key}_search_term"] + [f"{key}_{name}" for name in metric_names]
    fields += [
        "system_cpu_pct", "system_memory_available_bytes", "system_memory_used_pct",
        "system_disk_read_bytes_per_s", "system_disk_write_bytes_per_s", "system_disk_read_latency_ms", "system_disk_write_latency_ms",
        "system_net_sent_bytes_per_s", "system_net_recv_bytes_per_s", "memory_footprint_sampled",
        "lag_threshold_ms",
        "p1_probe_latency_ms", "p1_probe_status", "p1_lag_suspected",
        "p2_probe_latency_ms", "p2_probe_status", "p2_lag_suspected",
        "probe_latency_difference_ms", "lag_suspected",
    ]
    metadata = {
        "monitor_version": VERSION, "os": platform.system(), "os_release": platform.release(),
        "machine": platform.machine(), "logical_cpu_count": cpu_count, "total_memory_bytes": total_ram,
        "search_terms": terms,
        "matching": "decimal search terms select one exact PID; other terms match case-insensitive substrings in process name or executable basename",
        "process_scope": "all accessible matching processes; process list is refreshed each sample",
        "sample_interval_seconds": args.interval, "memory_detail_interval_seconds": args.memory_detail_interval,
        "disk_scope": "whole machine; process I/O counters are separate",
        "network_scope": "whole machine across interfaces; not attributed to either process group",
        "sampling_model": "CPU and I/O rates cover time since prior poll; memory is read at poll; target processes are not paused",
        "probe_urls": {"p1": args.probe_url1, "p2": args.probe_url2},
        "probe_interval_seconds": args.probe_interval,
        "probe_timeout_seconds": args.probe_timeout,
        "lag_threshold_ms": args.lag_threshold_ms,
        "csv_file": str(csv_path),
    }
    run_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Monitoring all matches for {args.p1!r} and {args.p2!r} every {args.interval:g}s.")
    print(f"CSV: {csv_path} (press Ctrl+C to stop)")

    def group_values(key: str, procs: list[psutil.Process], current: dict[str, Any], old: dict[str, Any], dt_s: float) -> dict[str, Any]:
        identities = []
        for proc in procs:
            try:
                identities.append(proc.as_dict(attrs=["pid", "name", "exe", "username", "create_time"], ad_value=None))
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                identities.append({"pid": proc.pid, "name": None, "exe": None, "username": None, "create_time": None})
        out: dict[str, Any] = {
            f"{key}_search_term": terms[key], f"{key}_process_count": current["process_count"],
            f"{key}_pids": ";".join(str(p.pid) for p in procs),
            f"{key}_process_details": json.dumps(identities, separators=(",", ":")),
            f"{key}_cpu_pct_one_core": current["cpu_pct"], f"{key}_cpu_pct_host": current["cpu_pct"] / cpu_count,
            f"{key}_cpu_user_s": current["cpu_user_s"], f"{key}_cpu_system_s": current["cpu_system_s"],
            f"{key}_rss_bytes": current["rss_bytes"],
            f"{key}_rss_pct_ram": current["rss_bytes"] / total_ram * 100 if total_ram else None,
            f"{key}_vms_bytes": current["vms_bytes"], f"{key}_uss_bytes": current["uss_bytes"], f"{key}_pss_bytes": current["pss_bytes"],
            f"{key}_num_threads": current["threads"], f"{key}_num_handles_or_fds": current["handles"],
            f"{key}_ctx_switches_voluntary": current["ctx_voluntary"], f"{key}_ctx_switches_involuntary": current["ctx_involuntary"],
            f"{key}_io_read_bytes_total": current["io_read"], f"{key}_io_write_bytes_total": current["io_write"],
        }
        for source, target in (("io_read", "io_read_bytes_per_s"), ("io_write", "io_write_bytes_per_s")):
            diff = delta(current[source], old[source]) if current[source] is not None and old[source] is not None else None
            out[f"{key}_{target}"] = diff / dt_s if diff is not None else None
        if not procs:
            identity = {f"{key}_{field}" for field in ("search_term", "process_count", "pids", "process_details")}
            for field in out.keys() - identity:
                out[field] = None
        if not old["process_count"]:
            for field in ("cpu_pct_one_core", "cpu_pct_host", "io_read_bytes_per_s", "io_write_bytes_per_s"):
                out[f"{key}_{field}"] = None
        return out

    try:
        with csv_path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            output.flush()
            while True:
                if stop_event is not None and stop_event.is_set():
                    break
                if args.max_duration is not None and time.monotonic() - begin >= args.max_duration:
                    break
                pause = next_tick - time.monotonic()
                if pause > 0:
                    time.sleep(pause)
                now = time.monotonic()
                dt_s = max(now - previous_time, 1e-9)
                memory_due = now - last_memory_detail >= args.memory_detail_interval
                if memory_due:
                    last_memory_detail = now
                current_groups: dict[str, dict[str, Any]] = {}
                current_procs: dict[str, list[psutil.Process]] = {}
                for key, term in terms.items():
                    current_procs[key] = current_group(term)
                    current_groups[key] = process_totals(current_procs[key], detailed_memory=memory_due)

                disk_now = psutil.disk_io_counters()
                net_now = psutil.net_io_counters()
                vm = psutil.virtual_memory()
                row: dict[str, Any] = {
                    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "elapsed_s": round(now - begin, 6), "sample_interval_actual_s": round(dt_s, 6),
                    "host_os": platform.system(), "logical_cpu_count": cpu_count, "total_memory_bytes": total_ram,
                }
                for key in terms:
                    row.update(group_values(key, current_procs[key], current_groups[key], previous[key], dt_s))
                row.update({
                    "system_cpu_pct": psutil.cpu_percent(interval=None),
                    "system_memory_available_bytes": vm.available, "system_memory_used_pct": vm.percent,
                    "system_disk_read_bytes_per_s": None, "system_disk_write_bytes_per_s": None,
                    "system_disk_read_latency_ms": None, "system_disk_write_latency_ms": None,
                    "system_net_sent_bytes_per_s": None, "system_net_recv_bytes_per_s": None,
                    "memory_footprint_sampled": memory_due,
                    "lag_threshold_ms": args.lag_threshold_ms,
                })
                probe_values: dict[str, float | None] = {"p1": None, "p2": None}
                probe_urls = {"p1": args.probe_url1, "p2": args.probe_url2}
                for key, url in probe_urls.items():
                    status = "not_configured" if not url else "not_sampled"
                    future = probe_futures[key]
                    if future is not None and future.done():
                        probe_values[key], status = future.result()
                        latest_probe[key] = (probe_values[key], now)
                        probe_futures[key] = None
                    row[f"{key}_probe_latency_ms"] = round(probe_values[key], 3) if probe_values[key] is not None else None
                    row[f"{key}_probe_status"] = status
                    row[f"{key}_lag_suspected"] = bool(probe_values[key] is not None and probe_values[key] >= args.lag_threshold_ms)
                if any(probe_urls.values()) and now >= next_probe:
                    for key, url in probe_urls.items():
                        if url and probe_futures[key] is None:
                            probe_futures[key] = probe_pool.submit(probe_url, url, args.probe_timeout)
                    next_probe = now + args.probe_interval
                lag = row["p1_lag_suspected"] or row["p2_lag_suspected"]
                lag_samples += int(lag)
                latest_p1, latest_p2 = latest_probe["p1"], latest_probe["p2"]
                new_probe = probe_values["p1"] is not None or probe_values["p2"] is not None
                recent_pair = latest_p1 is not None and latest_p2 is not None and latest_p1[0] is not None and latest_p2[0] is not None and abs(latest_p1[1] - latest_p2[1]) <= max(args.probe_interval * 2, 2.0)
                row["probe_latency_difference_ms"] = round(latest_p1[0] - latest_p2[0], 3) if new_probe and recent_pair else None
                row["lag_suspected"] = lag
                if disk_now is not None and previous_disk is not None:
                    dr = delta(getattr(disk_now, "read_bytes", None), getattr(previous_disk, "read_bytes", None))
                    dw = delta(getattr(disk_now, "write_bytes", None), getattr(previous_disk, "write_bytes", None))
                    row["system_disk_read_bytes_per_s"] = dr / dt_s if dr is not None else None
                    row["system_disk_write_bytes_per_s"] = dw / dt_s if dw is not None else None
                    dreads = delta(getattr(disk_now, "read_count", None), getattr(previous_disk, "read_count", None))
                    dwrites = delta(getattr(disk_now, "write_count", None), getattr(previous_disk, "write_count", None))
                    drms = delta(getattr(disk_now, "read_time", None), getattr(previous_disk, "read_time", None))
                    dwms = delta(getattr(disk_now, "write_time", None), getattr(previous_disk, "write_time", None))
                    row["system_disk_read_latency_ms"] = drms / dreads if dreads and drms is not None else None
                    row["system_disk_write_latency_ms"] = dwms / dwrites if dwrites and dwms is not None else None
                if net_now is not None and previous_net is not None:
                    sent = delta(net_now.bytes_sent, previous_net.bytes_sent)
                    recv = delta(net_now.bytes_recv, previous_net.bytes_recv)
                    row["system_net_sent_bytes_per_s"] = sent / dt_s if sent is not None else None
                    row["system_net_recv_bytes_per_s"] = recv / dt_s if recv is not None else None
                writer.writerow(row)
                output.flush()
                samples += 1
                previous, groups = current_groups, current_procs
                previous_disk, previous_net, previous_time = disk_now, net_now, now
                next_tick += args.interval
                if next_tick <= now:
                    missed += 1
                    next_tick = now + args.interval
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        probe_pool.shutdown(wait=False, cancel_futures=True)
    print(f"Saved {samples} synchronized rows to {csv_path}; missed polling ticks: {missed}.")
    print(f"Run details: {run_path}")
    if args.probe_url1 or args.probe_url2:
        print(f"HTTP probe samples at or above {args.lag_threshold_ms:g} ms: {lag_samples}.")
    return 0


_CSV_CACHE_LOCK = threading.Lock()
_CSV_CACHE: dict[str, Any] = {"signature": None, "rows": []}


def parse_csv_cell(value: str | None) -> Any:
    if value is None or value == "":
        return None
    if value in ("True", "False"):
        return value == "True"
    try:
        if value.isdecimal():
            return int(value)
        return float(value)
    except ValueError:
        return value


def load_dashboard_rows(path: Path, max_rows: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        stat = path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        return [], {"ready": False, "message": "Waiting for the collector to write its CSV."}
    with _CSV_CACHE_LOCK:
        if _CSV_CACHE["signature"] != signature:
            with path.open("r", newline="", encoding="utf-8-sig") as source:
                _CSV_CACHE["rows"] = [
                    {key: parse_csv_cell(value) for key, value in row.items()}
                    for row in csv.DictReader(source)
                ]
            _CSV_CACHE["signature"] = signature
        total = len(_CSV_CACHE["rows"])
        rows = _CSV_CACHE["rows"][-max_rows:]
    return rows, {
        "ready": True,
        "message": "",
        "data_file": path.name,
        "modified_at": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).isoformat(),
        "total_rows": total,
        "returned_rows": len(rows),
        "truncated": total > max_rows,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    csv_path: Path
    worker: Any
    max_rows: int = 20000

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # The client disconnected while this request was in progress.
            self.close_connection = True

    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]
        if route == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if route in ("/", "/index.html"):
            payload = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if route == "/api/data":
            try:
                rows, meta = load_dashboard_rows(self.csv_path, self.max_rows)
                meta["collector_running"] = self.worker.is_alive()
                meta["collector_exit_code"] = self.worker.exitcode
                if not rows and not meta["collector_running"]:
                    meta["message"] = "Collector stopped before writing samples. Check the terminal for a process-name or permission error."
                response = json.dumps({"rows": rows, **meta}, separators=(",", ":")).encode("utf-8")
            except (OSError, csv.Error, UnicodeError) as exc:
                response = json.dumps({"rows": [], "ready": False, "message": f"Could not read the CSV: {exc}"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return
        self.send_error(404, "Not found")

    def log_message(self, fmt: str, *args: Any) -> None:
        if not self.path.startswith("/api/"):
            super().log_message(fmt, *args)


def compare_live_processes(args: argparse.Namespace) -> int:
    """Start the CSV sampler in a child process and serve its live dashboard."""
    if not args.p1.strip() or not args.p2.strip():
        print("-p1 and -p2 search values cannot be empty.", file=sys.stderr)
        return 2
    if args.p1.casefold() == args.p2.casefold():
        print("-p1 and -p2 must use different search terms.", file=sys.stderr)
        return 2
    if args.interval <= 0 or args.memory_detail_interval <= 0 or args.probe_interval <= 0 or args.probe_timeout <= 0:
        print("Sampling intervals and probe timeout must be greater than zero.", file=sys.stderr)
        return 2
    if args.max_duration is not None and args.max_duration <= 0:
        print("--max-duration must be greater than zero.", file=sys.stderr)
        return 2
    if not (1 <= args.port <= 65535):
        print("--port must be between 1 and 65535.", file=sys.stderr)
        return 2

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    DashboardHandler.csv_path = out_dir / "process_comparison.csv"
    stop_event = mp.Event()
    worker_args = argparse.Namespace(**{k: v for k, v in vars(args).items() if k != "func"})
    worker = mp.Process(
        target=collect_processes,
        args=(worker_args, stop_event, {os.getpid()}),
        name="cmdn-sampler",
        daemon=False,
    )
    try:
        server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    except OSError as exc:
        print(f"Could not start the local webpage at {args.host}:{args.port}: {exc}", file=sys.stderr)
        return 2
    DashboardHandler.worker = worker
    try:
        worker.start()
        url = f"http://{args.host}:{args.port}/"
        print(f"Live dashboard: {url}")
        print(f"CSV output:     {DashboardHandler.csv_path}")
        print("The sampler runs in a separate process; press Ctrl+C to stop both.")
        if not args.no_open:
            try:
                webbrowser.open_new_tab(url)
            except Exception:
                pass
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("Stopping dashboard and sampler...")
    finally:
        server.server_close()
        if worker.is_alive():
            stop_event.set()
            worker.join(timeout=max(5.0, args.probe_timeout + 1.0))
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=2.0)
    print(f"Dashboard/capture ended. CSV remains at {DashboardHandler.csv_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor two existing process groups on Windows or Linux, or launch one program for a single run",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=SAMPLING_EXPLANATION,
    )
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser(
        "run", help="launch a program and collect data until it exits",
        description="Launch a command, capture its PID, and sample it until it exits.",
        epilog=SAMPLING_EXPLANATION,
    )
    run.add_argument("--out", required=True, help="output path prefix, or CSV path")
    run.add_argument("--sample-interval", "--interval", dest="interval", type=float, default=0.25,
                     help="seconds between sample ticks (default: 0.25). CPU and I/O rates cover the preceding interval; memory is a snapshot. The program is not paused")
    run.add_argument("--memory-detail-interval", type=float, default=5.0,
                     help="seconds between slower USS/PSS memory-footprint reads; RSS is still sampled every tick (default: 5)")
    run.add_argument("--start-at", type=parse_start_at, help="shared future ISO-8601 time; the program starts at this time")
    run.add_argument("--pair-id", help="same trial identifier on Windows and Linux, e.g. trial01")
    child_group = run.add_mutually_exclusive_group()
    child_group.add_argument("--include-children", dest="include_children", action="store_true", help="include child processes (this is the default)")
    child_group.add_argument("--no-include-children", dest="include_children", action="store_false", help="measure only the launched parent process")
    run.set_defaults(include_children=True)
    run.add_argument("--max-duration", type=float, help="stop monitoring after this many seconds; does not terminate the program")
    run.add_argument("--probe-url", help="optional read-only HTTP health/response endpoint to measure lag")
    run.add_argument("--probe-interval", type=float, default=1.0, help="seconds between optional HTTP response-time requests (default: 1)")
    run.add_argument("--probe-timeout", type=float, default=3.0, help="maximum wait for each optional HTTP request, in seconds (default: 3)")
    run.add_argument("--lag-threshold-ms", type=float, default=1000.0, help="flag an HTTP response sample at or above this threshold (default: 1000)")
    run.add_argument("command", nargs=argparse.REMAINDER, help="program and arguments, after --")
    run.set_defaults(func=run_monitor)

    compare = sub.add_parser(
        "compare", help="monitor two existing process groups and write synchronized CSV data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Find every process whose name or executable contains each search term, then sample both groups together until Ctrl+C.",
    )
    compare.add_argument("-p1", "--p1", required=True, help="first process name substring, or an exact numeric PID")
    compare.add_argument("-p2", "--p2", required=True, help="second process name substring, or an exact numeric PID")
    compare.add_argument("--out", required=True, help="output folder (creates process_comparison.csv and run.json)")
    compare.add_argument("--sample-interval", "--interval", dest="interval", type=float, default=0.25,
                         help="seconds between sample ticks")
    compare.add_argument("--memory-detail-interval", type=float, default=5.0,
                         help="seconds between USS/PSS reads; other memory fields update each tick")
    compare.add_argument("--max-duration", type=float, help="optional stop time in seconds; otherwise press Ctrl+C")
    compare.add_argument("--probe-url1", help="optional response URL for program 1; use a representative operation")
    compare.add_argument("--probe-url2", help="optional response URL for program 2; use a representative operation")
    compare.add_argument("--probe-interval", type=float, default=1.0, help="seconds between HTTP probes")
    compare.add_argument("--probe-timeout", type=float, default=3.0, help="HTTP probe timeout in seconds")
    compare.add_argument("--lag-threshold-ms", type=float, default=1000.0, help="flag probe latency at or above this value")
    compare.add_argument("--host", default="127.0.0.1", help="web server bind address; local machine only by default")
    compare.add_argument("--port", type=int, default=50080, help="web server port")
    compare.add_argument("--no-open", action="store_true", help="do not open the dashboard in a browser automatically")
    compare.set_defaults(func=compare_live_processes)

    stats = sub.add_parser(
        "stats", help="calculate run-level statistics from summary JSON files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Compare summary files from separate runs; use compare for live paired monitoring.",
    )
    stats.add_argument("--out", required=True, help="comparison CSV output path")
    stats.add_argument("summaries", nargs="+", help="summary JSON files created by run mode")
    stats.set_defaults(func=compare_summaries)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

