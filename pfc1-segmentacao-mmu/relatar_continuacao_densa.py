"""Consolida controles novos sem trocar desenvolvimento por teste independente."""
from pathlib import Path
import argparse,csv,json

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-root',type=Path,required=True);args=parser.parse_args()
    trained=args.output_root/'encoder_polar_denso_2026-10-20'
    completion=json.loads((trained/'CONCLUIDO.json').read_text())
    with (trained/'historico.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    best=next(r for r in history if int(r['epoch'])==completion['best_epoch'])
    linear=json.loads((args.output_root/'metrica_intra_val_2026-10-20/CONCLUIDO.json').read_text())
    fusion_dir=args.output_root/'fusao_densa_val_2026-10-20'
    fusion=json.loads((fusion_dir/'CONCLUIDO.json').read_text())
    previous=json.loads((ROOT/'outputs/fusao_espacial_val_2026-10-20/CONCLUIDO.json').read_text())['metrics']
    results=[('Fusão anterior RGB + polar + espacial',previous),('Métrica linear RGB',linear['results'][0]),
        ('Métrica linear polar',linear['results'][1]),('Fusão com métricas lineares',linear['results'][2]),
        ('Novo encoder polar denso',best),('Fusão fixa de quatro componentes',fusion['metrics'])]
    lines=['# Continuação do desenvolvimento do reconhecedor — 20/10/2026','',
        'O escopo confirmado é UBIPr principal e uma foto por consulta. O cadastro mantém várias fotos do mesmo olho. Todos os números abaixo usam as mesmas 482 consultas de 16 pessoas e 32 olhos da validação, sem oclusão artificial adicional. São resultados exploratórios após uso repetido da validação; não são novos resultados de teste independente.','',
        '## Alterações executadas','',
        f'Foi concluído um novo treino polar com {completion["epochs_completed"]} épocas, selecionado na época {completion["best_epoch"]}. Retirou-se o max-pooling inicial para preservar quatro vezes mais posições espaciais nas camadas seguintes. O lote foi reduzido de 64 para 32 por memória, portanto não é uma ablação isolada da arquitetura. Pesos iniciais ImageNet, seed e pré-processamento foram mantidos. O checkpoint anterior foi preservado.','',
        'Também foi ajustada uma transformação linear nos embeddings dos encoders anteriores, exclusivamente nas identidades de treino. A covariância intraolho recebeu regularização fixa de 0,1. Não houve busca de regularização nem pesos de fusão na validação. A fusão complementar usa RGB, polar e espacial com pesos iguais; a fusão do encoder denso usa os três componentes anteriores e o novo encoder com pesos de um quarto. Normalização por impostores e limiares continuam calculados na validação.','',
        '## Resultados','', '| Configuração | Rank-1 | TAR | FMR | Falhas de consulta |', '|---|---:|---:|---:|---:|']
    for name,r in results:
        fmt=lambda k:f'{100*float(r[k]):.2f}%'.replace('.',',')
        lines.append(f'| {name} | {fmt("rank1")} | {fmt("tar")} | {fmt("far")} | {r["extraction_failures"]} |')
    new=fusion['metrics'];improved=new['rank1']>=previous['rank1'] and new['tar']>previous['tar']
    chosen=new if improved else previous
    lines+=['','A transformação linear não superou simultaneamente as métricas da fusão anterior. Os resultados negativos foram preservados. A comparação da nova fusão com a anterior está em `CONCLUIDO.json`, com intervalos pareados por pessoa. São intervalos pontuais condicionados à galeria e aos limiares, sem correção pela seleção de checkpoint ou pelo desenvolvimento repetido.','',
        '## Critério e mínimo de área','',
        f'O candidato mantido nesta comparação tem Rank-1 de {100*chosen["rank1"]:.2f}% e TAR de {100*chosen["tar"]:.2f}%. Faltam {max(0,90-100*chosen["rank1"]):.2f} pp e {max(0,90-100*chosen["tar"]):.2f} pp, respectivamente, para o critério de 90% em ambas. A escolha aqui é de desenvolvimento e não promove automaticamente um modelo para uso final.', '',
        'O mínimo global de área permanece **não determinado**. Não foi executada nova curva de oclusão para esses candidatos. Não há percentual aprovado com ou sem oclusão adicional sob o critério original. O estudo de área deve reter também as consultas que falham, congelar a configuração e confirmar o desempenho em avaliação independente antes de anunciar um mínimo generalizável.','',
        '## Reprodutibilidade','',
        '- Protocolos e hashes registrados antes dos cálculos; todos os pesos anteriores mantidos.',
        '- Checkpoint denso: `../encoder_polar_denso_2026-10-20/melhor_modelo.pt`; reconstruir com `carregar_encoder_polar.load`, pois o max-pooling não aparece nos pesos do state_dict.',
        '- Histórico: `../encoder_polar_denso_2026-10-20/historico.csv`.',
        '- Transformações e escores lineares: `../metrica_intra_val_2026-10-20`.',
        '- Escores, contagens e comparação pareada da fusão: `CONCLUIDO.json` e `scores.npz`.',
        '- Saídas temporárias foram copiadas para o projeto com conferência SHA-256; a criação de arquivos pelo shell na pasta do OneDrive falhou, mas a cópia pela API de arquivos funcionou.','']
    (fusion_dir/'RELATORIO_CONTINUACAO.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'dense_training':completion,'new_fusion':new,'maintained_candidate':chosen,'minimum_area':None},indent=2))

if __name__=='__main__':main()
