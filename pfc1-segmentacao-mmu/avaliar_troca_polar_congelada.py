"""Troca isolada do polar; preserva todos os parametros do sistema de referencia."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
import torch
from avaliar_candidato_congelado import ROOT,fuse,global_scores
from avaliar_fusao_treino_separado import ORDER
from avaliar_robustez_reconhecimento import load_splits,identity
from validar_lateralidade_informada import subset
from treinar_bloco_fmr_separado import measured
from preparar_encoder_espacial import file_hash
from encoder_polar_espacial import prefix_model,prefix_features
from ajuste_bloco_polar import FullTail
NAME='troca_polar_parametros_originais_val_2026-10-24'
CONDITIONS=[('clean',''),('upper10','_oclusao_superior_10'),('lower10','_oclusao_inferior_10')]

def main():
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'bloco_fmr_separado_2026-10-23';sp=json.loads((source/'protocolo.json').read_text());sd=json.loads((source/'CONCLUIDO.json').read_text());fp=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json';frozen=json.loads(fp.read_text());manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';rows=load_splits(json.loads(manifest_file.read_text()))['val'];ids=sorted({identity(r) for r in rows})
    if a.registrar:
        out.mkdir(exist_ok=False);protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='Exploratory VAL counterfactual AFTER newcalibration pipeline failed. Candidateweights selectedonTRAIN only. Restore EXACTpriorstablefusionparameters,replaceONLYglobalpolar. No newcalibration or thresholdadjustment. VALpreviouslyexamined;notblind.',
            method='Original8components and original fixed calibration/querynormalization/threshold unchanged. TRAIN151FIT adjustedpolar FP32 ONLY change. ORIGINALcontrol exactreplay from all9cachedcomponents. No backgroundnormalizer,robustthreshold,weightsearch or modelselection onVAL.',
            gate='Firstclean must reach90%Rank1/TAR,FMR<=1%;otherwise skipocclusions. Ifpasses,diagnoseexistingupper/lower10%withsamefrozenparameters. No automatictest/promotion/minimum;0/10only,all482queries,onephoto,suppliedside,16eyes.',
            source_checkpoint_sha256=sd['checkpoint_sha256'],source_protocol_sha256=file_hash(source/'protocolo.json'),source_result_sha256=file_hash(source/'CONCLUIDO.json'),frozen_parameters_sha256=file_hash(fp),threshold=frozen['frozen_threshold'],script_sha256=file_hash(Path(__file__)),manifest_sha256=file_hash(manifest_file),dependencies_sha256={n:file_hash(ROOT/n) for n in ['avaliar_candidato_congelado.py','ajuste_bloco_polar.py','encoder_polar_espacial.py','normalizar_consulta.py']})
        (out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());(out/'parametros_originais.json').write_bytes(fp.read_bytes());print('Troca isolada registrada; parametros originais preservados.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256'];assert file_hash(fp)==protocol['frozen_parameters_sha256'] and file_hash(source/'melhor_modelo.pt')==protocol['source_checkpoint_sha256'];assert file_hash(source/'protocolo.json')==protocol['source_protocol_sha256'] and file_hash(source/'CONCLUIDO.json')==protocol['source_result_sha256'] and file_hash(manifest_file)==protocol['manifest_sha256']
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    assert not {r.subject for r in rows}&set(sp['fit_people']+sp['internal_people']+sp['monitor_people']);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu';encoder=IdentityEncoder();ef=ROOT/sp['encoder_relative_path'];assert file_hash(ef)==sp['encoder_sha256'];encoder.load_state_dict(torch.load(ef,map_location='cpu',weights_only=True)['model']);prefix=prefix_model(encoder).to(device).eval();tail=FullTail(encoder).to(device).eval();state=torch.load(source/'melhor_modelo.pt',map_location='cpu',weights_only=True);tail.load_adapters(state['adapters']);assert tail.frozen_digest()==sd['frozen_sha256'];results={};hashes={};clean_passed=False
    for tag,suffix in CONDITIONS:
        if tag!='clean' and not clean_passed:break
        original=ROOT/'outputs'/f'confirmacao_congelada_val{suffix}_2026-10-21';cache=a.root.parent/f'cache_confirmacao_val{suffix}_2026-10-21';components=[]
        for n in ORDER:
            file=original/f'scores_{n}.npz';hashes[str(file)]=file_hash(file)
            with np.load(file) as z:c={k:z[k] for k in ['scores','labels','valid']}
            components.append(c);np.savez_compressed(out/f'component_original_{tag}_{n}.npz',**c)
        baseline,valid=fuse(components,frozen['component_calibration_red_and_clahe']);bm,bd=measured(dict(scores=baseline,labels=components[0]['labels'],valid=valid),protocol['threshold']);np.savez_compressed(out/f'scores_original_{tag}.npz',**bd)
        with np.load(original/'scores_finais.npz') as z:np.testing.assert_allclose(baseline,z['scores'],atol=1e-14,rtol=0);np.testing.assert_array_equal(bd['correct'],z['correct']);np.testing.assert_array_equal(bd['accepted'],z['accepted'])
        images=np.load(cache/'polar.npy',mmap_mode='r');hashes[str(cache/'polar.npy')]=file_hash(cache/'polar.npy')
        with np.load(cache/'valid.npz') as z:pv=z['polar']
        embeddings=[]
        for start in range(0,len(rows),32):
            f=prefix_features(prefix,images[start:start+32],device)
            with torch.inference_mode():embeddings.append(tail(torch.from_numpy(f).to(device)).cpu().numpy())
        full,qv=global_scores(np.concatenate(embeddings),pv,rows);s,l,_=subset(full,rows,ids);np.testing.assert_array_equal(l,components[0]['labels']);components[1]=dict(scores=s,labels=l,valid=qv);np.savez_compressed(out/f'polar_adapted_{tag}.npz',**components[1]);scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);m,d=measured(dict(scores=scores,labels=l,valid=valid),protocol['threshold']);np.savez_compressed(out/f'scores_adapted_{tag}.npz',**d);results[tag]=dict(original=bm,adapted=m)
        if tag=='clean':clean_passed=m['rank1']>=.9 and m['tar']>=.9 and m['far']<=.01
        print(json.dumps(dict(condition=tag,original=bm,adapted=m)),flush=True)
    done=dict(status='isolated_polar_swap_fixed_reference_evaluated',results=results,clean_gate_passed=bool(clean_passed),occlusion_inference='upper10'in results,test_inference=False,calibration_changed=False,threshold_changed=False,candidate_replaced=False,minimum_area=None,input_sha256=hashes)
    (out/'CONCLUIDO.json').write_text(json.dumps(done,indent=2),encoding='utf-8')
if __name__=='__main__':main()
