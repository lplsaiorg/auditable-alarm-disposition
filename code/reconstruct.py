"""Current manuscript experiment source; see docs/REPRODUCTION.md for scope and portability changes."""
import numpy as np

def features(frame,cols,scaler,cut):
    x=frame.loc[frame['sample']>cut]
    grouped=x.groupby(['faultNumber','simulationRun'],sort=True)[cols].mean()
    z=scaler.transform(grouped)
    a=np.abs(z)
    extra=np.column_stack([z.mean(1),z.std(1),z.min(1),z.max(1),np.median(z,axis=1),np.quantile(z,.25,axis=1),np.quantile(z,.75,axis=1),a.mean(1),a.std(1),a.max(1),np.median(a,axis=1),np.mean(a>1,axis=1),np.mean(a>2,axis=1),np.mean(a>3,axis=1)])
    return grouped.index.to_frame(index=False),np.column_stack([z,a,extra])
