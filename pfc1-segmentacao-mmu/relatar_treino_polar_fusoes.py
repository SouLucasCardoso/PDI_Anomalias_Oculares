"""Sintese da rodada polar e das fusoes, distinguindo desenvolvimento de teste."""
from pathlib import Path
import csv,json
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs/fusao_espacial_val_2026-10-20'

def main():
    from avaliar_robustez_reconhecimento import load_splits,paired_ci
    trained=ROOT/'outputs/encoder_polar_2026-10-20';training=json.loads((trained/'CONCLUIDO.json').read_text());assert not training['technical_smoke']
    with (trained/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    polar=next(r for r in history if int(r['epoch'])==training['best_epoch'])
    baseline=json.loads((ROOT/'outputs/identidade_automatica_2026-10-20/CONCLUIDO.json').read_text())['baseline']
    phase=json.loads((ROOT/'outputs/loggabor_polar_val_2026-10-20/CONCLUIDO.json').read_text())['results'][-1]
    spatial=json.loads((ROOT/'outputs/espacial_polar_val_2026-10-20/CONCLUIDO.json').read_text())['results'][0]
    fusion2=json.loads((ROOT/'outputs/fusao_polar_rgb_val_2026-10-20/CONCLUIDO.json').read_text())['metrics']
    fusion3=json.loads((OUT/'CONCLUIDO.json').read_text())['metrics']
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val'];subjects=np.array([r.subject for r in rows if r.session==2])
    with np.load(ROOT/'outputs/identidade_automatica_2026-10-20/scores_baseline.npz') as z:base={k:z[k] for k in z.files}
    comparisons=[]
    for name,path in [('fusion2',ROOT/'outputs/fusao_polar_rgb_val_2026-10-20/scores.npz'),('fusion3',OUT/'scores.npz')]:
        with np.load(path) as z:current={k:z[k] for k in z.files}
        np.testing.assert_array_equal(base['labels'],current['labels']);assert current['scores'].shape==(482,32)
        assert np.isfinite(current['scores']).all() and not current['accepted'][~current['valid']].any()
        comparisons.append({'variant':name,'gain_pp':{key:float(100*(current[field].mean()-base[field].mean())) for key,field in [('rank1','correct'),('tar','accepted')]},
            'gain_ci95_pp':{key:paired_ci(current[field],base[field],subjects) for key,field in [('rank1','correct'),('tar','accepted')]}})
    report={'scope':'Development only; fixed weights, standardization/threshold on repeatedly used validation; pointwise paired person-cluster CI not selection-corrected',
        'comparisons':comparisons,'remaining_to90_pp':{'rank1':90-100*fusion3['rank1'],'tar':90-100*fusion3['tar']},
        'required_count_at90_of482':434,'current_correct_count':round(482*fusion3['rank1']),'current_genuine_accept_count':round(482*fusion3['tar'])}
    (OUT/'comparacao_pareada.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    summary=[('Encoder RGB anterior, top-3',baseline),('Encoder polar treinado, top-3',polar),('Fase Log-Gabor, top-3',phase),('Descritor espacial, protótipo',spatial),('Fusão RGB + polar, pesos iguais',fusion2),('Fusão RGB + polar + espacial, pesos iguais',fusion3)]
    lines=['# Avanço: treinamento polar e fusão de representações — 20/10/2026','',
        '## 1. Execuções concluídas','',
        f'Foi treinado um novo encoder de identidade em textura polar automática de 64 × 512 pixels. Foram concluídas {training["epochs_completed"]} épocas, com checkpoint selecionado na época {training["best_epoch"]}. O treino usou 183 pessoas e 366 identidades oculares; a validação manteve 16 pessoas, 32 olhos, 480 imagens de cadastro e 482 consultas. Os protocolos e hashes foram registrados antes de cada execução.','',
        'A representação usa U-Net congelada, aproximação elíptica da máscara prevista, contraste local CLAHE, remoção da região externa com cinza neutro e deslocamentos circulares no treino. O encoder ResNet18 foi inicializado em ImageNet. A referência manual não corrige os recortes. Essa mudança combina geometria, intensidade, proporção de entrada, representação e treinamento; não isola o efeito de um único componente.','',
        'Também foram concluídos um controle clássico de fase, dois controles de correspondência espacial e duas fusões de escores com pesos fixos. Nenhum novo escore de teste ou de oclusão foi produzido.','',
        '## 2. Resultados na mesma validação, sem oclusão adicional','',
        '| Método | Rank-1 | TAR | FMR | Falhas de consulta |','|---|---:|---:|---:|---:|']
    for name,r in summary:
        fmt=lambda key:f"{100*float(r[key]):.2f}%".replace('.',',')
        lines.append(f"| {name} | {fmt('rank1')} | {fmt('tar')} | {fmt('far')} | {r['extraction_failures']} |")
    lines+=['','A fusão de duas vias padroniza cada escore pela média e desvio dos impostores válidos e combina RGB e polar com pesos 0,5/0,5. A de três vias inclui o descritor espacial com pesos iguais de um terço. Não houve busca de pesos. Cada configuração recalibra seu limiar de validação para FMR empírica de até 1%. Os componentes espaciais e polares são correlacionados; não são evidências independentes.','',
        'O controle espacial sem deslocamento e com busca de até duas colunas produziu as mesmas métricas reportadas. A camada intermediária é comparada por local, após subtrair resposta a uma entrada uniforme e formar protótipos por olho. O Log-Gabor é um baseline local, não uma implementação oficial do OSIRIS. Sua máscara é reconstruída conservadoramente dos pixels diferentes do sentinela 127, com erosão e suporte mínimo; isso limita a interpretação de sua comparação.','',
        '## 3. Ganho e incerteza','',
        'A fusão de três vias aumentou Rank-1 de 66,80% para **79,88%** e TAR de 59,34% para **68,05%**, no mesmo conjunto. A fusão de duas vias já tinha atingido 76,35% e 67,63%; a inclusão espacial acrescentou 17 identificações corretas e apenas duas aceitações genuínas. Não tratar essa diferença pequena de TAR como superioridade já confirmada.','']
    for entry in comparisons:
        for key in ('rank1','tar'):
            lo,hi=entry['gain_ci95_pp'][key];lines.append(f'- {entry["variant"]}, {key.upper()}: ganho de {entry["gain_pp"][key]:.2f} pp; IC 95% pontual por pessoa {lo:.2f} a {hi:.2f} pp.')
    lines+=['','Os intervalos usam 5.000 reamostragens pareadas de pessoas, com galeria e limiares fixos. Não corrigem a seleção do checkpoint, o uso repetido da validação nem as múltiplas hipóteses investigadas. As fusões são candidatos de desenvolvimento: ainda não substituem um resultado de teste independente.','',
        '## 4. Distância até o mínimo aceitável','',
        'O critério permanece **Rank-1 e TAR de pelo menos 90%**, com limiar calibrado para FMR empírica de até 1% na validação. O mínimo de área permanece **não determinado**. No melhor resultado pontual desta rodada, faltam **10,12 pp de Rank-1 e 21,95 pp de TAR**. Em 482 consultas, seriam necessários 434 acertos/aceitações em cada métrica; há 385 identificações corretas e 328 aceitações genuínas, faltando respectivamente 49 e 106. Essa distância não prevê quantas épocas ou amostras resolveriam o problema.','',
        'O ensaio de oclusão não foi reexecutado para anunciar um mínimo com um sistema que ainda falha no critério original. Mais níveis de oclusão não corrigem essa deficiência. As decisões de imagem única versus sequência e de base principal devem ser explícitas: um resultado em outra condição de captura não pode substituir silenciosamente a pergunta original.','',
        '## 5. Qualidade e pesquisa de alternativas','',
        'Um diagnóstico posterior, sem remover consultas das métricas principais, mostrou 73,73% de Rank-1 e 68,64% de TAR no quartil de maior nitidez do encoder anterior (118 consultas, 15 pessoas). A associação não isola causas de captura nem justifica selecionar esse grupo como novo teste. Mesmo essa análise não atingiu o critério de 90%.','',
        'A pesquisa localizou o VIS-IrisFormer, cujo README descreve treinamento em UBIRIS.v2. Como o UBIPr deriva dessa base, existe risco de sobreposição de identidades ou imagens. O checkpoint não foi usado para anunciar confirmação independente. A fonte e esse limite estão documentados no protocolo.','',
        '## 6. Verificações e artefatos','',
        'Os 37 testes automatizados passaram, incluindo circularidade do deslocamento de textura, fase, comparação normalizada, correspondência espacial e retenção de falhas. O novo checkpoint e os pesos anteriores foram preservados.','',
        '- [Protocolo e fontes](../../PROTOCOLO_TREINO_POLAR_2026-10-20.md).',
        '- [Histórico do treinamento](../encoder_polar_2026-10-20/historico.csv).',
        '- [Conclusão do treinamento](../encoder_polar_2026-10-20/CONCLUIDO.json).',
        '- [Fusão de duas vias](../fusao_polar_rgb_val_2026-10-20/CONCLUIDO.json).',
        '- [Fusão de três vias](CONCLUIDO.json).',
        '- [Comparações e distância até o critério](comparacao_pareada.json).',
        '- [Diagnóstico de qualidade posterior](../encoder_polar_2026-10-20/diagnostico_qualidade_poshoc.json).','',
        '![Primeiras oito entradas polares válidas de treino, sem seleção por desempenho](../encoder_polar_2026-10-20/qa_textura_polar.png)','']
    (OUT/'RELATORIO_AVANCO_POLAR_FUSAO.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
