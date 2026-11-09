"""Confere os resultados existentes e explicita a incerteza, sem nova seleção."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os
import numpy as np

ROOT = Path(__file__).resolve().parent
LEVELS = (0, 1, 5, 10, 20, 30, 31)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fmt = lambda v, n=2: f'{v:.{n}f}'.replace('.', ',')


def passes(counts, joint=False):
    n = counts['queries']
    return (10*counts['correct'] >= 9*n and 10*counts['accepted'] >= 9*n
            and 100*counts['false_accepts'] <= counts['impostors']
            and (not joint or 10*counts['joint'] >= 9*n))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    run = ROOT/'outputs/ensaio_oclusoes_2026-11-08'
    raw_file = run/'resultados.json'
    audit_file = run/'analise_final/AUDITORIA_FINAL.json'
    protocol_file = run/'protocolo.json'
    frozen_file = ROOT/'outputs/candidato_congelado_2026-10-21/CONGELADO.json'
    files = {str(f): sha(f) for f in (raw_file, audit_file, protocol_file, frozen_file)}
    raw = json.loads(raw_file.read_text())
    audit = json.loads(audit_file.read_text())
    protocol = json.loads(protocol_file.read_text())
    frozen = json.loads(frozen_file.read_text())
    baseline = [r for r in raw if r['model'] == 'historico']
    assert len(baseline) == len(audit['counts_recomputed']) == 13
    for name, expected in protocol['source_sha256'].items():
        assert sha(ROOT/name) == expected, name
    registered = {'registered_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Delivery interpretation of completed results; no new training, inference, threshold or model selection',
        'input_sha256': files, 'source_sha256': sha(__file__),
        'uncertainty': 'Reuse the registered 5000-person-cluster bootstrap intervals, seed20261108, fixed gallery; descriptive pointwise intervals without simultaneous or selection correction',
        'criteria': 'Recount marginal targets 90/90/1 with integer counts; show joint90 separately. Interval containment is descriptive, not a new promotion criterion.'}
    (out/'protocolo.json').write_text(json.dumps(registered, indent=2), encoding='utf-8')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    conditions = {}
    for record in baseline:
        condition, level = record['condition'], record['loss_percent']
        key = f'{condition}_{level}'
        score_file = run/f'scores_historico_{key}.npz'
        expected = next(r for r in audit['counts_recomputed'] if r['condition'] == key)
        assert sha(score_file) == expected['scores_sha256']
        with np.load(score_file, allow_pickle=False) as z:
            s, y, valid = z['scores'], z['labels'], z['valid']
            correct = (s.argmax(1) == y) & valid
            accepted = (s[np.arange(len(y)), y] >= frozen['frozen_threshold']) & valid
            np.testing.assert_array_equal(correct, z['correct'])
            np.testing.assert_array_equal(accepted, z['accepted'])
        impostors = np.ones(s.shape, bool)
        impostors[np.arange(len(y)), y] = False
        counts = {'queries': len(y), 'correct': int(correct.sum()),
            'accepted': int(accepted.sum()), 'joint': int((correct & accepted).sum()),
            'impostors': int(impostors.sum()), 'extraction_failures': int((~valid).sum()),
            'false_accepts': int(((s >= frozen['frozen_threshold']) & valid[:,None] & impostors).sum())}
        assert counts == record['counts']
        assert counts['queries'] == 486 and counts['impostors'] == 7290
        assert passes(counts) == record['passed']
        intervals = record['interval95_cluster_person_pp']
        containment = (intervals['rank1'][0] >= 90 and intervals['tar'][0] >= 90
                       and intervals['fmr'][1] <= 1)
        conditions[key] = {'condition': condition, 'loss_percent': level, 'counts': counts,
            'rates': record['rates'], 'interval95_cluster_person_percent': intervals,
            'marginal_point_targets_pass': passes(counts),
            'joint90_also_required_pass': passes(counts, joint=True),
            'pointwise_intervals_entirely_inside_marginal_targets': containment,
            'scores_sha256': sha(score_file)}
    prefixes = {}
    for direction in ('oclusao_superior', 'oclusao_inferior'):
        prefixes[direction] = {}
        for rule in ('marginal_point_targets_pass', 'joint90_also_required_pass',
                     'pointwise_intervals_entirely_inside_marginal_targets'):
            prefix = []
            for level in LEVELS:
                item = conditions['original_0' if level == 0 else f'{direction}_{level}']
                if not item[rule]:
                    break
                prefix.append(level)
            prefixes[direction][rule] = {'passing_prefix_loss_percent': prefix,
                'lowest_retained_nominal_percent_on_grid': 100-prefix[-1] if prefix else None}
    final = {'status': 'verified', 'conditions': conditions, 'prefixes': prefixes,
        'queries_per_condition': 486, 'impostor_pairs_per_condition': 7290,
        'intervals_reused_without_recalculation': True, 'new_model_selection': False,
        'recognizer_replaced': False, 'independent_confirmation': False,
        'universal_minimum_claimed': False}
    (out/'AUDITORIA_DEFESA.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
    os.environ.setdefault('MPLCONFIGDIR', str(Path(os.environ['TEMP'])/'pfc-matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12})
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    control = conditions['original_0']
    for ax, metric, ci_key, title, target, limits in zip(axes,
            ('rank1','tar','far'), ('rank1','tar','fmr'),
            ('Rank-1 (%)','TAR (%)','FMR (%)'), (90,90,1), ((80,100),(80,100),(0,1.6))):
        point = 100*control['rates'][metric]
        low, high = control['interval95_cluster_person_percent'][ci_key]
        ax.errorbar(point, 0, xerr=[[point-low],[high-point]], fmt='o', color='#075a91', capsize=6, lw=2)
        ax.axvline(target, ymin=.30, color='#b95b00', ls='--', lw=1.5, label='Alvo pontual')
        ax.set_xlim(*limits); ax.set_ylim(-.7,.7); ax.set_yticks([]); ax.set_xlabel(title)
        ax.set_title(f'{fmt(point,3 if metric=="far" else 2)}%')
        ax.text(.5,.16,f'IC 95%: {fmt(low,3 if metric=="far" else 2)} a {fmt(high,3 if metric=="far" else 2)}%',
            transform=ax.transAxes, ha='center', fontsize=10)
        ax.spines[['top','left','right']].set_visible(False)
    axes[0].legend(loc='upper left', fontsize=10, frameon=False)
    fig.suptitle('Controle sem oclusão adicional: incerteza descritiva por pessoa', fontsize=14)
    fig.text(.5,.015,'486 consultas; 16 participantes; 5.000 reamostragens; galeria fixa; dados reutilizados no desenvolvimento.',ha='center',fontsize=10)
    fig.subplots_adjust(left=.045,right=.98,bottom=.21,top=.78,wspace=.35)
    fig.savefig(out/'controle_incerteza.png', dpi=180)
    plt.close(fig)
    lines = ['# Resultados e respostas para a defesa do PFC', '',
        'O estudo demonstra sensibilidade da cadeia à quantidade e à posição da oclusão. O percentual observado depende do protocolo; não foi estabelecido mínimo anatômico universal nem efeito causal de doenças.', '',
        '## Resultado central', '',
        '“Na população e na cadeia avaliadas, retirar parte do suporte de íris alterou a identificação e as falsas correspondências. Com a mesma perda de 31%, o Rank-1 foi 69,34% na orientação superior e 32,51% na inferior. A posição da informação preservada e a estabilidade do processamento importaram, além da quantidade restante.”', '',
        '## Estimativa pontual e incerteza', '',
        '| Medida do controle | Contagem | Estimativa | Intervalo descritivo de 95% | Alvo pontual |',
        '|---|---:|---:|---:|---:|']
    for label, rate, interval, numerator, denominator, target, precision in (
            ('Rank-1','rank1','rank1','correct','queries','≥90%',2),
            ('TAR','tar','tar','accepted','queries','≥90%',2),
            ('FMR','far','fmr','false_accepts','impostors','≤1%',3),
            ('Correto e aceito','joint','joint','joint','queries','≥90% na regra posterior',2)):
        low, high = control['interval95_cluster_person_percent'][interval]
        lines.append(f"| {label} | {control['counts'][numerator]}/{control['counts'][denominator]} | {fmt(100*control['rates'][rate],precision)}% | {fmt(low,precision)}% a {fmt(high,precision)}% | {target} |")
    lines += ['', '![Incerteza do controle e alvos pontuais](controle_incerteza.png)', '',
        'O controle passou pelos três alvos marginais nas estimativas pontuais. Os intervalos ultrapassam seus limites; essa incerteza impede apresentar o resultado como garantia populacional. Os intervalos são ponto a ponto, condicionados à galeria fixa, e não corrigem a seleção ou exposição prévia ao teste. Não formam uma certificação simultânea de 95%.', '',
        '## Qual é o percentual mínimo observado?', '',
        '| Interpretação da grade atual | Superior | Inferior |',
        '|---|---:|---:|',
        '| Menor suporte nominal no prefixo com os três alvos marginais pontuais | 100% | 99% |',
        '| Exigindo também correto e aceito de pelo menos 90% | Nenhum nível aprovado | Nenhum nível aprovado |',
        '| Intervalos descritivos inteiramente dentro dos três alvos | Nenhum nível | Nenhum nível |', '',
        'Essas linhas respondem a perguntas diferentes. Na perda superior de 1%, o controle teve 437 acertos; seriam necessários 438 para chegar a 90% em 486 consultas. O refinamento histórico de outra execução encontrou 99,5% no alto e 99% embaixo, em grade e ambiente próprios. Não se misturam esses valores com os da rodada atual nem se interpolam pontos ausentes.', '',
        '## Como responder às perguntas mais prováveis', '',
        '**Isso comprova a regra de 70%?** A perda de 30% deixou 70% do suporte originalmente anotado; a perda de 31% deixou 69%. Esse denominador não é uma medição normativa do anel completo. A mudança entre os dois níveis não demonstrou ruptura em 70%; os intervalos pareados das perdas de Rank-1 incluíram zero.', '',
        '**Foi isolada a influência da área?** A quantidade nominal retirada foi controlada, com cadastro e limiar fixos. A máscara e a geometria foram recalculadas após a intervenção; o efeito observado reúne textura removida e instabilidade de processamento. O diagnóstico assistido por geometria limpa ajuda a investigar esse mecanismo, mas depende da fotografia original disponível.', '',
        '**Por que não adotar o candidato com mais acertos?** O candidato polar ganhou seis acertos líquidos com 1% de perda superior, mas piorou em condições severas e aumentou falsas correspondências em partes da grade. A regra completa foi preservada; uma melhora localizada não autorizou a troca geral.', '',
        '**E o SAM3.1?** Foi avaliado em segmentação e geometria. Houve ganho localizado de validação, mas o controle limpo piorou. Os treinos e ablações não cumpriram a seleção registrada. A curva principal preserva a referência histórica de identidade; resultados de aparência ou Dice não foram tratados como prova de reconhecimento.', '',
        '**Posso concluir o efeito de patologias?** A extensão clínica tem quatro consultas de apenas dois olhos, sem pares saudáveis equivalentes dos mesmos olhos. Ela documenta falhas de transferência e a necessidade de referências revisadas; não estima causalmente o efeito de uma doença ou seu percentual anatômico mínimo.', '',
        '**O resultado vale para o celular?** A curva usa UBIPr entre sessões, lateralidade informada e dezesseis candidatos do mesmo lado. O aplicativo do S23 é um demonstrador separado, sem limiar clínico ou acurácia móvel validados por esta curva.', '',
        '## Conferência dos dados', '',
        'Foram conferidas as contagens e os hashes dos escores das 13 condições, mantendo 486 consultas e 7.290 pares impostores por condição. As seis referências de área vazia permanecem no denominador primário; a análise secundária fixa usa as mesmas 480 referências definidas. Não houve novo treinamento, inferência, ajuste de limiar ou seleção de modelo nesta consolidação.', '',
        '[Artigo atualizado](../../artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx). [Auditoria desta consolidação](AUDITORIA_DEFESA.json). [Curva completa e fontes](../ensaio_oclusoes_2026-11-08/analise_final/RESULTADO_PARA_DEFESA.md).', '']
    report = out/'GUIA_DEFESA.md'
    report.write_text('\n'.join(lines), encoding='utf-8')
    for path, expected in files.items():
        assert sha(path) == expected
    completion = {'status':'concluido', 'conditions_verified':13,
        'source_sha256':sha(__file__), 'audit_sha256':sha(out/'AUDITORIA_DEFESA.json'),
        'report_sha256':sha(report), 'figure_sha256':sha(out/'controle_incerteza.png'),
        'models_and_threshold_unchanged':True}
    (out/'CONCLUIDO.json').write_text(json.dumps(completion, indent=2), encoding='utf-8')
    print(json.dumps({'completion':completion, 'prefixes':prefixes}, ensure_ascii=False))


if __name__ == '__main__':
    main()
