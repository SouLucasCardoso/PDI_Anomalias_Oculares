"""Auditoria pos-treino por contagens: nao escolhe novamente pesos nem executa inferencia."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from analisar_rodada_segmentacao_area import paired_difference

ROOT = Path(__file__).resolve().parent
BASE = ROOT/'outputs/sam31_iris_adaptacao_2026-11-03'
OUT = BASE/'auditoria_treino_2026-11-04'
MODES = ('clean', 'zoom3', 'oblique', 'glasses')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def summarize(rows):
    dice = np.array([r['dice'] for r in rows])
    return {'samples': len(rows), 'macro_dice': float(dice.mean()) if len(rows) else None,
            'dice_below_0_5': int((dice < .5).sum()),
            'empty_reference_false_positives': sum(r['empty_reference_false_positive'] for r in rows)}


def main():
    OUT.mkdir(exist_ok=True)
    if any(OUT.iterdir()):
        raise ValueError('Preservar auditoria existente; usar outra versao de analise')
    protocol = read(BASE/'protocolo.json')
    final = read(BASE/'CONCLUIDO.json')
    if final['development_smoke_only']:
        raise ValueError('Nao analisar smoke como rodada real')
    for name, expected in protocol['frozen']['sources'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Fonte de treino alterada: '+name)
    selected = BASE/f'candidato_epoca_{final["best_epoch"]:02}.pt'
    if sha(selected) != final['checkpoint_sha256']:
        raise ValueError('Checkpoint selecionado divergente')
    files = sorted(BASE.glob('validacao_epoca_*.json'))
    histories, evidence = [], {}
    baseline, candidate = None, None
    for file in files:
        epoch = int(file.stem.rsplit('_', 1)[1])
        data = read(file)
        for mode in MODES:
            rows = data[mode]['records']
            if len(rows) != data[mode]['samples'] or len(rows) != 1652:
                raise ValueError('Validacao incompleta')
            for row in rows:
                tp, pp, tt = row['intersection_pixels'], row['prediction_pixels'], row['reference_pixels']
                if not 0 <= tp <= min(pp, tt):
                    raise ValueError('Contagens de pixels invalidas')
                if (not np.isclose(row['dice'], (2*tp+1e-6)/(pp+tt+1e-6), rtol=0, atol=1e-12) or
                        not np.isclose(row['iou'], (tp+1e-6)/(pp+tt-tp+1e-6), rtol=0, atol=1e-12)):
                    raise ValueError('Metrica nao reproduz as contagens')
                if row['empty_reference_false_positive'] != bool(tt == 0 and pp > 0):
                    raise ValueError('Indicador de referencia vazia incorreto')
            if not np.isclose(np.mean([r['dice'] for r in rows]), data[mode]['macro_dice'], rtol=0, atol=1e-12):
                raise ValueError('Media de Dice divergente')
            if sum(r['dice'] < .5 for r in rows) != data[mode]['catastrophic_cases']:
                raise ValueError('Contagem de falhas graves divergente')
        histories.append({'epoch': epoch, 'dice': {m: data[m]['macro_dice'] for m in MODES}})
        evidence[file.name] = sha(file)
        if epoch == 0:
            baseline = data
        if epoch == final['best_epoch']:
            candidate = data
    if [h['epoch'] for h in histories] != list(range(21)):
        raise ValueError('Esperadas todas as epocas de zero a vinte')
    # Reproduzir a regra congelada, incluindo a protecao da condicao original.
    best, best_epoch = min(histories[0]['dice'].values()), 0
    for row in histories[1:]:
        score = min(row['dice'].values())
        if row['dice']['clean'] >= histories[0]['dice']['clean']-.005 and score > best:
            best, best_epoch = score, row['epoch']
    if best_epoch != final['best_epoch'] or best != final['best_score']:
        raise ValueError('Selecao registrada nao reproduz a regra')
    modes = {}
    for mode in MODES:
        old, new = baseline[mode]['records'], candidate[mode]['records']
        if [(r['image'], r['subject'], r['reference_pixels']) for r in old] != [
                (r['image'], r['subject'], r['reference_pixels']) for r in new]:
            raise ValueError('Consultas ou alvos nao pareados')
        groups = {}
        for name, indices in (
                ('all', list(range(len(old)))),
                ('reference_positive', [i for i,r in enumerate(old) if r['reference_pixels'] > 0]),
                ('reference_empty', [i for i,r in enumerate(old) if r['reference_pixels'] == 0])):
            a, b = [old[i] for i in indices], [new[i] for i in indices]
            groups[name] = {'baseline': summarize(a), 'selected': summarize(b)}
            if a:
                groups[name]['paired_dice_change'] = paired_difference(
                    [r['dice'] for r in a], [r['dice'] for r in b], [r['subject'] for r in a])
        modes[mode] = groups
    report = {'audited_utc': datetime.now(timezone.utc).isoformat(), 'best_epoch': best_epoch,
              'checkpoint_sha256': final['checkpoint_sha256'], 'selection_rule_reproduced': True,
              'all_epochs_pixel_metrics_audited': len(histories), 'samples_per_condition': 1652,
              'epoch_zero_and_selected_paired': True, 'modes': modes,
              'bootstrap': {'replicates': 5000, 'seed': 127, 'unit': 'validation person'},
              'post_selection_intervals_descriptive_not_independent_confirmation': True,
              'sam3_specific_causal_gain_isolated': False,
              'recognition_or_minimum_area_measured_here': False,
              'sources': {'audit': sha(Path(__file__)), 'metrics': sha(ROOT/'analisar_rodada_segmentacao_area.py')},
              'evidence_sha256': evidence, 'training_protocol_sha256': sha(BASE/'protocolo.json')}
    (OUT/'AUDITORIA.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT/'source.py').write_bytes(Path(__file__).read_bytes())
    lines = ['# Auditoria do treino SAM3.1', '',
             'As 20 epocas foram concluidas. A regra original de selecao reproduziu a **epoca 15**, sem consultar identidade.', '',
             '| Condicao | Epoca zero | Epoca 15 | Delta Dice (pp) | Intervalo descritivo 95% (pp) | Falhas Dice<50%: antes / depois |',
             '|---|---:|---:|---:|---:|---:|']
    for mode, groups in modes.items():
        a, b = groups['all']['baseline'], groups['all']['selected']
        change = groups['all']['paired_dice_change']
        lo, hi = change['interval95_cluster_person_pp']
        lines.append(f"| {mode} | {100*a['macro_dice']:.2f}% | {100*b['macro_dice']:.2f}% | {change['candidate_minus_original_pp']:+.2f} | [{lo:+.2f}, {hi:+.2f}] | {a['dice_below_0_5']} / {b['dice_below_0_5']} |")
    lines += ['', 'Todas as condicoes usam as mesmas 1.652 imagens e transformacoes da epoca zero. Os intervalos sao descritivos, agrupados por pessoa e calculados apos selecao na mesma validacao.', '',
              '**A meta de Dice macro >=90% nas quatro condicoes ainda nao foi atingida.** A avaliacao biometrica continua separada e nao e substituida por este resultado.', '',
              '| Condicao | Referencias positivas | Referencias vazias | Dice nas positivas: antes / depois | Falsos positivos nas vazias: antes / depois |',
              '|---|---:|---:|---:|---:|']
    for mode, groups in modes.items():
        a,b=groups['reference_positive']['baseline'],groups['reference_positive']['selected']
        x,y=groups['reference_empty']['baseline'],groups['reference_empty']['selected']
        lines.append(f"| {mode} | {a['samples']} | {x['samples']} | {100*a['macro_dice']:.2f}% / {100*b['macro_dice']:.2f}% | {x['empty_reference_false_positives']} / {y['empty_reference_false_positives']} |")
    lines += ['', 'Os grupos sao apenas diagnosticos; nenhuma imagem foi removida da metrica principal ou do treino. Referencia vazia nao demonstra ausencia anatomica de iris.', '',
              'O ganho compara o pacote treinado com a sua epoca zero. O ramo RGB, a projecao SAM3 e a perda participaram da adaptacao; esta comparacao nao isola a contribuicao causal do SAM3 de mais epocas ou do novo objetivo de perda. Isso exigiria um controle de treino RGB pareado.', '',
              '[Acompanhamento da avaliacao de reconhecimento](../analise_area/RELATORIO_ATUAL.md).']
    (OUT/'RELATORIO.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'best_epoch': best_epoch, 'selection_reproduced': True,
                      'epochs_audited': len(histories),
                      'delta_dice_pp': {m:g['all']['paired_dice_change']['candidate_minus_original_pp'] for m,g in modes.items()},
                      'empty_reference_cases': {m:g['reference_empty']['baseline']['samples'] for m,g in modes.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
