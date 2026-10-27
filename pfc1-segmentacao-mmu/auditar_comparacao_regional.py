"""Audita prototipos, escores e decisoes com cache; ou artefatos compactos recuperados."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from comparador_regional import regions,unit,compare
ROOT=Path(__file__).resolve().parent
NAME='comparacao_regional_treino_2026-10-23'
def file_hash(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def operating_threshold(impostor,target=.01):
    values=np.sort(np.asarray(impostor,dtype=np.float64));candidates=np.unique(np.r_[values,np.nextafter(values,np.inf)])
    rates=(len(values)-np.searchsorted(values,candidates,side='left'))/len(values)
    return float(candidates[np.flatnonzero(rates<=target)[0]])

def metrics(scores,labels,threshold,valid):
    scores=np.asarray(scores,dtype=np.float64);n=len(labels);genuine=scores[np.arange(n),labels]
    mask=np.ones_like(scores,dtype=bool);mask[np.arange(n),labels]=False
    effective=scores.copy();effective[~valid]=-2.;g=effective[np.arange(n),labels];imp=effective[mask]
    ts=np.unique(np.r_[g,imp,np.nextafter(np.max(effective),np.inf)])
    fmr=(len(imp)-np.searchsorted(np.sort(imp),ts,side='left'))/len(imp);fnmr=np.searchsorted(np.sort(g),ts,side='left')/len(g);pos=np.argmin(np.abs(fmr-fnmr))
    correct=(scores.argmax(1)==labels)&valid;accepted=(genuine>=threshold)&valid;impostor_accept=((scores>=threshold)&valid[:,None])[mask]
    wrong=scores.copy();wrong[np.arange(n),labels]=-np.inf
    return dict(rank1=float(correct.mean()),tar=float(accepted.mean()),fnmr=float(1-accepted.mean()),far=float(impostor_accept.mean()),eer_descriptive=float((fmr[pos]+fnmr[pos])/2),extraction_failures=int((~valid).sum()),queries=n,genuine_mean_valid=float(genuine[valid].mean()) if valid.any() else None,margin_mean_valid=float((genuine-wrong.max(1))[valid].mean()) if valid.any() else None),correct,accepted

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache-root',type=Path);a=p.parse_args();folder=a.root/NAME;done=json.loads((folder/'CONCLUIDO.json').read_text());protocol=json.loads((folder/'protocolo.json').read_text());record=json.loads((folder/'consultas_cadastro.json').read_text())
    for name,h in done['files_sha256'].items():assert file_hash(folder/name)==h
    assert file_hash(folder/'source.py')==protocol['script_sha256'] and file_hash(folder/'comparator_source.py')==protocol['comparator_sha256']==file_hash(ROOT/'comparador_regional.py')
    original=(folder/'source.py').read_text();current=(ROOT/'piloto_comparacao_regional.py').read_text();assert current==original.replace("print(json.dumps(dict(gate_passed=bool(gate)),flush=True))","print(json.dumps(dict(gate_passed=bool(gate))),flush=True)")
    assert len(record['queries'])==480 and all(r['subject'] in protocol['monitor_people'] and r['session']==2 for r in record['queries']);assert not set(protocol['fit_people'])&set(protocol['monitor_people'])
    arrays={}
    for method in ['regional24','mean32']:
        arrays[method]={};threshold=done['results'][method]['clean']['threshold']
        for tag in ['clean','upper10','lower10']:
            with np.load(folder/f'scores_{method}_{tag}.npz') as z:data={k:z[k] for k in z.files}
            arrays[method][tag]=data;scores=data['scores'];labels=data['labels'];valid=data['valid'];assert scores.shape==(480,16)
            if tag=='clean':
                imp=np.ones_like(scores,bool);imp[np.arange(480),labels]=False
                assert operating_threshold(scores[imp&valid[:,None]&(scores>-2)])==threshold
            m,c,g=metrics(scores,labels,threshold,valid);m.update(threshold=threshold,correct=int(c.sum()),accepted=int(g.sum()));assert m==done['results'][method][tag];np.testing.assert_array_equal(c,data['correct']);np.testing.assert_array_equal(g,data['accepted'])
    if a.cache_root:
        source=a.cache_root/'encoder_polar_espacial_2026-10-23';assert file_hash(source/'cache_layer3.npy')==protocol['cache_sha256'] and file_hash(source/'cache_indices.npz')==protocol['indices_sha256'] and file_hash(source/'rows.json')==protocol['rows_sha256']
        maps=np.load(source/'cache_layer3.npy',mmap_mode='r');rows=json.loads((source/'rows.json').read_text())
        with np.load(source/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
        with np.load(folder/'normalizacao_ajuste.npz') as z:mean=z['mean'];std=z['std'];si=z['fit_s1_indices']
        expected=np.array([i for i,r in enumerate(rows) if r['subject'] in protocol['fit_people'] and r['session']==1 and valid[i,0]]);np.testing.assert_array_equal(si,expected)
        sums=np.zeros(256,np.float64);squares=sums.copy();count=0
        for start in range(0,len(si),64):
            x=np.array(maps[mapping[si[start:start+64],0]],dtype=np.float64);sums+=x.sum((0,2,3));squares+=(x*x).sum((0,2,3));count+=len(x)*128
        np.testing.assert_array_equal(mean,(sums/count).astype(np.float32));np.testing.assert_array_equal(std,np.sqrt(np.maximum(squares/count-(sums/count)**2,1e-10)).astype(np.float32))
        prototypes=[]
        for eye,gi in zip(record['eyes'],record['gallery_indices']):
            expected=[i for i,r in enumerate(rows) if r['subject'] in protocol['monitor_people'] and [r['subject'],r['side']]==eye and r['session']==1 and valid[i,0]];assert expected==gi
            prototypes.append(unit(regions(maps[mapping[gi,0]],mean,std).mean(0)) if gi else np.zeros((32,256),np.float32))
        with np.load(folder/'prototipos.npz') as z:gallery=z['gallery'];gv=z['valid'];np.testing.assert_array_equal(gallery,np.stack(prototypes))
        qi=np.array(record['query_indices']);assert [rows[i] for i in qi]==record['queries'];selection=np.array([[j for j,eye in enumerate(record['eyes']) if eye[1]==rows[i]['side']] for i in qi]);expected_labels=np.array([[eye for eye in record['eyes'] if eye[1]==rows[i]['side']].index([rows[i]['subject'],rows[i]['side']]) for i in qi])
        for tag,j in [('clean',0),('upper10',1),('lower10',2)]:
            q=regions(maps[mapping[qi,j]],mean,std)
            for method,keep in [('regional24',24),('mean32',32)]:
                full=np.concatenate([compare(q[start:start+32],gallery,keep) for start in range(0,len(q),32)]);full[:,~gv]=-2.;scores=np.take_along_axis(full,selection,axis=1)
                np.testing.assert_array_equal(scores,arrays[method][tag]['scores']);np.testing.assert_array_equal(expected_labels,arrays[method][tag]['labels']);np.testing.assert_array_equal(valid[qi,j]&(scores>-2).any(1),arrays[method][tag]['valid'])
    b=done['original_polar_baseline'];r=done['results']['regional24'];gate=all(r['clean'][k]>=b['clean'][k] for k in ['rank1','tar']) and r['clean']['far']<=.01 and all(r[t][k]>b[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t in ['upper10','lower10']);assert bool(gate)==done['gate_passed'] and not any(done[k] for k in ['new_cnn_training','validation_inference','test_inference','candidate_replaced'])
    audit=dict(status='regional_scores_and_gate_audited',metrics_exact=True,clean_thresholds_exact=True,source_hashes_verified=True,full_cache_reproduction=bool(a.cache_root),gate_passed=bool(gate),registered_source_preserved=True,post_completion_print_only_fix=True)
    (folder/'AUDITORIA_REPRODUCAO.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');print(json.dumps(audit))
if __name__=='__main__':main()
