"""Read-only network receipt. Never creates approvals/fills or connects a wallet.
Stops a failing provider; no retries, endpoint fallback, proxy bypass or credentials.
"""
import sys,json,os
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import trading_terminal as m
mint='So11111111111111111111111111111111111111112'
report={'started_utc':m.utc(),'mode':'READ ONLY; no approvals/fills/wallet/transactions','providers':{},
 'actual_kill_file_present':m.KILL_PATH.exists()}
for name,reader in [('dexscreener',lambda:m.read_market(mint)),('solana_rpc',lambda:m.read_authority(mint))]:
 try:
  data=reader()
  report['providers'][name]={'status':'READ SUCCESS','data':data}
 except Exception as e:report['providers'][name]={'status':'UNAVAILABLE; no alternate endpoint attempted','error':str(e)}
try:
 params=m.urlencode({'inputMint':m.USDC,'outputMint':mint,'amount':'1000000','slippageBps':100})
 raw,meta=m.public_json(m.JUP+'?'+params)
 report['providers']['jupiter']={'status':'READ SUCCESS','provenance':meta,
  'input_mint':raw.get('inputMint'),'output_mint':raw.get('outputMint'),'in_amount':raw.get('inAmount'),
  'out_amount':raw.get('outAmount'),'request_id':raw.get('requestId'),'route_steps':len(raw.get('routePlan',[])),
  'no_transaction':not bool(raw.get('transaction')),'no_taker':not bool(raw.get('taker')),
  'provenance_fresh_at_read':m.provenance_ok(meta,datetime.now(timezone.utc),30)}
 # Exercise production quote parser and local model on real source observations, but
 # deliberately never construct a ledger proposal, approval or fill.
 row=report['providers']['dexscreener']['data'][0]
 audit=report['providers']['solana_rpc']['data']
 seed={'mint':mint,'pair':row['pair'],'side':'BUY','usd':'1','quantity':'0','slippage_pct':'1'}
 quote=m.RouteModel.parse(raw,meta,seed,audit,1000000,m.USDC,mint)
 ticket=m.build_ticket(row,audit,quote,'BUY','1','0','1','READ_ONLY_NO_ORDER')
 report['local_model_preview_only']=m.RouteModel.simulate(ticket,row,audit,quote,datetime.now(timezone.utc))
 report['local_model_preview_only']['NOT_A_FILL']='No gate clearance, approval, order, position or ledger write was performed'
except Exception as e:report['providers']['jupiter']={'status':'UNAVAILABLE; no alternate endpoint attempted','error':str(e)}
try:m.DeskEvidence().read(datetime.now(timezone.utc))
except m.Blocked as e:report['runtime_gate_blocker']=str(e)
report['finished_utc']=m.utc()
path=Path(os.environ.get('PUMPGROK_SMOKE_OUTPUT',str(Path(__file__).resolve().parents[1]/'evidence'/'public-read-smoke.json')));path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
