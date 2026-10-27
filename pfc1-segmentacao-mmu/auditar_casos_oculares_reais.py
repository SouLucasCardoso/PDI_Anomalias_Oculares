"""Reconstroi fusao e decisoes do estudo de casos, sem diagnosticar imagens."""
from pathlib import Path
import argparse,csv,json
import numpy as np
from testar_casos_oculares_reais import ROOT,NAME,ORDER,choose
from avaliar_candidato_congelado import fuse,digest
from avaliar_robustez_reconhecimento import metrics

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--variant',choices=['original','escala3'],default='original');a=p.parse_args();out=a.root/(NAME if a.variant=='original' else 'casos_oculares_escala3_2026-10-27')
    source_file='testar_casos_oculares_reais.py' if a.variant=='original' else 'testar_casos_oculares_escala3.py'
    protocol=json.loads((out/'protocolo.json').read_text());done=json.loads((out/'CONCLUIDO.json').read_text());assert digest(out/'source.py')==protocol['script_sha256']==digest(ROOT/source_file)
    if a.variant=='escala3':assert digest(ROOT/'segmentacao_clinica_escala.py')==protocol['scale_module_sha256']
    for f,h in protocol['sources_sha256'].items():assert digest(Path(f))==h
    frozen=json.loads((ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json').read_text());assert done['threshold_unchanged']==protocol['threshold']==frozen['frozen_threshold']
    source=json.loads((ROOT/'data/slpvld/manifesto.json').read_text());clinical=json.loads((ROOT/'outputs/biometria_clinica_triagem_2026-10-20/manifesto.json').read_text());rows,explicit=choose(source,clinical);assert rows==protocol['rows'] and len(explicit)==9
    hashes={r['image']:r['sha256'] for r in source}
    for row in rows:assert digest(Path(row['image']))==hashes[row['image']]
    rec=[r for r in rows if r['session'] in [1,2]];q=[r for r in rec if r['session']==2];gallery=[r for r in rec if r['session']==1];assert len(q)==4 and len(gallery)==32
    expected=[]
    for r in q:
        candidates=sorted({(g['subject'],g['side']) for g in gallery if g['side']==r['side']});assert len(candidates)==16
        expected.append(candidates.index((r['subject'],r['side'])))
    components=[]
    for name in ORDER:
        with np.load(out/f'scores_{name}.npz') as z:c={k:z[k] for k in z.files}
        np.testing.assert_array_equal(c['labels'],expected);components.append(c)
    scores,valid=fuse(components,frozen['component_calibration_red_and_clahe']);actual,correct,accepted=metrics(scores,np.array(expected),protocol['threshold'],valid)
    assert actual==done['clinical_result']
    with np.load(out/'scores_finais.npz') as z:
        for k,v in dict(scores=scores,valid=valid,labels=expected,correct=correct,accepted=accepted).items():np.testing.assert_array_equal(z[k],v)
    queries=json.loads((out/'consultas_clinicas.json').read_text())
    for i,(r,v) in enumerate(zip(q,queries)):
        assert Path(r['image']).name==v['filename'] and v['correct']==bool(correct[i]) and v['accepted']==bool(accepted[i]) and v['valid']==bool(valid[i])
    areas=json.loads((out/'areas_clinicas.json').read_text());assert {Path(r['image']).name for r in explicit}<={r['filename'] for r in areas}
    for r in areas:
        assert 0<=r['predicted_pixels']<=r['image_pixels'] and abs(r['mask_percent_of_photo']-100*r['predicted_pixels']/r['image_pixels'])<1e-12 and r['anatomical_preserved_percent'] is None
        assert r['polar_support_percent'] is None or 0<=r['polar_support_percent']<=100
    groups=json.loads((out/'grupos_ubipr.json').read_text());csvfile=ROOT/'outputs/diagnostico_resolucao_geometria_val_2026-10-22/consultas.csv';rr=list(csv.DictReader(csvfile.open(encoding='utf-8')))
    for g in groups:
        interval=g['support_interval'];selected=[r for r in rr if (not r['polar_support'] if interval is None else bool(r['polar_support']) and interval[0]<=float(r['polar_support'])<interval[1])]
        assert len(selected)==g['queries'] and sum(r['correct']=='True' for r in selected)==g['correct'] and sum(r['accepted']=='True' for r in selected)==g['accepted']
    assert sum(g['queries'] for g in groups)==482 and done['minimum_anatomical_area'] is None and done['clinical_causal_effect'] is None and not done['main_candidate_replaced']
    genuine_available=(scores[np.arange(len(q)),expected]>-2)&valid
    gallery_diagnostic=dict(query_count=4,nominal_candidate_eyes=16,available_candidates_per_query=(scores>-2).sum(1).tolist(),query_extraction_available=valid.tolist(),genuine_comparison_available=genuine_available.tolist(),unavailable_genuine_count=int((~genuine_available).sum()),interpretation='Do not attribute unavailable genuine enrollment to identity discrimination or anatomical iris loss. All failures retained in primary denominator.')
    (out/'DISPONIBILIDADE_CADASTRO.json').write_text(json.dumps(gallery_diagnostic,indent=2),encoding='utf-8')
    report=dict(status='real_ocular_cases_audited',variant=a.variant,source_image_hashes_verified=len(rows),explicit_iris_images=9,queries=4,candidate_eyes_each=16,unavailable_genuine_comparisons=int((~genuine_available).sum()),frozen_fusion_and_decisions_exact=True,area_denominators_verified=True,anatomical_percent_not_claimed=True,ubipr_groups_all482_reproduced=True)
    (out/'AUDITORIA.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))

if __name__=='__main__':main()
