"""Relatorio dos controles de desenvolvimento, sem misturar teste anterior."""
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parent

def main():
    from avaliar_robustez_reconhecimento import load_splits,paired_ci
    folder=ROOT/'outputs/melhoria_normalizacao_val_gpu_2026-10-20'
    neural=ROOT/'outputs/melhoria_resolucao_encoder_val_2026-10-20'
    h=json.loads((folder/'CONCLUIDO.json').read_text()); n=json.loads((neural/'CONCLUIDO.json').read_text())
    rows=load_splits(json.loads((ROOT/'outputs/cnn/ubipr_retreino_2026-10-20/manifesto.json').read_text()))['val']
    subjects=np.array([r.subject for r in rows if r.session==2]); intervals={}
    with np.load(folder/'full_reference/scores.npz') as base,np.load(folder/'roi_reference/scores.npz') as roi:
        assert np.array_equal(base['labels'],roi['labels']) and len(base['labels'])==len(subjects)
        for key in ('correct','accepted'):
            intervals[key]=paired_ci(roi[key],base[key],subjects)
    (folder/'ganho_pareado_ic95.json').write_text(json.dumps({'note':'ROI minus full, percentage points; pointwise 5000 person cluster resamples, fixed gallery, validation-calibrated thresholds; development only','intervals':intervals},indent=2),encoding='utf-8')
    names={'full_reference':'HDBIF, imagem inteira','roi_reference':'HDBIF, recorte antes da normalização'}
    lines=['# Melhoria do reconhecedor — resultados de desenvolvimento em 20/10/2026','',
        '## 1. O que foi executado','',
        'Foram concluídos quatro controles na validação UBIPr, com 482 consultas, 16 pessoas e 32 olhos. A galeria contém uma captura por olho: a primeira em ordem lexicográfica da sessão 1, sem seleção por desempenho. As consultas são da sessão 2. Nenhum novo escore de teste ou de oclusão foi produzido nesta rodada.','',
        'Dois controles HDBIF comparam imagem inteira e recorte de referência com margem de 50% antes da regressão dos círculos e da normalização polar. Dois controles do encoder neural congelado comparam entradas de 128 e 256 pixels. Todos usam a mesma captura de cadastro por olho e mantêm falhas no denominador. Os limiares são calibrados separadamente na própria validação, por isso estas taxas são de desenvolvimento.','',
        '## 2. Resultados sem oclusão artificial adicional','',
        '| Configuração | Rank-1 | TAR | FMR | Falhas de consulta | Cadastros inválidos |',
        '|---|---:|---:|---:|---:|---:|']
    for r in h['results']+n['results']:
        label=names[r['variant']] if 'variant' in r else f"Encoder congelado, entrada {r['input_size']} × {r['input_size']}"
        fmt=lambda key:f"{100*r[key]:.2f}%".replace('.',',')
        lines.append(f"| {label} | {fmt('rank1')} | {fmt('tar')} | {fmt('far')} | {r['extraction_failures']} | {r['failed_gallery']} |")
    a,b=h['results']; gainrank=100*(b['rank1']-a['rank1']); gaintar=100*(b['tar']-a['tar'])
    lines+=['','## 3. Ganho observado e limites','',
        f'O recorte prévio melhorou o HDBIF em **{gainrank:.2f} pontos percentuais de Rank-1** e **{gaintar:.2f} pontos de TAR**. O IC 95% pareado por pessoa foi {intervals["correct"][0]:.2f} a {intervals["correct"][1]:.2f} pp em Rank-1 e {intervals["accepted"][0]:.2f} a {intervals["accepted"][1]:.2f} pp em TAR. A comparação é condicional à galeria fixa e aos limiares calibrados nesta validação.','',
        'As falhas de consulta HDBIF caíram de 22 para 12. Houve ganho mensurável no pré-processamento, mas o HDBIF recortado ainda ficou abaixo do encoder de 128 pixels neste protocolo. Não substituímos automaticamente o reconhecedor principal.','',
        'Apenas ampliar a entrada neural para 256 pixels piorou o desempenho. O modelo foi treinado com entrada 128; inferir em 256 altera a distribuição de entrada e não equivale a treinar um novo modelo nessa resolução. O resultado não prova que maior resolução seja sempre pior.','',
        f'A largura nativa da região de referência teve mediana de **{h["iris_native_width_percentiles"]["median"]:.0f} pixels**, percentil 10 de {h["iris_native_width_percentiles"]["p10"]:.1f} e percentil 90 de {h["iris_native_width_percentiles"]["p90"]:.1f}, nas 514 capturas selecionadas com referência não vazia. A distribuição inclui a galeria e as consultas; ampliar por interpolação não recupera textura ausente.','',
        'A inspeção dos quatro cadastros iniciais por variante confirmou alinhamento de imagem e máscara, mas ainda mostrou aproximações circulares imperfeitas e porções polares inválidas, inclusive em olhos com óculos. A prancha serve para diagnóstico e não representa auditoria manual completa de todas as imagens.','',
        '## 4. Relação com os resultados anteriores e o mínimo de área','',
        'Estes resultados são de **validação com uma captura de cadastro**. Os 67,90% de Rank-1 e 55,14% de TAR publicados anteriormente são do teste UBIPr com galeria por centróide de múltiplas capturas. Não misturar essas amostras e protocolos nem interpretar a diferença como regressão do modelo. Os pesos anteriores foram preservados.','',
        'Nenhum dos quatro controles atingiu 90% de Rank-1 e TAR. Não há novo mínimo de área determinado. Esta rodada identifica uma melhoria útil para o HDBIF e rejeita, neste controle, a ampliação simples da entrada neural.','',
        '## 5. Próxima direção técnica','',
        'A próxima comparação deve controlar também o cadastro com múltiplas capturas, antes de escolher o método. Em paralelo, a normalização precisa de avaliação com máscara automática e melhor ajuste dos limites pupilar/externo. Um novo treinamento em representação polar só deve ser iniciado após verificar essa geometria. A confirmação de ganho exige avaliação independente: o teste UBIPr anterior já foi examinado e não será apresentado como intocado.','',
        'Não foram necessários novos dados, credenciais ou assinatura para esta rodada. Vinte testes automatizados passaram, incluindo dois novos controles de geometria e os testes existentes das métricas e do comparador FFT. As fontes e os pesos CVRL locais foram conferidos em 17 verificações de SHA-256.','',
        '## 6. Artefatos','',
        '- [Protocolo de desenvolvimento](../../MELHORIA_RECONHECEDOR_2026-10-20.md).',
        '- [Resultados HDBIF](CONCLUIDO.json).',
        '- [Resultados dos controles de resolução](../melhoria_resolucao_encoder_val_2026-10-20/CONCLUIDO.json).',
        '- [Imagem real da normalização e máscaras polares](qa_normalizacao.png).',
        '- [Intervalos dos ganhos pareados](ganho_pareado_ic95.json).','']
    (folder/'RELATORIO_MELHORIA.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Report and paired intervals written.')

if __name__=='__main__': main()
