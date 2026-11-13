"""只读获取官方Codex额度安全快照；不输出账户或凭据。"""
import argparse
from pathlib import Path
import subprocess,json,threading,queue,datetime
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output",type=Path,required=True)
args=parser.parse_args()
exe=max(Path(r"C:\Users\zephy\AppData\Local\OpenAI\Codex\bin").glob("*/codex.exe"),key=lambda p:p.stat().st_mtime)
p=subprocess.Popen([str(exe),"app-server","--listen","stdio://"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding="utf-8")
q=queue.Queue()
def reader():
 for line in p.stdout:
  try:q.put(json.loads(line))
  except ValueError:pass
threading.Thread(target=reader,daemon=True).start()
def rpc(i,m,params):
 p.stdin.write(json.dumps({"id":i,"method":m,"params":params})+"\n");p.stdin.flush()
 while True:
  r=q.get(timeout=30)
  if r.get("id")==i:
   assert "error" not in r,r
   return r["result"]
try:
 init=rpc(1,"initialize",{"clientInfo":{"name":"quota_readonly_check","version":"1.0"}})
 p.stdin.write('{"method":"initialized"}\n');p.stdin.flush()
 result=rpc(2,"account/rateLimits/read",{})
 out={"checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"ordinaryUsageAllowed":result["ordinaryUsageAllowed"],"rateLimits":result["rateLimits"],"available_reset_credits":result.get("rateLimitResetCredits",{}).get("availableCount"),"source":"official account/rateLimits/read ordinary user"}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
 print(json.dumps(out))
finally:
 p.kill();p.wait()
