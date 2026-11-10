"""Current manuscript experiment source; see docs/REPRODUCTION.md for scope and portability changes."""
import numpy as np
from sklearn.metrics import roc_auc_score
from v2_numeric import ROOT, route, evaluate
import json
OUT=ROOT/'experiments/v4'
def dump(n,x):
    (OUT/'results'/n).write_text(json.dumps(x,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v)),encoding='utf-8')

def calibrate(y,s):
    grid=np.unique(np.r_[-np.inf,np.quantile(s,np.linspace(0,1,201)),np.inf]);best=None
    for lo in grid:
        benign=s<=lo;fb=np.mean(benign[y==1]);nr=np.mean(benign[y==0])
        if fb>.05:continue
        for hi in grid[grid>lo]:
            fault=s>=hi;nf=np.mean(fault[y==0]);fr=np.mean(fault[y==1])
            if nf>.05:continue
            q={'lo':float(lo),'hi':float(hi),'coverage':float(np.mean(benign|fault)),'FB_rate':float(fb),'NF_rate':float(nf),'balanced_recognition':float((nr+fr)/2),'fault_recall':float(fr)}
            if best is None or (-q['balanced_recognition'],-q['coverage'],fb,lo,hi)<(-best['balanced_recognition'],-best['coverage'],best['FB_rate'],best['lo'],best['hi']):best=q
    return best

def metric(y,r,s=None):
    m=evaluate(y,r)
    for key in ['FB_upper','NF_upper','pass_risk']:m.pop(key)
    m['balanced_recognition']=.5*(m['fault_recognized']/m['n_fault']+m['normal_recognized']/m['n_normal'])
    if s is not None:m['AUROC']=float(roc_auc_score(y,s))
    return m
