"""Porta limpa VAL de pipeline totalmente congelado no TREINO."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import numpy as np
import torch
from avaliar_fusao_treino_separado import ROOT,ORDER
from normalizacao_fundo_consulta import fuse_background
from treinar_bloco_fmr_separado import measured
from ajuste_bloco_polar import FullTail
from encoder_polar_espacial import prefix_model,prefix_features,tail_vectors
from preparar_encoder_espacial import file_hash
from avaliar_robustez_reconhecimento import load_splits,identity
from avaliar_candidato_congelado import global_scores
from validar_lateralidade_informada import subset
NAME='porta_limpa_multicondicao_val_2026-10-24'

def main():
    from treinar_identidade_iris import IdentityEncoder
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--registrar',action='store_true');a=p.parse_args();out=a.root/NAME;source=a.root/'bloco_fmr_separado_2026-10-23';cal=a.root/'calibracao_multicondicao_treino_2026-10-24';background=a.root/'fundo_consulta_treino_2026-10-23';sp=json.loads((source/'protocolo.json').read_text());sd=json.loads((source/'CONCLUIDO.json').read_text());cd=json.loads((cal/'CONCLUIDO.json').read_text());bd=json.loads((background/'CONCLUIDO.json').read_text());original=ROOT/'outputs/confirmacao_congelada_val_2026-10-21';cache=a.root.parent/'cache_confirmacao_val_2026-10-21'
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json';rows=load_splits(json.loads(manifest_file.read_text()))['val'];ids=sorted({identity(r) for r in rows});assert len(rows)==962 and sum(r.session==2 for r in rows)==482;assert not {r.subject for r in rows}&set(sp['fit_people']+sp['internal_people']+sp['monitor_people'])
    if a.registrar:
        out.mkdir(exist_ok=False);protocol=dict(registered_utc=datetime.now(timezone.utc).isoformat(),scope='CLEAN developmentVAL ONLY,482queries,16same-sideeyes,onequeryphoto. IdentitiesdisjointTRAINgradient/calibration/monitor,butVALhistoricallyusedindevelopment;NOTnewblindconfirmation. No occlusion/test inference and no fitting onVAL.',
            pipeline='8original cachedcomponents unchanged;151FIT fulltail adjusted polar FP32;fixed9componentweights;TRAINinternal componentmean/std;dropmaxbackground querynormalization;ONErobustglobalthreshold from120INTERNALqueriesclean+upper10+lower10. NO recalibration/selection/weights onVAL.',
            gate='CLEANRank1>=90%,TAR>=90%,empiricalFMR<=1%,all482queries/failuresretained. Fail=>NO5%occlusionorTEST;no threshold tweak onthese results. Passingisnecessarynot sufficientforfutureareaestimate.',
            threshold=cd['threshold'],calibration=bd['component_calibration'],checkpoint_sha256=sd['checkpoint_sha256'],training_protocol_sha256=file_hash(source/'protocolo.json'),training_result_sha256=file_hash(source/'CONCLUIDO.json'),calibration_result_sha256=file_hash(cal/'CONCLUIDO.json'),background_result_sha256=file_hash(background/'CONCLUIDO.json'),manifest_sha256=file_hash(manifest_file),cached_images_sha256=file_hash(cache/'polar.npy'),cached_valid_sha256=file_hash(cache/'valid.npz'),original_components_sha256={n:file_hash(original/f'scores_{n}.npz') for n in ORDER if n!='polar'},script_sha256=file_hash(Path(__file__)),dependencies_sha256={n:file_hash(ROOT/n) for n in ['normalizacao_fundo_consulta.py','ajuste_bloco_polar.py','encoder_polar_espacial.py','avaliar_candidato_congelado.py','avaliar_robustez_reconhecimento.py','validar_lateralidade_informada.py']})
        assert cd['five_percent_feasibility_eligible'];(out/'protocolo.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8');(out/'source.py').write_bytes(Path(__file__).read_bytes());print('Porta limpa VAL registrada com parametros TREINO congelados.');return
    protocol=json.loads((out/'protocolo.json').read_text());assert not (out/'CONCLUIDO.json').exists() and file_hash(Path(__file__))==protocol['script_sha256'];assert protocol['threshold']==cd['threshold'] and protocol['calibration']==bd['component_calibration'];assert file_hash(source/'melhor_modelo.pt')==protocol['checkpoint_sha256'] and file_hash(manifest_file)==protocol['manifest_sha256']
    for path,key in [(source/'protocolo.json','training_protocol_sha256'),(source/'CONCLUIDO.json','training_result_sha256'),(cal/'CONCLUIDO.json','calibration_result_sha256'),(background/'CONCLUIDO.json','background_result_sha256'),(cache/'polar.npy','cached_images_sha256'),(cache/'valid.npz','cached_valid_sha256')]:assert file_hash(path)==protocol[key]
    for n,h in protocol['dependencies_sha256'].items():assert file_hash(ROOT/n)==h
    for n,h in protocol['original_components_sha256'].items():assert file_hash(original/f'scores_{n}.npz')==h
    torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;device='cuda' if torch.cuda.is_available() else 'cpu';encoder=IdentityEncoder();encoder_file=ROOT/sp['encoder_relative_path'];assert file_hash(encoder_file)==sp['encoder_sha256'];encoder.load_state_dict(torch.load(encoder_file,map_location='cpu',weights_only=True)['model']);prefix=prefix_model(encoder).to(device).eval();tail=FullTail(encoder).to(device).eval();state=torch.load(source/'melhor_modelo.pt',map_location='cpu',weights_only=True);tail.load_adapters(state['adapters']);assert tail.frozen_digest()==sd['frozen_sha256']
    images=np.load(cache/'polar.npy',mmap_mode='r');assert len(images)==len(rows)
    with np.load(cache/'valid.npz') as z:valid=z['polar']
    parts=[]
    for start in range(0,len(rows),32):
        features=prefix_features(prefix,images[start:start+32],device)
        with torch.inference_mode():parts.append(tail(torch.from_numpy(features).to(device)).cpu().numpy())
    vectors=np.concatenate(parts);full,available=global_scores(vectors,valid,rows);scores,labels,_=subset(full,rows,ids);components=[];np.savez_compressed(out/'polar_adapted.npz',scores=scores,labels=labels,valid=available,vectors=vectors)
    for name in ORDER:
        if name=='polar':c=dict(scores=scores,labels=labels,valid=available)
        else:
            with np.load(original/f'scores_{name}.npz') as z:c={k:z[k] for k in ['scores','labels','valid']}
        np.testing.assert_array_equal(c['labels'],labels);components.append(c);np.savez_compressed(out/f'component_{name}.npz',**c)
    fused,usable=fuse_background(components,protocol['calibration']);data=dict(scores=fused,labels=labels,valid=usable);m,d=measured(data,protocol['threshold']);np.savez_compressed(out/'scores_finais.npz',**d);gate=m['rank1']>=.9 and m['tar']>=.9 and m['far']<=.01
    done=dict(status='frozen_train_pipeline_clean_validation_evaluated',result=m,clean_gate_passed=bool(gate),validation_fitting=False,calibration_changed=False,occlusion_inference=False,test_inference=False,candidate_replaced=False,minimum_area=None)
    (out/'CONCLUIDO.json').write_text(json.dumps(done,indent=2),encoding='utf-8');print(json.dumps(done),flush=True)
if __name__=='__main__':main()
