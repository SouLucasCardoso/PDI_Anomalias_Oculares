"""Criterios de engenharia para piloto; ausencia de evidencia nunca significa aprovacao."""
from datetime import datetime,timezone
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from PIL import Image
from revisar_mascaras_clinicas import sha,write_json

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
PACK=ROOT/'outputs/revisao_clinica_2026-11-03'
OUT=ROOT/'outputs/prontidao_anomalias_2026-11-03'


def fraction_pass(numerator,denominator,threshold,maximum=False):
    if denominator<=0:return False
    value=Fraction(str(threshold))
    left=numerator*value.denominator;right=denominator*value.numerator
    return left<=right if maximum else left>=right


def identity_gate(counts,criteria):
    if not counts:return False
    n=counts['queries'];imp=counts['impostors']
    return all((fraction_pass(counts['correct'],n,criteria['minimum_rank1']),
                fraction_pass(counts['accepted'],n,criteria['minimum_tar']),
                fraction_pass(counts['joint'],n,criteria['minimum_joint_correct_and_accepted']),
                fraction_pass(counts['false_accepts'],imp,criteria['maximum_fmr'],True)))


def clinical_normals(candidate_sha):
    tasks=[t for t in json.loads((PACK/'manifesto.json').read_text(encoding='utf-8'))['tasks'] if t['group']=='normal']
    records=[];reviewed=[];people=set()
    for task in tasks:
        latest=PACK/'revisoes'/task['id']/'latest.json'
        if not latest.exists():continue
        review=json.loads(latest.read_text(encoding='utf-8'))
        if review['status']!='reviewed_initial' or not review['reviewer']:continue
        mask_file=(PACK/review['mask']).resolve()
        if not mask_file.is_relative_to(PACK.resolve()) or sha(mask_file)!=review['mask_sha256'] or review['image_sha256']!=task['image_sha256']:
            raise ValueError('Referencia humana divergente')
        reviewed.append(task['id']);people.add(task['subject'])
        prediction=BASE/'clinica/normal'/(task['id']+'.npz')
        if not prediction.exists():continue
        with np.load(prediction,allow_pickle=False) as saved:
            if str(saved['checkpoint_sha256'])!=candidate_sha or str(saved['image_sha256'])!=task['image_sha256']:continue
            shape=tuple(saved['shape']);pred=np.unpackbits(saved['predicted'],count=int(np.prod(shape))).reshape(shape).astype(bool)
        with Image.open(mask_file) as image:target=np.asarray(image)
        if target.shape!=pred.shape:raise ValueError('Dimensoes de referencia divergentes')
        valid=target!=255;truth=target==1;pupil=target==2;pred=pred&valid
        tp=int((pred&truth).sum());pp=int(pred.sum());tt=int(truth.sum())
        y,x=np.where(truth|pupil)
        unknown=float((target[y.min():y.max()+1,x.min():x.max()+1]==255).mean()) if len(x) else float((target==255).mean())
        records.append({'id':task['id'],'subject':task['subject'],'dice':(2*tp+1e-6)/(pp+tt+1e-6),
                        'reference_iris_pixels':tt,'pupil_pixels':int(pupil.sum()),
                        'pupil_leak':float((pred&pupil).sum()/pupil.sum()) if pupil.any() else None,
                        'uncertain_fraction':unknown,'mask_sha256':review['mask_sha256']})
    pupil=[r['pupil_leak'] for r in records if r['pupil_leak'] is not None]
    return {'reviewed_images':len(reviewed),'people':len(people),'evaluated_images':len(records),
            'visible_iris_references':sum(r['reference_iris_pixels']>0 for r in records),
            'pupil_references':len(pupil),'macro_dice':float(np.mean([r['dice'] for r in records])) if records else None,
            'p10_dice':float(np.quantile([r['dice'] for r in records],.1)) if records else None,
            'catastrophic_cases':sum(r['dice']<.5 for r in records),
            'macro_pupil_leak':float(np.mean(pupil)) if pupil else None,
            'maximum_uncertain_fraction':max((r['uncertain_fraction'] for r in records),default=None),'records':records}


def assess(segmentation,clinical,identity,criteria,checkpoint_sha):
    s=criteria['segmentation_validation'];c=criteria['clinical_normal_controls']
    seg_ok=bool(segmentation and not segmentation.get('development_smoke_only') and
                all(m in segmentation['validation'] and segmentation['validation'][m]['samples']>=s['minimum_images_each_condition'] and
                    segmentation['validation'][m]['macro_dice']>=s['minimum_macro_dice_each_condition'] for m in s['conditions']))
    clinical_ok=bool(clinical['reviewed_images']>=c['minimum_reviewed_images'] and clinical['people']>=c['minimum_people'] and
                     clinical['evaluated_images']>=c['minimum_reviewed_images'] and clinical['visible_iris_references']>=c['minimum_reviewed_images'] and
                     clinical['pupil_references']>=c['minimum_visible_pupil_references'] and
                     clinical['macro_dice']>=c['minimum_macro_dice'] and clinical['p10_dice']>=c['minimum_p10_dice'] and
                     clinical['catastrophic_cases']<=c['maximum_catastrophic_dice_below_0_5'] and
                     clinical['macro_pupil_leak']<=c['maximum_macro_pupil_leak_fraction'] and
                     clinical['maximum_uncertain_fraction']<=c['maximum_uncertain_fraction_in_eye_region'])
    id_ok=bool(checkpoint_sha and identity and identity.get('checkpoint_sha256')==checkpoint_sha and identity_gate(identity.get('counts'),criteria['identification_study']))
    return {'segmentation_validation_passed':seg_ok,'clinical_normal_controls_passed':clinical_ok,
            'segmentation_pilot_ready':seg_ok and clinical_ok,'identification_gate_passed':id_ok,
            'biometric_anomaly_study_ready':seg_ok and clinical_ok and id_ok,
            'clinical_anomaly_causal_effect_established':False,'checkpoint_sha256':checkpoint_sha}


def report():
    criteria=json.loads((ROOT/'criterios_prontidao_anomalias.json').read_text(encoding='utf-8'))
    final_file=BASE/'CONCLUIDO.json';seg=json.loads(final_file.read_text()) if final_file.exists() else None
    candidate_sha=seg['checkpoint_sha256'] if seg else None
    clinical=clinical_normals(candidate_sha)
    id_file=BASE/'identidade/novo_original_0.json'
    identity=json.loads(id_file.read_text()) if id_file.exists() else None
    state=assess(seg,clinical,identity,criteria,candidate_sha)
    state.update(updated_utc=datetime.now(timezone.utc).isoformat(),clinical_normal_metrics=clinical,
                 criteria_sha256=sha(ROOT/'criterios_prontidao_anomalias.json'))
    OUT.mkdir(exist_ok=True);write_json(OUT/'estado.json',state)
    lines=['# Prontidão para o piloto com anomalias','',
           '**Metas de engenharia propostas para este projeto. Não são um padrão clínico validado.**','',
           f"Primeiras revisões de olhos normais: **{clinical['reviewed_images']}/30**, de {clinical['people']} pessoas.",'',
           '| Verificação | Meta | Situação |','|---|---|---|',
           f"| Validação de segmentação | Dice macro ≥90% nas quatro condições,1.652 imagens cada | {'Atingida' if state['segmentation_validation_passed'] else 'Pendente ou não atingida'} |",
           f"| Controles clínicos normais | 30 referências humanas; Dice≥90%; sem falhas graves; vazamento na pupila≤2% | {'Atingida' if state['clinical_normal_controls_passed'] else 'Pendente ou não atingida'} |",
           f"| Identificação do mesmo candidato | Rank1/TAR/acerto aceito≥90%,FMR≤1% | {'Atingida' if state['identification_gate_passed'] else 'Pendente ou não atingida'} |",'',
           f"**Piloto de segmentação com anomalias: {'pronto' if state['segmentation_pilot_ready'] else 'ainda não liberado pelos critérios'}**.",'',
           'A primeira revisão do usuário deve ser distinguida de validação anatômica por especialista. As seis imagens com diagnóstico envolvendo íris pertencem a cinco pessoas e permitem um piloto exploratório, sem conclusão populacional ou causal sobre identificação. Óculos e poses sintéticos não comprovam cobertura de óculos e poses clínicas reais.','',
           '[Abrir o editor local de revisão](http://127.0.0.1:8766/). Os rascunhos não entram como referências.','',
           'O percentual mínimo de área exige a avaliação biométrica e a curva de oclusão do mesmo candidato. Não é atribuído por aparência, Dice ou número de épocas.']
    (OUT/'PRONTIDAO.md').write_text('\n'.join(lines),encoding='utf-8')
    return state


if __name__=='__main__':print(json.dumps(report(),ensure_ascii=False,indent=2))
