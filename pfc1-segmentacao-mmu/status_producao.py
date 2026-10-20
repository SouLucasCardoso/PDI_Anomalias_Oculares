"""Mostra progresso salvo em disco sem confundir checkpoint parcial com conclusao."""
import csv
import argparse
import json
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
              'active_protocol': 'PROTOCOLO_AREA_IRIS_2026-10-20.md',
              'clinical_protocol': 'outputs/biometria_clinica_triagem_2026-10-20/protocolo_triagem.json',
              'clinical_status': 'inspect clinical_validation and clinical_test below', 'datasets': {}}
    report['recognition']={}
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
