# Continuação do desenvolvimento do reconhecedor — 20/10/2026

O escopo confirmado é UBIPr principal e uma foto por consulta. O cadastro mantém várias fotos do mesmo olho. Todos os números abaixo usam as mesmas 482 consultas de 16 pessoas e 32 olhos da validação, sem oclusão artificial adicional. São resultados exploratórios após uso repetido da validação; não são novos resultados de teste independente.

## Alterações executadas

Foi concluído um novo treino polar com 29 épocas, selecionado na época 21. Retirou-se o max-pooling inicial para preservar quatro vezes mais posições espaciais nas camadas seguintes. O lote foi reduzido de 64 para 32 por memória, portanto não é uma ablação isolada da arquitetura. Pesos iniciais ImageNet, seed e pré-processamento foram mantidos. O checkpoint anterior foi preservado.

Também foi ajustada uma transformação linear nos embeddings dos encoders anteriores, exclusivamente nas identidades de treino. A covariância intraolho recebeu regularização fixa de 0,1. Não houve busca de regularização nem pesos de fusão na validação. A fusão complementar usa RGB, polar e espacial com pesos iguais; a fusão do encoder denso usa os três componentes anteriores e o novo encoder com pesos de um quarto. Normalização por impostores e limiares continuam calculados na validação.

## Resultados

| Configuração | Rank-1 | TAR | FMR | Falhas de consulta |
|---|---:|---:|---:|---:|
| Fusão anterior RGB + polar + espacial | 79,88% | 68,05% | 0,99% | 4 |
| Métrica linear RGB | 67,43% | 59,54% | 0,99% | 4 |
| Métrica linear polar | 61,41% | 47,10% | 0,99% | 4 |
| Fusão com métricas lineares | 78,22% | 65,98% | 0,99% | 4 |
| Novo encoder polar denso | 61,62% | 46,68% | 0,99% | 4 |
| Fusão fixa de quatro componentes | 78,84% | 68,26% | 0,99% | 4 |

A transformação linear não superou simultaneamente as métricas da fusão anterior. Os resultados negativos foram preservados. A comparação da nova fusão com a anterior está em `CONCLUIDO.json`, com intervalos pareados por pessoa. São intervalos pontuais condicionados à galeria e aos limiares, sem correção pela seleção de checkpoint ou pelo desenvolvimento repetido.

## Critério e mínimo de área

O candidato mantido nesta comparação tem Rank-1 de 79.88% e TAR de 68.05%. Faltam 10.12 pp e 21.95 pp, respectivamente, para o critério de 90% em ambas. A escolha aqui é de desenvolvimento e não promove automaticamente um modelo para uso final.

O mínimo global de área permanece **não determinado**. Não foi executada nova curva de oclusão para esses candidatos. Não há percentual aprovado com ou sem oclusão adicional sob o critério original. O estudo de área deve reter também as consultas que falham, congelar a configuração e confirmar o desempenho em avaliação independente antes de anunciar um mínimo generalizável.

## Reprodutibilidade

- Protocolos e hashes registrados antes dos cálculos; todos os pesos anteriores mantidos.
- Checkpoint denso: `../encoder_polar_denso_2026-10-20/melhor_modelo.pt`; reconstruir com `carregar_encoder_polar.load`, pois o max-pooling não aparece nos pesos do state_dict.
- Histórico: `../encoder_polar_denso_2026-10-20/historico.csv`.
- Transformações e escores lineares: `../metrica_intra_val_2026-10-20`.
- Escores, contagens e comparação pareada da fusão: `CONCLUIDO.json` e `scores.npz`.
- Saídas temporárias foram copiadas para o projeto com conferência SHA-256; a criação de arquivos pelo shell na pasta do OneDrive falhou, mas a cópia pela API de arquivos funcionou.
