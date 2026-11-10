"""Current manuscript experiment source; see docs/REPRODUCTION.md for scope and portability changes."""
import json,hashlib,gc,time
from pathlib import Path
import numpy as np,pandas as pd,pyreadr,joblib
from scipy.stats import beta
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import make_pipeline
from paths import ROOT, RAW_DATA_ROOT, ensure_layout
OUT=ROOT/'experiments/v2';SEED=20261106
def dump(name,obj):
    (OUT/'results'/name).write_text(json.dumps(obj,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v)),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def original(part):
    if part=='Training':return dict(np.load(ROOT/'data/tep_training_features.npz'))
    a=[np.load(ROOT/'data'/f'tep_{k}_testing_features.npz') for k in ['Faulty','FaultFree']]
    return {k:np.concatenate([d[k] for d in a]) for k in ['x','fault','run']}
def dynamic(part):
    dest=OUT/'data'/f'dynamic_{part}.npz'
    if dest.exists():return dict(np.load(dest))
    pre=joblib.load(ROOT/'models/tep_preprocessing.joblib');cols=pre['columns'];sc=pre['scaler'];rows=[];ids=[]
    for kind in ['FaultFree','Faulty']:
        print('extract dynamic',part,kind,flush=True)
        df=next(iter(pyreadr.read_r(str(RAW_DATA_ROOT/'TEP'/f'TEP_{kind}_{part}.RData')).values()))
        df=df.loc[df['sample']>(20 if part=='Training' else 160)].sort_values(['faultNumber','simulationRun','sample'])
        for (fault,run),g in df.groupby(['faultNumber','simulationRun'],sort=True):
            z=(g[cols].to_numpy()-sc.mean_)/sc.scale_;half=len(z)//2
            row=np.r_[z.std(0),np.quantile(z,.1,axis=0),np.quantile(z,.9,axis=0),z[half:].mean(0)-z[:half].mean(0),np.sqrt(np.mean(np.diff(z,axis=0)**2,axis=0))]
            rows.append(row);ids.append((int(fault),int(run)))
        del df;gc.collect()
    a=np.array(ids);np.savez_compressed(dest,x=np.array(rows),fault=a[:,0],run=a[:,1]);return dict(np.load(dest))
def merged(part):
    a=original(part);d=dynamic(part);lookup={(f,r):x for f,r,x in zip(d['fault'],d['run'],d['x'])}
    return a,np.column_stack([a['x'],np.array([lookup[(f,r)] for f,r in zip(a['fault'],a['run'])])])
def evaluate(y,r):
    y=np.asarray(y);r=np.asarray(r);nfault=int(sum(y==1));nnormal=int(sum(y==0));fb=int(sum((y==1)&(r==0)));nf=int(sum((y==0)&(r==1)))
    uf=float(beta.ppf(.975,fb+1,nfault-fb)) if fb<nfault else 1.;un=float(beta.ppf(.975,nf+1,nnormal-nf)) if nf<nnormal else 1.
    auto=int(sum(r!=-1));correct=int(sum((r==y)&(r!=-1)))
    return dict(n=len(y),n_fault=nfault,n_normal=nnormal,FB=fb,NF=nf,FB_upper=uf,NF_upper=un,pass_risk=uf<=.05 and un<=.10,coverage=auto/len(y),automatic=auto,fault_recognized=int(sum((y==1)&(r==1))),normal_recognized=int(sum((y==0)&(r==0))),abstain=int(sum(r==-1)),accepted_error=(auto-correct)/auto if auto else None)
def route(s,lo,hi,veto=None):
    benign=(s<=lo)&(np.ones(len(s),bool) if veto is None else veto)
    return np.where(benign,0,np.where(s>=hi,1,-1))
def search(y,s,ok):
    grid=np.r_[-.01,np.linspace(0,1,101),1.01];out=[];nF=sum(y==1);nN=sum(y==0)
    uf=np.r_[beta.ppf(.975,np.arange(nF)+1,nF-np.arange(nF)),1.]
    un=np.r_[beta.ppf(.975,np.arange(nN)+1,nN-np.arange(nN)),1.]
    for lo in grid:
        benign=(s<=lo)&ok;fb=int(sum(benign&(y==1)))
        if uf[fb]>.05:continue
        for hi in grid[grid>lo]:
            fault=s>=hi;nf=int(sum(fault&(y==0)))
            if un[nf]<=.1:out.append(dict(lo=float(lo),hi=float(hi),coverage=float(np.mean(benign|fault)),FB=fb,NF=nf,FB_upper=float(uf[fb]),NF_upper=float(un[nf])))
    return sorted(out,key=lambda x:(-x['coverage'],x['FB_upper'],x['lo'],x['hi']))[:1]
