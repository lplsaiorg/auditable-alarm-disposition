"""Verify the accompanying saved-result package; Python standard library only."""
from pathlib import Path
import csv,json,hashlib,math
from collections import defaultdict
ROOT=Path(__file__).resolve().parent
def load(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
def rows(name):return list(csv.DictReader((ROOT/name).open(encoding='utf8',newline='')))
def upper(k,n):
    if k==n:return 1.0
    lo,hi=0.,1.
    for _ in range(70):
        p=(lo+hi)/2
        cdf=sum(math.exp(math.lgamma(n+1)-math.lgamma(j+1)-math.lgamma(n-j+1)+j*math.log(p)+(n-j)*math.log1p(-p)) for j in range(k+1))
        if cdf>.025:lo=p
        else:hi=p
    return (lo+hi)/2

def verify_base():
    manifest=load('manifest_20261106_v02.json')
    for name,h in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    alltep=rows('calibration_predictions.csv');groups=defaultdict(list)
    for r in alltep:groups[(int(r['seed']),int(r['fold']),r['strategy'])].append(r)
    final=[]
    for r in load('calibration_followup.json'):
        rr=groups[(r['seed'],r['fold'],r['strategy'])]
        fb=sum(int(x['fault'])>0 and x['route']=='0' for x in rr)
        nf=sum(x['fault']=='0' and x['route']=='1' for x in rr)
        auto=sum(x['route']!='-1' for x in rr)
        assert (fb,nf,auto)==(r['FB'],r['NF'],r['automatic'])
        assert abs(upper(fb,400)-r['FB_upper'])<1e-9
        assert abs(upper(nf,100)-r['NF_upper'])<1e-9
        if r['strategy']=='guarded_margin_cal400':final.append(r)
    metadata={int(x['index']):x for x in rows('tep_index_metadata_20261106_v01.csv')}
    for r in load('calibration_bindings.json'):
        assert not set(r['calibration_indices']) & set(r['evaluation_indices'])
        assert not {metadata[i]['run'] for i in r['calibration_indices']} & {metadata[i]['run'] for i in r['evaluation_indices']}
        expected={(int(metadata[i]['fault']),int(metadata[i]['run'])) for i in r['evaluation_indices']}
        actual={(int(x['fault']),int(x['run'])) for x in groups[(r['seed'],r['fold'],r['strategy'])]}
        assert expected==actual
    hp=rows('hai_predictions_20261106_v01.csv');hc=load('hai_comparison_20261106_v01.json')
    for r in hc['records']:
        rr=[x for x in hp if x['model']==r['model'] and (x['source']==r['source'] if r['source']!='heldout' else x['source'] in ['test4','test5'])]
        assert len(rr)==r['n']
        assert sum(x['truth']=='1' and x['route']=='0' for x in rr)==r['FB']
        assert sum(x['truth']=='0' and x['route']=='1' for x in rr)==r['NF']
        assert sum(x['route']=='-1' for x in rr)==r['abstain']
    detected=defaultdict(int)
    for e in hc['episodes']:
        hit=any(x['route']=='1' and x['source']==e['source'] and x['model']==e['model'] and int(x['start'])<e['end'] and int(x['end'])>e['start'] for x in hp)
        assert hit==e['detected']
        detected[e['model']]+=hit
    reader=[r for r in rows('fair_per_response.csv') if int(r['repeat'])==0]
    nr=defaultdict(set)
    for r in reader:nr[r['query_id']].add(r['numeric_route'])
    assert len(nr)==40 and all(len(v)==1 for v in nr.values())
    for e in load('paired_effects_20261106_v01.json'):
        if e['include_unavailable'] or e['mode'] not in ['ordinary','separated']:continue
        a={x['query_id']:x for x in reader if x['mode']==e['mode'] and x['condition']=='clean' and x['valid'].lower()=='true'}
        b={x['query_id']:x for x in reader if x['mode']==e['mode'] and x['condition']==e['condition'] and x['valid'].lower()=='true'}
        keys=[k for k in a.keys()&b.keys() if (int(a[k]['fault'])>0)==(e['direction']=='FB')]
        label='0' if e['direction']=='FB' else '1'
        delta=sum((float(b[k]['reader'])==int(label))-(float(a[k]['reader'])==int(label)) for k in keys)/len(keys)
        assert len(keys)==e['n'] and abs(delta-e['estimate'])<1e-10
    print(json.dumps({'files_verified':len(manifest),'TEP_evaluations':len(final),'TEP_passes':sum(x['pass_risk'] for x in final),'TEP_mean_coverage':sum(x['coverage'] for x in final)/len(final),'HAI_episode_hits':dict(detected),'history_invariant_queries':len(nr)},indent=2))


def verify_extra():
    summaries={}
    expected_keys={(r['seed'],r['fold'],r['fault'],r['run']) for r in rows('calibration_predictions.csv') if r['strategy']=='guarded_margin_cal400'}
    for filename,resultname in [('tep_predictions.csv','tep_results.json'),('length_predictions_20261106_v01.csv','length_results_20261106_v01.json')]:
        grouped=defaultdict(list)
        for r in rows(filename):grouped[(int(r['seed']),int(r['fold']),r['strategy'])].append(r)
        for r in load(resultname):
            rr=grouped[(r['seed'],r['fold'],r['strategy'])]
            fb=sum(int(x['fault'])>0 and x['route']=='0' for x in rr)
            nf=sum(x['fault']=='0' and x['route']=='1' for x in rr)
            auto=sum(x['route']!='-1' for x in rr)
            assert (fb,nf,auto)==(r['FB'],r['NF'],r['automatic'])
            assert abs(upper(fb,400)-r['FB_upper'])<1e-9 and abs(upper(nf,100)-r['NF_upper'])<1e-9
            assert abs(auto/500-r['coverage'])<1e-12
        for strategy in {k[2] for k in grouped}:
            assert {(x['seed'],x['fold'],x['fault'],x['run']) for k,g in grouped.items() if k[2]==strategy for x in g}==expected_keys
    for m in rows('table_s4_mapping_20261106_v01.csv'):
        rr=[r for r in load(m['results']) if r['strategy']==m['strategy']]
        assert len(rr)==15
        actual=[sum(r['pass_risk'] for r in rr),sum(r['coverage'] for r in rr)/15*100,max(r['FB_upper'] for r in rr)*100,max(r['NF_upper'] for r in rr)*100]
        expected=[float(m[k]) for k in ['passes','coverage_pct','max_FB_upper_pct','max_NF_upper_pct']]
        assert all(abs(a-e)<.0051 for a,e in zip(actual,expected)),m['strategy']
        summaries[m['strategy']]=actual
    metadata={int(r['index']):r for r in rows('tep_index_metadata_20261106_v01.csv')}
    queries=rows('history_query_manifest_20261106_v01.csv');overlap=load('history_query_overlap_20261106_v01.json')
    bindings=[b for b in load('calibration_bindings.json') if b['strategy']=='guarded_margin_cal400']
    reader={(r['query_id'],r['fault'],r['run']) for r in rows('fair_per_response.csv')}
    assert len(queries)==40 and {(q['query_id'],q['fault'],q['run']) for q in queries}==reader
    for q in queries:
        i=int(q['index']);assert (q['fault'],q['run'])==(metadata[i]['fault'],metadata[i]['run']) and q['split']=='Testing'
        for role in ['evaluation','calibration']:
            assert int(q[role+'_event_occurrences'])==sum(i in b[role+'_indices'] for b in bindings)
            assert int(q[role+'_run_occurrences'])==sum(q['run'] in {metadata[j]['run'] for j in b[role+'_indices']} for b in bindings)
    for record in overlap['per_fold']:
        b=next(b for b in bindings if b['seed']==record['seed'] and b['fold']==record['fold'])
        for role in ['evaluation','calibration']:
            assert record[role+'_query_events']==sum(int(q['index']) in b[role+'_indices'] for q in queries)
            assert record[role+'_query_runs']==len({q['run'] for q in queries}&{metadata[j]['run'] for j in b[role+'_indices']})
    scores={int(r['index']):r for r in rows('length_scores_20261106_v01.csv')}
    lp=rows('length_predictions_20261106_v01.csv')
    for r in load('length_results_20261106_v01.json'):
        b=next(b for b in bindings if b['seed']==r['seed'] and b['fold']==r['fold'])
        def route(x):return 0 if float(x['score'])<=r['policy']['lo'] else 1 if float(x['score'])>=r['policy']['hi'] else -1
        for x in lp:
            if int(x['seed'])==r['seed'] and int(x['fold'])==r['fold']:
                assert int(x['route'])==route(scores[int(x['index'])])
        cal=[scores[i] for i in b['calibration_indices']]
        fb=sum(int(x['fault'])>0 and route(x)==0 for x in cal);nf=sum(x['fault']=='0' and route(x)==1 for x in cal)
        assert (fb,nf)==(r['calibration']['FB'],r['calibration']['NF'])
        assert upper(fb,1600)<=.02 and upper(nf,400)<=.025
    length=load('length_results_20261106_v01.json');ls=load('length_summary_20261106_v01.json')
    assert sum(x['pass_risk'] for x in length)==ls['passes']
    assert abs(sum(x['coverage'] for x in length)/15-ls['mean_coverage'])<1e-12
    print(json.dumps({'Table_S4_verified_rows':len(summaries),'length_control_passes':ls['passes'],'length_control_coverage':ls['mean_coverage'],'query_evaluation_overlap':sum(int(q['evaluation_event_occurrences'])>0 for q in queries),'query_calibration_overlap':sum(int(q['calibration_event_occurrences'])>0 for q in queries)},indent=2))
if __name__=='__main__':
    verify_base()
    verify_extra()
