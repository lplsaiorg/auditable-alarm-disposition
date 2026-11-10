"""Current manuscript experiment source; see docs/REPRODUCTION.md for scope and portability changes."""
import json, hashlib
from pathlib import Path
import numpy as np, pandas as pd, joblib
from sklearn.metrics import roc_auc_score
from v2_numeric import ROOT, merged, evaluate, route, search
OUT=ROOT/'experiments/v3'
def dump(n,x):
    (OUT/'results'/n).write_text(json.dumps(x,indent=2,default=lambda v:v.item() if hasattr(v,'item') else str(v)),encoding='utf-8')
def risk():
    a,x=merged('Testing'); f=a['fault'].astype(int); run=a['run'].astype(int); y=(f>0).astype(int)
    names=[f'{kind}_hist_w{w}' for kind in ['mean','dynamic'] for w in [1,5,20]]+[f'{kind}_logistic_balanced' for kind in ['mean','dynamic']]
    scores={n:joblib.load(ROOT/'experiments/v2/models'/f'{n}.joblib').predict_proba(x[:,:118 if n.startswith('mean') else 378])[:,1] for n in names}
    def sample(groups,rng):
        ids=list(np.flatnonzero((f==0)&np.isin(run,groups)))
        for fault in range(1,21):
            candidates=np.flatnonzero((f==fault)&np.isin(run,groups));ids.extend(rng.choice(candidates,20,replace=False))
        return np.array(ids)
    results=[];pred=[];bindings=[]
    for seed in [20261107,20261108,20261109]:
        rng=np.random.default_rng(seed); folds=np.array_split(rng.permutation(np.unique(run)),5)
        for fold,groups in enumerate(folds):
            calibration=rng.choice(np.setdiff1d(np.unique(run),groups),100,replace=False);ci=sample(calibration,rng);ti=sample(groups,rng)
            assert not set(run[ci])&set(run[ti]);candidates=[]
            for n in names:
                z=search(y[ci],scores[n][ci],np.ones(len(ci),bool))
                if z:candidates.append(dict(z[0],model=n))
            best=sorted(candidates,key=lambda q:(-q['coverage'],q['FB_upper'],names.index(q['model']),q['lo'],q['hi']))[0]
            r=route(scores[best['model']][ti],best['lo'],best['hi']);m=evaluate(y[ti],r)
            results.append(dict(seed=seed,fold=fold,policy=best,**m));bindings.append(dict(seed=seed,fold=fold,calibration=calibration.tolist(),evaluation=groups.tolist()))
            pred.extend(dict(seed=seed,fold=fold,fault=int(f[i]),run=int(run[i]),route=int(v)) for i,v in zip(ti,r))
            print('risk',seed,fold,m['coverage'],m['pass_risk'],flush=True)
    dump('risk_splits.json',bindings);dump('risk_results.json',results);pd.DataFrame(pred).to_csv(OUT/'results/risk_predictions.csv',index=False)
    frame=pd.DataFrame(pred);per=frame.groupby('fault').route.value_counts().unstack(fill_value=0)
    dump('risk_summary.json',{'evaluations':len(results),'passes':sum(r['pass_risk'] for r in results),'coverage_range':[min(r['coverage'] for r in results),max(r['coverage'] for r in results)],'coverage_mean':np.mean([r['coverage'] for r in results]),'FB_upper_range':[min(r['FB_upper'] for r in results),max(r['FB_upper'] for r in results)],'per_fault_repeated_counts':per.to_dict('index'),'warning':'Overlapping repeated evaluations; counts are not independent events; no binomial CI for pass fraction'})
    s=scores['dynamic_hist_w20'];ids=np.isin(f,[0,9]);dump('fault9_diagnostic.json',{'fault9_vs_normal_AUROC':roc_auc_score(y[ids],s[ids]),'score_quantiles':{str(k):np.quantile(s[f==k],[0,.1,.25,.5,.75,.9,1]).tolist() for k in [0,9,15]},'scope':'descriptive all existing Testing runs; no new tuning or independent confirmation'})

if __name__=='__main__':
    from paths import ensure_layout
    ensure_layout()
    risk()
