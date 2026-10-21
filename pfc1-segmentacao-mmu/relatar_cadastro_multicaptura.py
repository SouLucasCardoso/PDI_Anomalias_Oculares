"""Consolida onze variantes sem apresentar desenvolvimento como teste final."""
from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/cadastro_multicaptura_val_v2_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,paired_ci
    summary=json.loads((OUT/'CONCLUIDO.json').read_text())
    results=summary['results']; assert len(results)==11
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    subjects=np.array([r.subject for r in rows if r.session==2])
    saved={}
    for r in results:
        with np.load(OUT/(r['variant']+'.npz')) as z: saved[r['variant']]={key:z[key] for key in z.files}
    replication=[]
    for new,old in [('neural_reference_first',ROOT/'outputs/melhoria_resolucao_encoder_val_2026-10-20/scores_128.npz'),
                    ('hdbif_reference_first',ROOT/'outputs/melhoria_normalizacao_val_gpu_2026-10-20/roi_reference/scores.npz')]:
        with np.load(old) as z:
            np.testing.assert_array_equal(saved[new]['labels'],z['labels'])
            tolerance=1e-6 if new.startswith('neural') else 1e-12
            np.testing.assert_allclose(saved[new]['scores'],z['scores'],atol=tolerance,rtol=0)
            for key in ('correct','accepted','valid'): np.testing.assert_array_equal(saved[new][key],z[key])
            replication.append({'variant':new,'maximum_absolute_score_difference':float(np.abs(saved[new]['scores']-z['scores']).max()),'absolute_tolerance':tolerance,'decisions_and_validity_identical':True})
    (OUT/'replicacao_controles.json').write_text(json.dumps(replication,indent=2),encoding='utf-8')
    pairs=[('neural_reference_centroid','neural_reference_first'),('neural_automatic_top3','neural_automatic_first'),
           ('neural_automatic_top3','neural_reference_top3'),('neural_automatic_centroid','neural_reference_centroid'),
           ('hdbif_reference_max','hdbif_reference_first'),('hdbif_reference_top3','hdbif_reference_first')]
    comparisons=[]
    byname={r['variant']:r for r in results}
    for new,old in pairs:
        entry={'new':new,'baseline':old}
        for metric,key in [('rank1','correct'),('tar','accepted')]:
            entry[metric]={'gain_pp':100*(byname[new][metric]-byname[old][metric]),'ci95_pp':paired_ci(saved[new][key],saved[old][key],subjects)}
        comparisons.append(entry)
    common=saved['neural_automatic_top3']['valid']&saved['neural_reference_top3']['valid']
    conditional={'queries':int(common.sum()),'note':'Secondary shared-valid subset only; all482 retained in primary metrics',
        'automatic':{key:float(saved['neural_automatic_top3'][key][common].mean()) for key in ('correct','accepted')},
        'reference':{key:float(saved['neural_reference_top3'][key][common].mean()) for key in ('correct','accepted')}}
    (OUT/'comparacoes_pareadas.json').write_text(json.dumps({'comparisons':comparisons,'common_valid_secondary':conditional,'note':'Pointwise 5000 person-cluster bootstrap, fixed gallery and development-calibrated thresholds; no multiple-comparison correction or independent confirmation'},indent=2),encoding='utf-8')
    with (OUT/'resumo.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(results[0])); w.writeheader(); w.writerows(results)
    lines=['# Cadastro multicaptura e recorte automático — validação de 20/10/2026','',
        '## 1. Execução concluída','',
        'Foram concluídas onze variantes, mantendo os pesos de identidade e segmentação congelados. A base de desenvolvimento tem 962 imagens de 16 pessoas e 32 olhos: 480 capturas da sessão 1 para cadastro e 482 consultas da sessão 2. Nenhum novo escore de teste ou oclusão foi gerado.','',
        'As variantes neurais comparam máscara de referência e máscara automática da U-Net, com cadastro de uma foto, máximo entre fotos, média das três melhores correspondências e centróide. O HDBIF usa o recorte de referência antes da normalização e as três primeiras regras de cadastro. Cada variante tem limiar próprio, calibrado na mesma validação para FMR empírica de até 1%. Não foi usado o limiar de cadastro único para favorecer o cadastro múltiplo.','',
        '## 2. Todas as variantes','',
        '| Configuração | Rank-1 | TAR | FMR | Identificação e aceitação conjuntas | Falhas de consulta |',
        '|---|---:|---:|---:|---:|---:|']
    names={'neural':'Encoder','hdbif':'HDBIF','reference':'referência','automatic':'automático','first':'uma foto','max':'máximo','top3':'média top-3','centroid':'centróide'}
    for r in results:
        label=' / '.join(names[x] for x in r['variant'].split('_'))
        p=lambda key:f"{100*r[key]:.2f}%".replace('.',',')
        lines.append(f"| {label} | {p('rank1')} | {p('tar')} | {p('far')} | {p('joint_success')} | {r['extraction_failures']} |")
    lines+=['','## 3. Comparações pareadas','',
        'Os ganhos abaixo usam as mesmas consultas. ICs de 95% pontuais foram calculados com 5.000 reamostragens de pessoas, mantendo galeria e limiares fixos. São análises de desenvolvimento, sem correção por múltiplas comparações.','',
        '| Comparação: nova − referência | Ganho Rank-1 (pp) | IC 95% | Ganho TAR (pp) | IC 95% |',
        '|---|---:|---|---:|---|']
    for entry in comparisons:
        a,b=entry['rank1'],entry['tar']
        lines.append(f"| {entry['new']} − {entry['baseline']} | {a['gain_pp']:.2f} | {a['ci95_pp'][0]:.2f} a {a['ci95_pp'][1]:.2f} | {b['gain_pp']:.2f} | {b['ci95_pp'][0]:.2f} a {b['ci95_pp'][1]:.2f} |")
    lines+=['','## 4. Interpretação e limites','',
        'O cadastro múltiplo deve ser comparado com a foto única na mesma máscara e extrator. Comparar os números deste quadro com os 67,90% de Rank-1 anteriores sem explicar a partição é incorreto: aquele resultado é do teste; este é da validação. O centróide com referência já fazia parte do protocolo neural anterior. Reproduzi-lo aqui não constitui um novo avanço além daquele benchmark.','',
        'No HDBIF, o máximo multicaptura piorou Rank-1 de 42,12% para 6,43% e TAR de 24,69% para 1,45%; a média top-3 também piorou. Não será adotado como melhoria. Mais fotos ampliam a exposição a comparações espúrias; um diagnóstico posterior dos cadastros vencedores foi registrado separadamente, sem remoção retrospectiva. É necessário investigar suporte de máscara e sobreposição entre códigos antes de propor uma nova regra de comparação.','',
        'O controle automático é uma implementação completa de extração de máscara e comparação de identidade nas imagens originais. Não usa a referência para corrigir a previsão. O encoder, porém, foi treinado com referências; as máscaras previstas podem incluir textura externa ou omitir regiões. Um ganho no automático não comprova maior precisão anatômica nem reconhecimento exclusivamente da textura da íris. A boa métrica de segmentação, isoladamente, também não garante identidade correta.','',
        f'As comparações automáticas e de referência não têm exatamente as mesmas falhas. No subconjunto secundário em que ambas as extrações top-3 são válidas, há **{conditional["queries"]} consultas**. Nesse subconjunto, Rank-1 automático é {100*conditional["automatic"]["correct"]:.2f}% e de referência {100*conditional["reference"]["correct"]:.2f}%; TAR automático é {100*conditional["automatic"]["accepted"]:.2f}% e de referência {100*conditional["reference"]["accepted"]:.2f}%. Esses números não substituem a tabela operacional de todas as 482 consultas.','',
        'O limiar é recalibrado por variante na própria validação; diferenças de TAR refletem o sistema completo, não apenas uma mudança causal de máscara. Os mesmos dados já foram usados para selecionar o checkpoint e orientar desenvolvimento. Escolher o maior resultado entre onze variantes pode sobreajustar a validação; ainda é necessária confirmação independente.','',
        '## 5. Situação do percentual mínimo','',
        'Nenhuma variante alcançou simultaneamente 90% de Rank-1 e TAR no original. O mínimo global permanece **não determinado**. Esta rodada não atualiza a curva de oclusão nem autoriza transferir um ganho no original para um percentual de área tolerada.','',
        'A próxima melhoria deve considerar treinamento com a distribuição de máscaras automáticas e robustez a pequenas diferenças de recorte; para HDBIF, permanece importante revisar os limites da normalização polar. Um novo treinamento só deve usar treino e validação. Antes de anunciar mínimo ou ganho confirmado, precisa existir avaliação independente do conjunto usado para essas escolhas.','',
        '## 6. Verificação e preservação','',
        'Vinte e quatro testes automatizados passaram. O comparador HDBIF em lote foi conferido contra o escalar, incluindo sobreposição vazia; os controles de foto única reproduzem os escores das rodadas anteriores dentro da tolerância numérica. Os escores negativos válidos do encoder são preservados, e a sentinela de falha -2 é tratada separadamente.','',
        'A replicação neural permite diferença absoluta de até 0,000001 por arredondamento FP32 e alteração da dimensão da multiplicação matricial; o máximo observado está registrado no JSON de replicação. As decisões Rank-1, aceitação e validade devem ser idênticas às anteriores. A replicação HDBIF usa tolerância de 0,000000000001.','',
        '![Consultas e recortes automáticos com os três cadastros do candidato](exemplos_multicaptura.png).','',
        'Os exemplos são as primeiras consultas de quatro pessoas distintas na ordem do manifesto, sem seleção por acerto. As três fotos mostradas são do candidato encontrado, que pode ser incorreto. Aceitação genuína refere-se ao escore da identidade verdadeira; Rank-1 indica a posição do candidato correto.','',
        '- [Protocolo](../../PROTOCOLO_CADASTRO_MULTICAPTURA_2026-10-20.md).',
        '- [Registro anterior à execução](protocolo.json).',
        '- [Resultados completos](CONCLUIDO.json).',
        '- [Resumo CSV](resumo.csv).',
        '- [Comparações pareadas e análise secundária](comparacoes_pareadas.json).','']
    (OUT/'RELATORIO_CADASTRO.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Report, CSV, paired comparisons and baseline replication checked.')

if __name__=='__main__': main()
