"""Encadeia treino SAM3, controles de identidade e referencias humanas do piloto."""
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import numpy as np
from avaliar_prontidao_anomalias import report,identity_gate
from analisar_rodada_segmentacao_area import measure,validation_queries
from avaliar_clinica_sam3_adaptado import selected_checkpoint

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
OUT=ROOT/'outputs/prontidao_anomalias_2026-11-03'
LOSSES=(0,1,2,5,10,20,30,40,50,60,70,80,90)
FILES=('acompanhar_prontidao_anomalias.py','avaliar_identidade_sam3_adaptado.py',
       'avaliar_clinica_sam3_adaptado.py','avaliar_prontidao_anomalias.py','criterios_prontidao_anomalias.json',
       'segmentador_sam3_iris.py','avaliar_candidato_congelado.py','analisar_rodada_segmentacao_area.py')


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.json.part');temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(path)


def command(script,args,log):
    subprocess.run([sys.executable,'-u',str(ROOT/script),*map(str,args)],cwd=ROOT,stdout=log,stderr=log,check=True)


def identity_assessment(checkpoint,log):
    destination=BASE/'identidade';destination.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text())
    queries,people,expected=validation_queries(manifest)
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text())
    threshold=frozen['frozen_threshold'];cp_sha=digest(checkpoint)
    criteria=json.loads((ROOT/'criterios_prontidao_anomalias.json').read_text())['identification_study']
    def evaluate(custom,condition,level):
        key=('novo' if custom else 'original')+'_'+condition+'_'+str(level)
        record_file=destination/(key+'.json')
        if record_file.exists():
            value=json.loads(record_file.read_text());
            if value['checkpoint_sha256']!=(cp_sha if custom else None):raise ValueError('Candidato diferente em resultados existentes')
            return value
        # Raizes curtas e cache exclusivo por tentativa evitam MAX_PATH e reuso parcial.
        parent=Path(os.environ['TEMP'])/'pfc-s3id'/key;parent.mkdir(parents=True,exist_ok=True)
        attempts=sorted(parent.glob('a*/r/confirmacao*/CONCLUIDO.json'))
        if attempts:folder=attempts[-1].parent
        else:
            number=1
            while (parent/f'a{number:03}').exists():number+=1
            result_root=parent/f'a{number:03}'/'r'
            args=['--output-root',result_root,'--split','val','--condition',condition,'--level',level]
            if custom:args+=['--segmenter',checkpoint]
            write(OUT/'execucao.json',{'stage':'identity','condition':key,'pid':os.getpid()})
            command('avaliar_identidade_sam3_adaptado.py',args,log)
            folder=next(result_root.glob('confirmacao*/CONCLUIDO.json')).parent
        adapter_info=json.loads((folder.parent/'ADAPTADOR_SAM3.json').read_text())
        if adapter_info['candidate_sha256']!=(cp_sha if custom else None):raise ValueError('Cache de outro candidato')
        if any(digest(ROOT/n)!=h for n,h in adapter_info['sources'].items()):raise ValueError('Cache de outro codigo')
        if any(importlib.metadata.version(n)!=v for n,v in adapter_info['versions'].items()):raise ValueError('Cache de outro ambiente')
        with np.load(folder/'scores_finais.npz',allow_pickle=False) as saved:
            np.testing.assert_array_equal(expected,saved['labels'])
            counts,rates,_,vectors=measure(saved['scores'],saved['labels'],saved['valid'],threshold)
            np.testing.assert_array_equal(vectors['rank1'],saved['correct']);np.testing.assert_array_equal(vectors['tar'],saved['accepted'])
        record={'checkpoint_sha256':cp_sha if custom else None,'counts':counts,'rates':rates,
                'passed_new_readiness_criterion':identity_gate(counts,criteria),'folder':str(folder),
                'condition':condition,'loss_percent':level,'model':'sam3_adapter' if custom else 'original_unet',
                'threshold':threshold,'queries':len(queries),'people':len(people),'test_inference':False}
        evidence=destination/'evidencias'/key;evidence.mkdir(parents=True,exist_ok=True)
        for file in folder.iterdir():
            if file.is_file() and file.suffix in ('.json','.npz','.py'):
                target=evidence/file.name
                if target.exists() and digest(target)!=digest(file):raise ValueError('Evidencia divergente')
                if not target.exists():target.write_bytes(file.read_bytes())
        adapter=folder.parent/'ADAPTADOR_SAM3.json'
        if not adapter.exists():raise ValueError('Proveniencia do adaptador ausente')
        target=evidence/'ADAPTADOR_SAM3.json'
        if target.exists() and digest(target)!=digest(adapter):raise ValueError('Proveniencia alterada')
        if not target.exists():target.write_bytes(adapter.read_bytes())
        write(record_file,record);return record
    controls={}
    for custom in (False,True):
        for condition,level in (('original',0),('oclusao_superior',10),('oclusao_inferior',10)):
            controls[(custom,condition,level)]=evaluate(custom,condition,level)
    frontier={}
    if controls[(True,'original',0)]['passed_new_readiness_criterion']:
        for condition in ('oclusao_superior','oclusao_inferior'):
            decisions=[True]
            for level in LOSSES[1:]:
                r=controls[(True,condition,10)] if level==10 else evaluate(True,condition,level)
                decisions.append(r['passed_new_readiness_criterion'])
            minimum=None
            for loss,passed in zip(LOSSES,decisions):
                if not passed:break
                minimum=100-loss
            frontier[condition]={'nominal_visible_area_on_registered_prefix':minimum,'passed':decisions}
    write(destination/'CONCLUIDO.json',{'checkpoint_sha256':cp_sha,'frontier':frontier,
          'minimum_assigned':bool(frontier),'area_is_annotated_visible_support_not_anatomical':True,
          'validation_reused_not_blind':True,'clinical_effect_established':False})


def main():
    OUT.mkdir(exist_ok=True);protocol=OUT/'protocolo_fluxo.json'
    sources={n:digest(ROOT/n) for n in FILES}
    versions={n:importlib.metadata.version(n) for n in ('torch','torchvision','numpy','pillow','sam3')}
    if protocol.exists():
        registered=json.loads(protocol.read_text())
        if registered['sources']!=sources or registered['versions']!=versions:raise ValueError('Fontes/ambiente do fluxo mudaram apos registro')
    else:write(protocol,{'registered_utc':datetime.now(timezone.utc).isoformat(),'sources':sources,
                        'versions':versions,
                        'identity_gate_includes_joint_success':True,'area_loss_grid':LOSSES,
                        'clinical_references_not_used_for_checkpoint_selection':True,'no_test_inference':True})
    with (OUT/'execucao.log').open('a',encoding='utf-8',buffering=1) as log:
        try:
            deadline=time.monotonic()+23*3600
            while time.monotonic()<deadline:
                state=report()
                if (BASE/'CONCLUIDO.json').exists():
                    checkpoint=selected_checkpoint()
                    if not (BASE/'clinica/normal/CONCLUIDO.json').exists():command('avaliar_clinica_sam3_adaptado.py',[],log)
                    if not (BASE/'identidade/CONCLUIDO.json').exists():identity_assessment(checkpoint,log)
                    state=report()
                    if state['segmentation_pilot_ready'] and not (BASE/'clinica/iris_anomaly/CONCLUIDO.json').exists():
                        command('avaliar_clinica_sam3_adaptado.py',['--group','iris_anomaly'],log)
                    if state['segmentation_pilot_ready']:
                        write(OUT/'execucao.json',{'stage':'pilot_ready','pid':os.getpid()});return
                write(OUT/'execucao.json',{'stage':'waiting_training_or_human_references','pid':os.getpid()})
                time.sleep(30)
        except BaseException as error:
            traceback.print_exc(file=log);write(OUT/'execucao.json',{'stage':'failed','error':repr(error),'pid':os.getpid()});raise


if __name__=='__main__':main()
