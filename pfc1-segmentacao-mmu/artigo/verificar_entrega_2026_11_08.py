"""Conferencia final do pacote, da paginacao e das evidencias cientificas."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from lxml import etree
from pypdf import PdfReader
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--render-dir',type=Path,required=True);p.add_argument('--output-json',type=Path,required=True);p.add_argument('--visual-review-json',type=Path,required=True)
    p.add_argument('--dense-analysis',type=Path);p.add_argument('--clinical-figures-dir',type=Path);a=p.parse_args()
    stage=a.render_dir.parent
    final=ROOT/'artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx'
    assert sha(final)==sha(stage/final.name)
    pages=json.loads((a.render_dir/'PAGINACAO_WORD.json').read_text(encoding='utf-8-sig'))
    pdf=next(a.render_dir.glob('*.pdf'));reader=PdfReader(pdf)
    assert pages['pages']==len(reader.pages)==34
    assert pages['bookmarks']['PFC_PAGINA_31']==31
    assert 'REFERÊNCIAS' in reader.pages[30].extract_text()
    assert 'REFERÊNCIAS' not in reader.pages[29].extract_text()
    assert len(list(a.render_dir.glob('page-*.png')))==34
    review=json.loads(a.visual_review_json.read_text(encoding='utf-8-sig'))
    previous_file=Path(review['previous_qa_file'])
    assert sha(previous_file)==review['previous_qa_sha256']
    previous=json.loads(previous_file.read_text(encoding='utf-8-sig'))
    assert review['current_docx_sha256']==sha(final)
    inspected=set(review['inspected_current_pages_at_original_resolution'])
    carried=set(review['unchanged_pages_carried_from_previous_review'])
    assert not inspected&carried and inspected|carried==set(range(1,35))
    for n in range(1,35):
        name=f'page-{n}.png';actual=sha(a.render_dir/name)
        assert review['rendered_page_sha256'][name]==actual
        if n in carried:
            assert previous['rendered_page_sha256'][name]==actual
            assert n in previous['all_pages_visually_reviewed_at_original_resolution']
    package=json.loads((stage/'verificacao_pacote.json').read_text())
    assert package['references']==31
    source=ROOT/'artigo/ARTIGO_CONSOLIDADO_2026-11-08.md'
    assert sha(source)==package['source_sha256']
    reference=json.loads((ROOT/'artigo/verificacao_2026-10-27/template-style-evidence.json').read_text())['input']
    assert sha(reference)==package['template_sha256']
    with zipfile.ZipFile(final) as z,zipfile.ZipFile(reference) as template:
        assert z.testzip() is None
        for part in package['preserved_parts']:assert z.read(part)==template.read(part)
        root=etree.fromstring(z.read('word/document.xml'))
        images=root.findall('.//'+W+'drawing')
        tables=root.findall('.//'+W+'tbl')
        links=root.findall('.//'+W+'hyperlink')
        assert len(images)==5 and len(tables)==12 and len(links)>=31
        rels=etree.fromstring(z.read('word/_rels/document.xml.rels'))
        image_parts=[r.get('Target').replace('media/','word/media/') for r in rels if r.get('Type','').endswith('/image')]
        curve=(a.dense_analysis/'curva_area_identificacao.png') if a.dense_analysis else ROOT/'outputs/ensaio_oclusoes_2026-11-08/analise_final/curva_area_identificacao.png'
        assert sha(curve) in [hashlib.sha256(z.read(part)).hexdigest() for part in image_parts]
        for figure in (a.clinical_figures_dir or ROOT/'artigo/figuras_2026-11-08').glob('*.png'):
            assert sha(figure) in [hashlib.sha256(z.read(part)).hexdigest() for part in image_parts]
    document=Document(final)
    body='\n'.join(p.text for p in document.paragraphs)
    for title in ('Implications of ocular pathologies for iris recognition reliability','DU, Yingzi','69,34%','32,51%'):
        assert title in body
    run=ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    protocol=json.loads((run/'protocolo.json').read_text())
    for name,expected in protocol['source_sha256'].items():assert sha(ROOT/name)==expected
    scientific=json.loads((run/'analise_final/AUDITORIA_FINAL.json').read_text())
    assert len(scientific['counts_recomputed'])==13
    assert all(r['historical_frozen_evaluator_scores_reproduced'] for r in scientific['counts_recomputed'])
    result={'status':'verified','docx':str(final),'docx_sha256':sha(final),'content_pages':30,'reference_pages':4,
        'references_start_physical_page':31,'total_pages_word_and_pdf':34,'references':31,'native_tables':12,'figures':5,
        'hyperlinks':len(links),'template_sha256':sha(reference),'template_opaque_parts_preserved':True,
        'all_pages_visually_reviewed_at_original_resolution':list(range(1,35)),
        'visual_review_trace':review,
        'rendered_page_sha256':{f.name:sha(f) for f in a.render_dir.glob('page-*.png')},
        'scientific_conditions_recounted_and_replayed':13,'queries_per_condition':486,'area_defined_queries':480,
        'globally_improved_model_claimed':False,'local_recognition_gains_reported':True,'universal_or_clinical_minimum_claimed':False,
        'scientific_audit_sha256':sha(run/'analise_final/AUDITORIA_FINAL.json'),
        'source_sha256':sha(source),'pdf_qa_only':str(pdf),'sources_of_frozen_run_unchanged':True}
    validation=ROOT/'outputs/refino_recorte_validacao_final_2026-11-08/CONCLUIDO.json'
    conservative=ROOT/'outputs/contorno_continuo_2026-11-08/CONCLUIDO.json'
    v=json.loads(validation.read_text());c=json.loads(conservative.read_text())
    assert v['n']==c['n']==78
    assert abs(v['mean_dice_previous']-c['mean_dice_previous'])<1e-12
    result['crop_refinement_validation']={'n':78,'unet_dice':v['mean_dice_previous'],
        'sam31_dice':v['mean_dice_refined'],'continuous_margin_dice':c['mean_dice_continuous'],
        'sam31_not_promoted_to_recognizer':True,'recognition_reevaluated':True,
        'validation_sha256':sha(validation),'conservative_sha256':sha(conservative)}
    hybrid_file=ROOT/'outputs/reconhecedor_confirmacao_2026-11-08/analise/AUDITORIA_FINAL.json'
    geometry_file=ROOT/'outputs/sam31_geometria_identidade_2026-11-08/CONCLUIDO.json'
    hybrid=json.loads(hybrid_file.read_text());geometry=json.loads(geometry_file.read_text())
    assert len(hybrid['records'])==13 and not geometry['eligible_gain']
    result['completed_recognition_experiments']={'hybrid_audit_sha256':sha(hybrid_file),
        'sam31_geometry_validation_sha256':sha(geometry_file),'recognizer_replaced':False}
    training_file=ROOT/'outputs/polar_sam31_adaptacao_entrega_2026-11-08/CONCLUIDO.json'
    training_audit_file=ROOT/'outputs/polar_sam31_adaptacao_entrega_2026-11-08/analise/AUDITORIA_TREINO_FINAL.json'
    training=json.loads(training_file.read_text());training_audit=json.loads(training_audit_file.read_text())
    assert not training['eligible_gain'] and training['epochs_completed']==6
    assert training_audit['status']=='verified' and training_audit['selected_epoch'] is None
    result['completed_recognition_experiments'].update(
        polar_training_sha256=sha(training_file),polar_training_audit_sha256=sha(training_audit_file),
        polar_training_selected_epoch=None,polar_training_epochs=6)
    defense_file=ROOT/'outputs/defesa_consolidada_final_2026-11-08/AUDITORIA_DEFESA.json'
    defense_done=json.loads((defense_file.parent/'CONCLUIDO.json').read_text())
    defense=json.loads(defense_file.read_text())
    assert defense_done['audit_sha256']==sha(defense_file)
    assert defense_done['source_sha256']==sha(ROOT/'consolidar_defesa_pfc.py')
    assert len(defense['conditions'])==13 and not defense['new_model_selection']
    for token in ('84,79% a 95,83%','86,25% a 96,75%','0,514% a 1,278%'):
        assert token in body
    result['uncertainty_explicit_in_article']={
        'defense_audit_sha256':sha(defense_file),
        'control_interval95_descriptive_percent':defense['conditions']['original_0']['interval95_cluster_person_percent'],
        'intervals_reused_from_registered_experiment':True,
        'no_population_guarantee_claimed':True}
    if a.dense_analysis:
        dense_file=a.dense_analysis/'AUDITORIA_FINAL.json';dense=json.loads(dense_file.read_text())
        done=json.loads((a.dense_analysis/'CONCLUIDO.json').read_text())
        assert done['audit_sha256']==sha(dense_file) and done['figure_sha256']==sha(curve)
        assert dense['status']=='verified' and dense['conditions']==63 and len(dense['counts_recomputed'])==63
        assert dense['all_queries_retained']==486 and dense['impostors_per_condition']==7290
        assert dense['sources_unchanged'] and not dense['recognizer_replaced']
        assert '1% a 31%' in body and '63 condições' in body
        result.update(scientific_conditions_recounted_and_replayed=63,
            dense_scientific_audit_sha256=sha(dense_file),
            full_dense_relative_gate_passed=dense['comparison_gate_passed'],
            same_fixed480_area_defined_secondary_cohort=True)
        prompt_file=ROOT/'outputs/sam31_prompts_exteriores_2026-11-08/CONCLUIDO.json'
        prompt=json.loads(prompt_file.read_text());assert not prompt['segmentation_gate_passed']
        prompt_dice=prompt['summary']['original']['24']
        assert f'{100*prompt_dice:.2f}'.replace('.',',')+'%' in body
        result['sam31_exterior_prompt_validation']={'completion_sha256':sha(prompt_file),
            'hybrid_dice_clean':prompt_dice,'fallbacks':sum(r['variants']['24']['status']=='coarse_fallback' for r in prompt['records'] if r['condition']=='original'),
            'not_promoted':True}
    if a.clinical_figures_dir:
        figure_provenance=json.loads((a.clinical_figures_dir/'PROVENIENCIA.json').read_text())
        for name,expected in figure_provenance['figure_sha256'].items():assert sha(a.clinical_figures_dir/name)==expected
        matte_file=ROOT/'outputs/sam31_matte_subpixel_2026-11-08/CONCLUIDO.json'
        matte=json.loads(matte_file.read_text());assert not matte['recognition_mask_changed']
        assert all(r['binary_mask_equal_previous'] and r['native_rgb_exact'] for r in matte['records'])
        result['clinical_display_subpixel']={'matte_completion_sha256':sha(matte_file),
            'binary_masks_equal_to_previous':True,'native_rgb_exact':True,'new_clinical_accuracy_claimed':False}
    a.output_json.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','content_pages','reference_pages','references','native_tables','figures','scientific_conditions_recounted_and_replayed')}))

if __name__=='__main__':main()
