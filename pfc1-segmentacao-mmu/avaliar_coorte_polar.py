"""Experimento fixo: coorte FIT, limiar interno limpo, monitor somente ao final."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
import torch
from normalizacao_coorte_polar import cohort_stats,symmetric_scores
from treinar_bloco_fmr_separado import ROOT,CONDITIONS,score,calibrate,measured
from preparar_encoder_espacial import file_hash
from ajuste_bloco_polar import FullTail
from encoder_polar_espacial import tail_vectors
from comparador_hdbif_lote import aggregate
from avaliar_robustez_reconhecimento import identity
from validar_lateralidade_informada import subset
NAME='coorte_polar_separada_2026-10-23'

def normalized_match(vectors,valid,rows,cohort):
    gi=sorted([i for i,r in enumerate(rows) if r.session==1],key=lambda i:(identity(rows[i]),Path(rows[i].image).name));qi=[i for i,r in enumerate(rows) if r.session==2];ids=sorted({identity(r) for r in rows});groups=[[j for j,i in enumerate(gi) if identity(rows[i])==eye] for eye in ids];sides=np.array([0 if r.side=='L' else 1 for r in rows])
    stats=cohort_stats(vectors,valid,sides,cohort['vectors'],cohort['valid'],cohort['eye_sides'],cohort['groups']);raw=symmetric_scores(vectors[qi],vectors[gi],stats[qi],stats[gi]);bounded=.5+.5*np.tanh(raw/4);bounded[:,~valid[gi]]=-2.
    full=aggregate(bounded,groups,'top3');values,labels,_=subset(full,rows,ids);available=valid[qi]&(values>-2).any(1)
    return dict(scores=values,labels=labels,valid=available),stats

def main():
    from types import SimpleNamespace
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'bloco_fmr_separado_2026-10-23';sp=json.loads((source/'protocolo.json').read_text());sd=json.loads((source/'CONCLUIDO.json').read_text())
    if a.registrar:
        out.mkdir(exist_ok=False);protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Fixed post-training TRAIN experiment. No retraining/VAL/test. ModelselectedpreviouslywithoutOLDmonitor;normalizationhypothesisintroducedafterpriorresults,thusmonitorremainsreuseddevelopmentNOTindependent.',
            method='Cohort ONLY151FIT cleanvalidS1 eyes. For each observed photo,mean/std oftop3cosine-per-cohort-eye on SAMEside;std floor.05. For query/galleryphoto pair,z=.5*((cos-mean_query)/std_query+(cos-mean_gallery)/std_gallery). Boundpairscore=.5+.5tanh(z/4) toreserve-2failure sentinel; top3mean per enrolled eye. No clean query counterpart, labels/GT/occlusionlevel in normalization.',
            calibration='Single16INTERNALpeople CLEAN threshold,targetFMR0.5%,frozenforbothocclusionsand16OLDmonitor inclclean. No parametersweep,weightfitting,threshold adjustment on occlusions/OLDmonitor. Raw frozen candidate reported alongside.',
            gate='OLDmonitor cleanRank1/TAR>=rawcandidateclean,FMR<=1%;BOTHocclusionRank1/TAR>=rawcandidate,FMR<=1%. Absolute90%Rank1/TAR+FMR<=1 separate. No automaticVAL/test/promotion/minimum.',
            training_protocol_sha256=file_hash(source/'protocolo.json'),training_result_sha256=file_hash(source/'CONCLUIDO.json'),checkpoint_sha256=sd['checkpoint_sha256'],script_sha256=file_hash(Path(__file__)),normalizer_sha256=file_hash(ROOT/'normalizacao_coorte_polar.py'),dependencies_sha256={n:file_hash(ROOT/n) for n in ['treinar_bloco_fmr_separado.py','comparador_hdbif_lote.py','ajuste_bloco_polar.py','encoder_polar_espacial.py','validar_lateralidade_informada.py']})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Normalizacao por coorte registrada antes das comparacoes.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256'] and file_hash(ROOT/'normalizacao_coorte_polar.py')==protocol['normalizer_sha256'];assert file_hash(source/'protocolo.json')==protocol['training_protocol_sha256'] and file_hash(source/'CONCLUIDO.json')==protocol['training_result_sha256'] and file_hash(source/'melhor_modelo.pt')==protocol['checkpoint_sha256']
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    cache=a.root/'encoder_polar_espacial_2026-10-23';assert file_hash(cache/'cache_layer3.npy')==sp['cache_sha256'] and file_hash(cache/'cache_indices.npz')==sp['indices_sha256'];features=np.load(cache/'cache_layer3.npy',mmap_mode='r')
    with np.load(cache/'cache_indices.npz') as z:mapping=z['mapping'];valid=z['valid']
    rows=[SimpleNamespace(**r) for r in json.loads((source/'rows.json').read_text())];fit=set(sp['fit_people']);internal=set(sp['internal_people']);monitor=set(sp['monitor_people']);assert not fit&internal and not (fit|internal)&monitor
    with np.load(source/'indices_ajuste.npz') as z:gallery=z['gallery'];ci=z['internal'];mi=z['monitor']
    assert all(rows[i].subject in fit and rows[i].session==1 and valid[i,0] for i in gallery)
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu';encoder=IdentityEncoder();encoder_file=ROOT/sp['encoder_relative_path'];assert file_hash(encoder_file)==sp['encoder_sha256'];encoder.load_state_dict(torch.load(encoder_file,map_location='cpu',weights_only=True)['model']);tail=FullTail(encoder).to(device).eval();state=torch.load(source/'melhor_modelo.pt',map_location='cpu',weights_only=True);tail.load_adapters(state['adapters']);assert tail.frozen_digest()==sd['frozen_sha256']
    cv=tail_vectors(tail,features,mapping[gallery,0],device);eyes=sorted({(rows[i].subject,rows[i].side) for i in gallery});groups=[[j for j,i in enumerate(gallery) if (rows[i].subject,rows[i].side)==eye] for eye in eyes];cs=np.array([0 if s=='L' else 1 for _,s in eyes]);cohort=dict(vectors=cv,valid=valid[gallery,0],eye_sides=cs,groups=groups);np.savez_compressed(out/'coorte.npz',vectors=cv,valid=cohort['valid'],eye_sides=cs,gallery_indices=gallery)
    (out/'grupos_coorte.json').write_text(json.dumps(dict(groups=groups,eyes=eyes),indent=2),encoding='utf-8');results={};threshold=None
    for split,ii in [('internal',ci),('monitor',mi)]:
        rr=[rows[i] for i in ii];assert not {r.subject for r in rr}&fit
        for j,tag in enumerate(CONDITIONS):
            v=tail_vectors(tail,features,mapping[ii,j],device);data,stats=normalized_match(v,valid[ii,j],rr,cohort)
            # S1 cache maps and validity are explicitly CLEAN for all three conditions.
            assert all(mapping[i,j]==mapping[i,0] and valid[i,j]==valid[i,0] for i in ii if rows[i].session==1)
            if split=='internal' and tag=='clean':threshold=calibrate(data)
            m,d=measured(data,threshold);results.setdefault(split,{})[tag]=m;np.savez_compressed(out/f'scores_{split}_{tag}.npz',**d,cohort_stats=stats,photo_vectors=v,photo_valid=valid[ii,j],global_indices=ii);print(json.dumps(dict(split=split,condition=tag,metrics=m)),flush=True)
    raw=sd['results']['monitor'];r=results['monitor'];gate=all(r['clean'][k]>=raw['clean'][k] for k in ['rank1','tar']) and all(r[t]['far']<=.01 for t in CONDITIONS) and all(r[t][k]>=raw[t][k] for t in ['upper10','lower10'] for k in ['rank1','tar']);absolute=all(r[t]['rank1']>=.9 and r[t]['tar']>=.9 and r[t]['far']<=.01 for t in CONDITIONS)
    done=dict(status='fixed_cohort_normalization_completed',results=results,raw_control=sd['results'],threshold=threshold,monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute),cohort_people=151,internal_people=16,monitor_people=16,labels_used_for_normalization=False,new_training=False,validation_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None,files_sha256={f.name:file_hash(f) for f in out.iterdir() if f.is_file()})
    (out/'CONCLUIDO.json').write_text(json.dumps(done,indent=2),encoding='utf-8');print(json.dumps(dict(monitor_gate_passed=bool(gate),absolute_target_reached=bool(absolute))),flush=True)
if __name__=='__main__':main()
