"""Piloto registrado no TREINO; comparacao regional sem novo treino de CNN."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
from comparador_regional import regions,unit,compare
from preparar_encoder_espacial import file_hash
from avaliar_robustez_reconhecimento import metrics,operating_threshold
ROOT=Path(__file__).resolve().parent
NAME='comparacao_regional_treino_2026-10-23'

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'encoder_polar_espacial_2026-10-23';old=json.loads((source/'protocolo.json').read_text());cache=json.loads((source/'CACHE_CONCLUIDO.json').read_text())
    if a.registrar:
        out.mkdir(exist_ok=False)
        protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='TRAIN only:167fit people for clean S1 channel standardization;16reusedmonitor people,480queries,16same-sidecandidateeyes. No VAL/test or newCNNtraining. Encoders previously saw monitor; exploratory reused monitor.',
            primary='Frozen original layer3 256x4x32 -> standardize each channel using FITcleanS1 ONLY -> pool4angularcolumns ->32regions4x8 -> L2perregion. Match corresponding regions,discard8lowest localcosines for EACHquery/gallerypair,mean24. Fixed keep24,NOshift/search/GTsectorselection. Broad CNN receptive fields mean regions are NOT isolated iris pixels.',
            control='Same representation/prototype/localcosines;meanALL32regions,keep32. Primary never chosen posthoc from control.',
            gallery='Mean regional unit descriptors over all valid MONITOR S1 photos per eye,renormalizedperregion;gallery always CLEAN. Same-side16eyes;one observed S2query only. No paired clean query used in scoring. No fitting on monitor other than CLEAN threshold per method.',
            calibration='Single CLEAN monitor threshold at empirical FMR<=1%,unchanged for BOTH10%occlusions. Failures retained. No threshold sweep on occluded monitor, no fitting/parameter search after results.',
            gate='Primary cleanRank1/TAR >= original polar baseline and FMR<=1%;BOTHocclusions strictRank1/TAR gains vs original polar and FMR<=1%. Gate is feasibility only;NOautomaticVAL/test/promotion/minimum. Report keep32 control regardless of primary outcome.',
            fit_people=old['fit_people'],monitor_people=old['monitor_people'],cache_sha256=cache['sha256'],indices_sha256=cache['indices_sha256'],rows_sha256=file_hash(source/'rows.json'),source_protocol_sha256=file_hash(source/'protocolo.json'),manifest_sha256=file_hash(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'),script_sha256=file_hash(Path(__file__)),comparator_sha256=file_hash(ROOT/'comparador_regional.py'))
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'comparator_source.py').write_bytes((ROOT/'comparador_regional.py').read_bytes());print('Protocolo regional registrado antes dos escores.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists()
    for path,key in [(Path(__file__),'script_sha256'),(ROOT/'comparador_regional.py','comparator_sha256'),(source/'cache_layer3.npy','cache_sha256'),(source/'cache_indices.npz','indices_sha256'),(source/'rows.json','rows_sha256'),(source/'protocolo.json','source_protocol_sha256'),(ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json','manifest_sha256')]:assert file_hash(path)==protocol[key]
    rows=json.loads((source/'rows.json').read_text());fit=set(protocol['fit_people']);monitor=set(protocol['monitor_people']);assert not fit&monitor
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text());assert not (fit|monitor)&{r['subject'] for r in manifest['val']+manifest['test']}
    maps=np.load(source/'cache_layer3.npy',mmap_mode='r')
    with np.load(source/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
    si=np.array([i for i,r in enumerate(rows) if r['subject'] in fit and r['session']==1 and valid[i,0]])
    sums=np.zeros(256,np.float64);squares=sums.copy();count=0
    for start in range(0,len(si),64):
        x=np.array(maps[mapping[si[start:start+64],0]],dtype=np.float64);sums+=x.sum((0,2,3));squares+=(x*x).sum((0,2,3));count+=len(x)*128
    mean=(sums/count).astype(np.float32);std=np.sqrt(np.maximum(squares/count-(sums/count)**2,1e-10)).astype(np.float32)
    np.savez_compressed(out/'normalizacao_ajuste.npz',mean=mean,std=std,fit_s1_indices=si)
    mi=np.array([i for i,r in enumerate(rows) if r['subject'] in monitor]);qi=np.array([i for i in mi if rows[i]['session']==2]);eyes=sorted({(rows[i]['subject'],rows[i]['side']) for i in mi});assert len(qi)==480 and len(eyes)==32
    gallery=[];gallery_valid=[];gallery_indices=[]
    for eye in eyes:
        gi=np.array([i for i in mi if (rows[i]['subject'],rows[i]['side'])==eye and rows[i]['session']==1 and valid[i,0]],dtype=int);gallery_indices.append(gi.tolist());gallery_valid.append(bool(len(gi)))
        gallery.append(unit(regions(maps[mapping[gi,0]],mean,std).mean(0)) if len(gi) else np.zeros((32,256),np.float32))
    gallery=np.stack(gallery);np.savez_compressed(out/'prototipos.npz',gallery=gallery,valid=gallery_valid)
    labels=np.array([[eye for eye in eyes if eye[1]==rows[i]['side']].index((rows[i]['subject'],rows[i]['side'])) for i in qi]);selection=np.array([[j for j,eye in enumerate(eyes) if eye[1]==rows[i]['side']] for i in qi]);results={};thresholds={}
    baseline=json.loads((source/'CONCLUIDO.json').read_text())['baseline_monitor']
    for tag,j in [('clean',0),('upper10',1),('lower10',2)]:
        query=regions(maps[mapping[qi,j]],mean,std)
        for method,keep in [('regional24',24),('mean32',32)]:
            chunks=[]
            for start in range(0,len(qi),32):chunks.append(compare(query[start:start+32],gallery,keep))
            full=np.concatenate(chunks);full[:,~np.array(gallery_valid)]=-2.;scores=np.take_along_axis(full,selection,axis=1);available=valid[qi,j]&(scores>-2).any(1)
            if tag=='clean':
                imp=np.ones_like(scores,bool);imp[np.arange(len(qi)),labels]=False
                thresholds[method]=operating_threshold(scores[imp&available[:,None]&(scores>-2)])
            measured,correct,accepted=metrics(scores,labels,thresholds[method],available);measured.update(threshold=thresholds[method],correct=int(correct.sum()),accepted=int(accepted.sum()));results.setdefault(method,{})[tag]=measured
            np.savez_compressed(out/f'scores_{method}_{tag}.npz',scores=scores,labels=labels,valid=available,correct=correct,accepted=accepted)
            print(json.dumps(dict(method=method,condition=tag,metrics=measured)),flush=True)
    primary=results['regional24'];gate=all(primary['clean'][k]>=baseline['clean'][k] for k in ['rank1','tar']) and primary['clean']['far']<=.01 and all(primary[t][k]>baseline[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']) and all(primary[t]['far']<=.01 for t in ['upper10','lower10'])
    (out/'consultas_cadastro.json').write_text(json.dumps(dict(queries=[rows[i] for i in qi],query_indices=qi.tolist(),eyes=eyes,gallery_indices=gallery_indices),indent=2),encoding='utf-8')
    done=dict(status='regional_train_pilot_completed',results=results,original_polar_baseline=baseline,fit_s1_photos=len(si),queries=480,monitor_people=16,regions=32,retained_primary_regions=24,gate_passed=bool(gate),new_cnn_training=False,validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None,files_sha256={f.name:file_hash(f) for f in out.iterdir() if f.is_file()})
    (out/'CONCLUIDO.json').write_text(json.dumps(done,indent=2),encoding='utf-8');print(json.dumps(dict(gate_passed=bool(gate))),flush=True)
if __name__=='__main__':main()
