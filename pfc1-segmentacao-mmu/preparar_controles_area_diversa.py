"""Audita controles legados na validacao e prepara seu reuso na rodada ativa.

Reproduz fusao, rotulos, decisoes e contagens. Confere tres entradas fixas de
preprocessamento por condicao contra os caches originais. Nenhum teste e lido,
nenhum peso e selecionado por estas metricas e nenhuma fonte ativa e alterada.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import numpy as np
import torch

from avaliar_area_segmentador_diverso import digest,inspect_scores
from avaliar_candidato_congelado import WEIGHTS,fuse,prepare
from avaliar_robustez_reconhecimento import identity,load_splits,metrics

ROOT=Path(__file__).resolve().parent
ORDER=('rgb','polar','spatial','r50','convnext','native','transformer','arc_clahe','arc_red')
UNET_HASH='2bcfc269ffc9562ca8cf0956998faf1e22641587cd60f7059b3cec3dd0f4093d'
SPECS=(('original',0,''),('oclusao_superior',10,'_oclusao_superior_10'),('oclusao_inferior',10,'_oclusao_inferior_10'))


def audit_training_snapshot(mirror,initial):
    files=sorted((mirror/'treino').glob('retomada_epoca_*_lote_*.pt'))
    if not files:return {'status':'no_immutable_snapshot_yet'}
    file=files[-1];state=torch.load(file,map_location='cpu',weights_only=True)
    original=torch.load(initial,map_location='cpu',weights_only=True)['model']
    if state['model'].keys()!=original.keys():raise ValueError('Chaves do segmentador mudaram')
    changed=[];max_delta=0.
    for name,value in state['model'].items():
        if value.shape!=original[name].shape or not bool(torch.isfinite(value).all()):raise ValueError('Tensor invalido: '+name)
        delta=float((value.float()-original[name].float()).abs().max())
        if delta:changed.append(name)
        max_delta=max(max_delta,delta)
    steps=sorted({int(item['step']) for item in state['optimizer']['state'].values()})
    if steps!=[state['completed_batches']]:raise ValueError('Passos do AdamW nao correspondem ao primeiro ciclo esperado')
    return {'status':'passed','snapshot':str(file),'sha256':digest(file),'epoch':state['epoch'],
            'completed_batches':state['completed_batches'],'trained_samples':state['totals']['samples'],
            'optimizer_steps':steps,'changed_tensors':len(changed),'largest_absolute_tensor_delta':max_delta,
            'validation_after_training_available':False,'recognition_gain_measured':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-root',type=Path,required=True);p.add_argument('--mirror-root',type=Path,required=True)
    p.add_argument('--stage',action='store_true');a=p.parse_args()
    state=json.loads((a.run_root/'estado_rodada.json').read_text(encoding='utf-8'))
    if a.stage and state['stage']!='training':raise ValueError('Preparar reuso somente antes da fase de reconhecimento')
    torch.set_num_threads(2);torch.backends.cudnn.benchmark=False
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    frozen_file=ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    frozen=json.loads(frozen_file.read_text(encoding='utf-8-sig'));threshold=frozen['frozen_threshold']
    manifest_file=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8-sig'));rows=load_splits(manifest)['val']
    queries=[r for r in rows if r.session==2];subjects=np.array([r.subject for r in queries]);people=sorted(set(subjects.tolist()))
    expected_labels=np.array([people.index(r.subject) for r in queries]);ids=sorted({identity(r) for r in rows})
    selected=[0,next(i for i,r in enumerate(rows) if r.session==2),len(rows)-1]
    summaries=[];staged=[]
    for condition,level,suffix in SPECS:
        stem='confirmacao_congelada_val'+suffix+'_2026-10-21';source=ROOT/'outputs'/stem
        protocol=json.loads((source/'protocolo.json').read_text(encoding='utf-8-sig'))
        if protocol['split']!='val' or protocol.get('condition','original')!=condition or protocol.get('occluded_percent',0)!=level:
            raise ValueError('Condicao ou particao divergente')
        if protocol.get('fixed_geometry_diagnostic',False) or protocol.get('new_segmenter_validation_only',False):raise ValueError('Controle nao operacional')
        if protocol['unet_sha256']!=UNET_HASH or protocol['frozen_sha256']!=digest(frozen_file) or protocol['threshold']!=threshold:
            raise ValueError('Pesos/calibracao divergentes')
        if protocol['checkpoint_sha256']!={name:value[1] for name,value in WEIGHTS.items()}:raise ValueError('Reconhecedores divergentes')
        if digest(source/'source.py')!=protocol['script_sha256']:raise ValueError('Fonte historica nao corresponde ao protocolo')
        for name,expected in protocol.get('dependencies_sha256',{}).items():
            if digest(ROOT/name)!=expected:raise ValueError('Dependencia historica mudou: '+name)
        if protocol['queries']!=len(queries) or protocol['input_images']!=len(rows) or protocol['candidates']!=len(people):
            raise ValueError('Populacao ou galeria divergente')
        components=[]
        for name in ORDER:
            with np.load(source/f'scores_{name}.npz',allow_pickle=False) as z:
                current={k:z[k] for k in z.files}
            np.testing.assert_array_equal(current['labels'],expected_labels);components.append(current)
        fused,valid=fuse(components,frozen['component_calibration_red_and_clahe'])
        with np.load(source/'scores_finais.npz',allow_pickle=False) as z:
            np.testing.assert_array_equal(z['labels'],expected_labels);np.testing.assert_array_equal(z['valid'],valid)
            np.testing.assert_allclose(fused,z['scores'],rtol=0,atol=1e-12)
            measured,correct,accepted=metrics(fused,expected_labels,threshold,valid)
            np.testing.assert_array_equal(correct,z['correct']);np.testing.assert_array_equal(accepted,z['accepted'])
            max_difference=float(np.max(np.abs(fused-z['scores'])))
        completed=json.loads((source/'CONCLUIDO.json').read_text(encoding='utf-8-sig'))
        for key in ('rank1','tar','far','queries','extraction_failures'):
            if abs(measured[key]-completed['result'][key])>1e-12:raise ValueError('Metrica nao reproduzida: '+key)
        cache=Path(os.environ['TEMP'])/('cache_confirmacao_val'+suffix+'_2026-10-21')
        with tempfile.TemporaryDirectory(prefix='pfc-controle-inputs-') as directory:
            arrays,rv,pv=prepare([rows[i] for i in selected],device,Path(directory)/'inputs',condition,level)
            checks={name:bool(np.array_equal(np.asarray(array),np.load(cache/(name+'.npy'),mmap_mode='r',allow_pickle=False)[selected])) for name,array in arrays.items()}
            with np.load(cache/'valid.npz',allow_pickle=False) as z:
                checks['rgb_valid']=bool(np.array_equal(rv,z['rgb'][selected]));checks['polar_valid']=bool(np.array_equal(pv,z['polar'][selected]))
            # Memmaps precisam ser fechados antes da limpeza do TemporaryDirectory no Windows.
            for array in arrays.values():array._mmap.close()
            if not all(checks.values()):raise ValueError('Preprocessamento diferente no controle: '+str(checks))
        summary=inspect_scores(source,subjects,threshold)
        summary.update(condition=condition,loss_percent=level,source=str(source),reuse=True)
        summary['joint_identification_and_acceptance']=float((correct&accepted).mean())
        summary['fusion_maximum_absolute_difference']=max_difference
        summary['input_cache_checks']=checks;summary['input_checked_names']=[Path(rows[i].image).name for i in selected]
        summary['source_sha256']={str(file.relative_to(source)):digest(file) for file in source.iterdir() if file.is_file()}
        summaries.append(summary)
        if a.stage:
            target=a.run_root/'recognition'/('original_'+condition+'_'+str(level))/'attempt_001'/stem
            if target.exists():raise FileExistsError('Tentativa de reuso ja existe: '+str(target))
            staged.append((source,target,summary))
        print(json.dumps({'condition':condition,'counts':summary['counts'],'preprocessing_exact':all(checks.values()),'fusion_difference':max_difference}),flush=True)
    # Publicar apenas depois de todos os tres controles passarem pela auditoria.
    for source,target,summary in staged:
        target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_name(target.name+'.staging');temporary.mkdir()
        for file in source.iterdir():
            if file.is_file():shutil.copy2(file,temporary/file.name)
        if not (temporary/'interventions.json').exists():
            if summary['condition']!='original':raise FileNotFoundError('Intervencoes ausentes')
            (temporary/'interventions.json').write_text('[]',encoding='utf-8')
        (temporary/'REUSO_AUDITADO.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
        temporary.replace(target)
    initial=ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/melhor_modelo.pt'
    training=audit_training_snapshot(a.mirror_root,initial)
    report={'status':'passed','registered_utc':datetime.now(timezone.utc).isoformat(),'queries':len(queries),'people':len(people),
            'records_recomputed':len(queries)*len(SPECS),'conditions':summaries,'staged_for_reuse':a.stage,
            'manifest_sha256':digest(manifest_file),'frozen_sha256':digest(frozen_file),
            'script_sha256':digest(Path(__file__)),'current_training_snapshot_audit':training,
            'test_inference':False,'new_identity_evaluation':False,'recognition_gain_measured':False,
            'limitations':'Historical validation controls, not new inference or independent evidence. Cache agreement checked on3predefined photos per condition, not whole dataset recapture.'}
    out=a.mirror_root/'CONTROLES_AUDITADOS.json'
    if out.exists():raise FileExistsError('Preservar auditoria existente')
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(out,flush=True)


if __name__=='__main__':main()
