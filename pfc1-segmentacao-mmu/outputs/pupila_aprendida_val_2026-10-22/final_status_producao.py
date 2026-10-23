"""Mostra progresso salvo em disco sem confundir checkpoint parcial com conclusao."""
import csv
import argparse
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Salvar snapshot UTF-8 dentro de outputs/')
    args=parser.parse_args()
    out = ROOT / 'outputs/cnn/ubipr_retreino_2026-10-20'
    history_file = out / 'historico.csv'
    history = []
    if history_file.exists():
        with history_file.open(encoding='utf-8', newline='') as stream:
            history = list(csv.DictReader(stream))
    metrics_file = out / 'metricas.json'
    report = {'training': {'status': 'completed' if metrics_file.exists() else 'not_completed',
                           'epochs_recorded': len(history), 'checkpoint_exists': (out / 'melhor_modelo.pt').exists(),
                           'last_validation': history[-1] if history else None,
                           'warning': 'not_completed may mean running or interrupted; inspect log/process.'},
              'objective': 'iris preserved area and ocular identity recognition',
              'confirmed_scope': {'primary_dataset':'UBIPr','query_images_per_identification':1,'multiple_enrollment_images_allowed':True,'query_side_may_be_required':True,'side_informed_candidate_eyes_per_query':16,'previous32_eye_protocol_preserved':True},
              'active_protocol': 'PROTOCOLO_AREA_IRIS_2026-10-20.md',
              'clinical_protocol': 'outputs/biometria_clinica_triagem_2026-10-20/protocolo_triagem.json',
              'clinical_status': 'inspect clinical_validation and clinical_test below', 'datasets': {}}
    report['frozen_candidate_evaluation']={}
    for split in ['val','test']:
        name=f'confirmacao_congelada_{split}_2026-10-21'
        folder=ROOT/'outputs'/name
        temporary=Path(tempfile.gettempdir())/'pfc-tcc-resultados'/name
        if not (folder/'protocolo.json').exists() and (temporary/'protocolo.json').exists():folder=temporary
        entry={'protocol_registered':(folder/'protocolo.json').exists(),'completed':(folder/'CONCLUIDO.json').exists(),'artifact_directory':str(folder),'note':'Frozen calibration/threshold; test previously exposed to other strategies, external pretraining overlap unknown'}
        if (folder/'CONCLUIDO.json').exists():entry['result']=json.loads((folder/'CONCLUIDO.json').read_text(encoding='utf-8'))
        report['frozen_candidate_evaluation'][split]=entry
    report['frozen_occlusion']={}
    for kind,name in [('coarse','curva_oclusao_congelada_2026-10-21'),('refinement','refinamento_oclusao_congelada_2026-10-21')]:
        folder=ROOT/'outputs'/name
        temporary=Path(tempfile.gettempdir())/'pfc-tcc-resultados'/name
        if not (folder/'protocolo.json').exists() and (temporary/'protocolo.json').exists():folder=temporary
        entry={'protocol_registered':(folder/'protocolo.json').exists(),'completed':(folder/'CONCLUIDO.json').exists(),'artifact_directory':str(folder),'note':'Frozen threshold, all queries retained; visible annotated pixel loss, not clinical/anatomical minimum'}
        if (folder/'CONCLUIDO.json').exists():entry['result']=json.loads((folder/'CONCLUIDO.json').read_text(encoding='utf-8'))
        elif (folder/'progresso.json').exists():entry['progress']=json.loads((folder/'progresso.json').read_text(encoding='utf-8'))
        report['frozen_occlusion'][kind]=entry
    report['recognition']={}
    report['recognizer_development']={}
    for name,folder_name in [('normalization','melhoria_normalizacao_val_gpu_2026-10-20'),
                             ('resolution','melhoria_resolucao_encoder_val_2026-10-20'),
                             ('multicapture','cadastro_multicaptura_val_v2_2026-10-20'),
                             ('polar_support','suporte_polar_val_2026-10-20'),
                             ('automatic_finetuning','identidade_automatica_2026-10-20'),
                             ('automatic_metric_learning','identidade_metrica_automatica_2026-10-20'),
                             ('tripletiris_pretrained','tripletiris_validacao_2026-10-20'),
                             ('tripletiris_ellipse','tripletiris_elipse_validacao_2026-10-20'),
                             ('polar_encoder','encoder_polar_2026-10-20'),
                             ('loggabor_phase','loggabor_polar_val_2026-10-20'),
                             ('spatial_matching','espacial_polar_val_2026-10-20'),
                             ('fixed_rgb_polar_fusion','fusao_polar_rgb_val_2026-10-20'),
                             ('fixed_three_way_fusion','fusao_espacial_val_2026-10-20'),
                             ('dense_polar_encoder','encoder_polar_denso_2026-10-20'),
                             ('fixed_four_way_fusion','fusao_densa_val_2026-10-20'),
                             ('training_only_linear_metric','metrica_intra_val_2026-10-20'),
                             ('resnet50_session_training','resnet50_sessoes_2026-10-20'),
                             ('single_query_normalization','normalizacao_consulta_2026-10-20'),
                             ('single_photo_multiview','multivista_foto_unica_2026-10-20'),
                             ('spatial_layer2_enrollment','espacial_capturas_val_2026-10-20'),
                             ('enrollment_cohort_normalization','normalizacao_cadastro_2026-10-20'),
                             ('resnet50_fixed_fusion','fusao_resnet50_val_2026-10-20'),
                             ('enrollment_classifier','classificador_cadastro_2026-10-20'),
                             ('convnext_contrast_training','convnext_contraste_2026-10-20'),
                             ('side_informed_resnet50','lateralidade_resnet50_2026-10-20'),
                             ('side_conditioned_fusion4','fusao_lateral_4_2026-10-20'),
                             ('side_conditioned_fusion5','fusao_lateral_5_2026-10-20'),
                             ('side_enrollment_classifiers','classificador_lateral_2026-10-20'),
                             ('convnext_full32_fusion','fusao_convnext_val_2026-10-20'),
                             ('wide_resnet50','backbone_resnet50_2026-10-21'),
                             ('wide_convnext','backbone_convnext_2026-10-21'),
                             ('native224_training','resnet50_nativo224_2026-10-21'),
                             ('side_conditioned_fusion6','fusao_lateral_6_2026-10-21'),
                             ('polar_transformer','transformer_polar_2026-10-21'),
                             ('side_conditioned_fusion7','fusao_lateral_7_2026-10-21'),
                             ('angular_alignment','alinhamento_transformer_2026-10-21'),
                             ('photometric_alignment','alinhamento_fotometrico_2026-10-21'),
                             ('enrollment_quality','selecao_cadastro_2026-10-21'),
                             ('scale_prototypes','prototipos_escala_2026-10-21'),
                             ('external_arciris_clahe','arciris_polar_2026-10-21'),
                             ('external_arciris_red','arciris_red_2026-10-21'),
                             ('external_arciris_equal_views','arciris_duas_vistas_2026-10-21'),
                             ('occlusion_segmenter_training','segmentacao_oclusao_2026-10-21'),
                             ('occlusion_segmenter_recognition_validation','validacao_segmentacao_oclusao_identidade_2026-10-21'),
                             ('dual_segmentation_validation','dupla_segmentacao_val_2026-10-21'),
                             ('identity_occlusion_adaptation','identidade_oclusao_segmentacao_2026-10-21'),
                             ('identity_occlusion_fusion','fusao_identidade_adaptada_val_2026-10-21'),
                             ('identity_residual_mapping','identidade_residual_oclusao_2026-10-21'),
                             ('identity_residual_fusion','fusao_identidade_residual_val_2026-10-21'),
                             ('local_texture_matching','textura_local_val_2026-10-21'),
                             ('validation_error_audit','diagnostico_erros_val_2026-10-21'),
                             ('trimmed_fusion','fusao_aparada_val_2026-10-21'),
                             ('training_only_regularized_fusion','fusao_regularizada_treino_2026-10-21'),
                             ('person_disjoint_identity_fusion','fusao_pessoas_separadas_2026-10-21'),
                             ('resolution_geometry_diagnostic','diagnostico_resolucao_geometria_val_2026-10-22'),
                             ('pupil_locator_training','localizador_pupila_2026-10-22'),
                             ('pupil_locator_identity_validation','pupila_aprendida_val_2026-10-22'),
                             ('original_geometry_diagnostic','diagnostico_geometria_fixa_2026-10-21'),
                             ('enrollment_adaptation_failed','adaptacao_cadastro_2026-10-21'),
                             ('enrollment_adaptation','adaptacao_cadastro_v2_2026-10-21')]:
        folder=ROOT/'outputs'/folder_name
        temporary=Path(tempfile.gettempdir())/'pfc-tcc-resultados'/folder_name
        if not (folder/'protocolo.json').exists() and (temporary/'protocolo.json').exists():folder=temporary
        if name in ['training_only_regularized_fusion','person_disjoint_identity_fusion'] and not (folder/'CONCLUIDO.json').exists() and (temporary/'protocolo.json').exists():folder=temporary
        entry={'protocol_registered':(folder/'protocolo.json').exists(),
               'completed':(folder/'CONCLUIDO.json').exists(),
               'artifact_directory':str(folder),
               'note':'Development only; absent completion may mean running or interrupted; no independent confirmation'}
        if name=='training_only_regularized_fusion':
            score_folder=temporary if (temporary/'clean').exists() else folder
            entry['score_component_directory']=str(score_folder)
            entry['score_components_saved']=sum(len(list((score_folder/condition).glob('scores_*.npz'))) for condition in ['clean','upper10','lower10'])
            entry['score_components_expected']=27
            entry['fusion_weights_fitted']=(folder/'MODELO_FUSAO.json').exists()
        if (folder/'CONCLUIDO.json').exists():entry['result']=json.loads((folder/'CONCLUIDO.json').read_text(encoding='utf-8'))
        if name=='person_disjoint_identity_fusion' and (folder/'progresso.json').exists():entry['progress']=json.loads((folder/'progresso.json').read_text(encoding='utf-8'))
        if (folder/'INTERROMPIDO_TECNICO.json').exists():
            entry['interrupted_technical']=True
            entry['interruption']=json.loads((folder/'INTERROMPIDO_TECNICO.json').read_text(encoding='utf-8'))
        if (folder/'historico.csv').exists():
            with (folder/'historico.csv').open(encoding='utf-8',newline='') as stream:recorded=list(csv.DictReader(stream))
            entry['epochs_after_baseline']=sum(int(r['epoch'])>0 for r in recorded)
            entry['last_validation']=recorded[-1] if recorded else None
        report['recognizer_development'][name]=entry
    identity_run=ROOT/'outputs/identidade_arcface_ubipr_2026-10-20'
    identity_history=[]
    if (identity_run/'historico.csv').exists():
        with (identity_run/'historico.csv').open(encoding='utf-8',newline='') as stream: identity_history=list(csv.DictReader(stream))
    report['identity_training']={'protocol_registered':(identity_run/'protocolo.json').exists(),
                                 'completed':(identity_run/'CONCLUIDO.json').exists(),
                                 'epochs_recorded':len(identity_history),
                                 'last_validation':identity_history[-1] if identity_history else None,
                                 'note':'Exploratory ResNet18 angular-margin training; Nuclear evaluation registered before recognition'}
    if (identity_run/'CONCLUIDO.json').exists(): report['identity_training']['result']=json.loads((identity_run/'CONCLUIDO.json').read_text(encoding='utf-8'))
    nuclear_run=ROOT/'outputs/nuclear_identidade_arcface_2026-10-20'
    report['nuclear_identity']={'preprocessing_registered':(nuclear_run/'protocolo_preprocessamento.json').exists(),
                                'recognition_protocol_registered':(nuclear_run/'protocolo_avaliacao.json').exists(),
                                'completed':(nuclear_run/'CONCLUIDO.json').exists()}
    report['nuclear_identity']['interrupted_by_quality_review']=(nuclear_run/'INTERROMPIDO_QA.json').exists()
    follow_up=ROOT/'outputs/area_encoder_ubipr_2026-10-20'
    report['trained_encoder_area']={'registered':(follow_up/'protocolo.json').exists(),
                                   'completed':(follow_up/'CONCLUIDO.json').exists(),
                                   'note':'Exploratory follow-up on previously examined UBIPr test'}
    if (follow_up/'area_minima.json').exists(): report['trained_encoder_area']['result']=json.loads((follow_up/'area_minima.json').read_text(encoding='utf-8'))
    report['conditional_analysis_completed']=(ROOT/'outputs/tolerancia_condicional_exploratoria_2026-10-20/CONCLUIDO.json').exists()
    if (nuclear_run/'progresso.json').exists(): report['nuclear_identity']['preprocessing_progress']=json.loads((nuclear_run/'progresso.json').read_text(encoding='utf-8'))
    clinical=ROOT/'outputs/hdbif_slpvld_validacao_completa_2026-10-20'
    report['clinical_validation']={'completed':(clinical/'CONCLUIDO.json').exists(),
                                   'test_recognition_started':(ROOT/'outputs/hdbif_slpvld_teste_congelado_2026-10-20/protocolo.json').exists(),
                                   'cached_templates':len(list((clinical/'templates').glob('*.npz'))),
                                   'note':'Development-only HDBIF validation; not a clinical minimum-area estimate'}
    if (clinical/'resultado.json').exists():
        report['clinical_validation']['result']=json.loads((clinical/'resultado.json').read_text(encoding='utf-8'))
    clinical_test=ROOT/'outputs/hdbif_slpvld_teste_congelado_2026-10-20'
    report['clinical_test']={'completed':(clinical_test/'CONCLUIDO.json').exists(),
                             'protocol_registered':(clinical_test/'protocolo.json').exists(),
                             'cached_templates':len(list((clinical_test/'templates').glob('*.npz'))),
                             'note':'Frozen original-image recognition, no minimum-area estimate'}
    if (clinical_test/'resultado.json').exists():
        report['clinical_test']['result']=json.loads((clinical_test/'resultado.json').read_text(encoding='utf-8'))
    for name, rel in [('pilot','biometria_area_piloto_2026-10-20'),('full','biometria_area_completa_2026-10-20')]:
        folder=ROOT/'outputs'/rel
        summary=folder/'resumo.csv'; rows=[]
        if summary.exists():
            with summary.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
        report['recognition'][name]={'completed':(folder/'CONCLUIDO.json').exists(),'result_rows':len(rows),
                                    'note':'pilot is technical only' if name=='pilot' else 'completion requires CONCLUIDO.json; absent may mean waiting, running or interrupted'}
    if metrics_file.exists():
        metrics = json.loads(metrics_file.read_text(encoding='utf-8'))
        report['training']['best_epoch'] = metrics['best_epoch']
        report['training']['test'] = metrics['test']
    for name, rel in [('catscreen', 'data/catscreen/auditoria.json'),
                      ('slid', 'data/slid/auditoria.json'), ('nuclear', 'data/nuclear/auditoria.json'),
                      ('slpvld', 'data/slpvld/auditoria.json')]:
        path = ROOT / rel
        report['datasets'][name] = {'audited': path.exists()}
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            report['datasets'][name]['images'] = data.get('images')
    partial = ROOT / 'data/archives/slp-vld-v3.zip.part'
    if partial.exists():
        report['datasets']['slpvld']['downloaded_bytes'] = partial.stat().st_size
        report['datasets']['slpvld']['expected_bytes'] = 3521274419
    content=json.dumps(report,indent=2,ensure_ascii=False)
    if args.output:
        destination=args.output.resolve()
        if not destination.is_relative_to((ROOT/'outputs').resolve()): raise ValueError('Salvar snapshot somente em outputs/')
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(content,encoding='utf-8')
    print(content)


if __name__ == '__main__':
    main()
