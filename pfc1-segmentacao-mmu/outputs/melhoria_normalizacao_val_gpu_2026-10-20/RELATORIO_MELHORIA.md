# Melhoria do reconhecedor — resultados de desenvolvimento em 20/10/2026

## 1. O que foi executado

Foram concluídos quatro controles na validação UBIPr, com 482 consultas, 16 pessoas e 32 olhos. A galeria contém uma captura por olho: a primeira em ordem lexicográfica da sessão 1, sem seleção por desempenho. As consultas são da sessão 2. Nenhum novo escore de teste ou de oclusão foi produzido nesta rodada.

Dois controles HDBIF comparam imagem inteira e recorte de referência com margem de 50% antes da regressão dos círculos e da normalização polar. Dois controles do encoder neural congelado comparam entradas de 128 e 256 pixels. Todos usam a mesma captura de cadastro por olho e mantêm falhas no denominador. Os limiares são calibrados separadamente na própria validação, por isso estas taxas são de desenvolvimento.

## 2. Resultados sem oclusão artificial adicional

| Configuração | Rank-1 | TAR | FMR | Falhas de consulta | Cadastros inválidos |
|---|---:|---:|---:|---:|---:|
| HDBIF, imagem inteira | 28,84% | 11,62% | 0,89% | 22 | 2 |
| HDBIF, recorte antes da normalização | 42,12% | 24,69% | 0,94% | 12 | 1 |
| Encoder congelado, entrada 128 × 128 | 48,76% | 38,38% | 0,94% | 10 | 1 |
| Encoder congelado, entrada 256 × 256 | 29,67% | 15,15% | 0,94% | 10 | 1 |

## 3. Ganho observado e limites

O recorte prévio melhorou o HDBIF em **13.28 pontos percentuais de Rank-1** e **13.07 pontos de TAR**. O IC 95% pareado por pessoa foi 6.88 a 19.71 pp em Rank-1 e 5.60 a 21.25 pp em TAR. A comparação é condicional à galeria fixa e aos limiares calibrados nesta validação.

As falhas de consulta HDBIF caíram de 22 para 12. Houve ganho mensurável no pré-processamento, mas o HDBIF recortado ainda ficou abaixo do encoder de 128 pixels neste protocolo. Não substituímos automaticamente o reconhecedor principal.

Apenas ampliar a entrada neural para 256 pixels piorou o desempenho. O modelo foi treinado com entrada 128; inferir em 256 altera a distribuição de entrada e não equivale a treinar um novo modelo nessa resolução. O resultado não prova que maior resolução seja sempre pior.

A largura nativa da região de referência teve mediana de **123 pixels**, percentil 10 de 85.2 e percentil 90 de 184.8, nas 514 capturas selecionadas com referência não vazia. A distribuição inclui a galeria e as consultas; ampliar por interpolação não recupera textura ausente.

A inspeção dos quatro cadastros iniciais por variante confirmou alinhamento de imagem e máscara, mas ainda mostrou aproximações circulares imperfeitas e porções polares inválidas, inclusive em olhos com óculos. A prancha serve para diagnóstico e não representa auditoria manual completa de todas as imagens.

## 4. Relação com os resultados anteriores e o mínimo de área

Estes resultados são de **validação com uma captura de cadastro**. Os 67,90% de Rank-1 e 55,14% de TAR publicados anteriormente são do teste UBIPr com galeria por centróide de múltiplas capturas. Não misturar essas amostras e protocolos nem interpretar a diferença como regressão do modelo. Os pesos anteriores foram preservados.

Nenhum dos quatro controles atingiu 90% de Rank-1 e TAR. Não há novo mínimo de área determinado. Esta rodada identifica uma melhoria útil para o HDBIF e rejeita, neste controle, a ampliação simples da entrada neural.

## 5. Próxima direção técnica

A próxima comparação deve controlar também o cadastro com múltiplas capturas, antes de escolher o método. Em paralelo, a normalização precisa de avaliação com máscara automática e melhor ajuste dos limites pupilar/externo. Um novo treinamento em representação polar só deve ser iniciado após verificar essa geometria. A confirmação de ganho exige avaliação independente: o teste UBIPr anterior já foi examinado e não será apresentado como intocado.

Não foram necessários novos dados, credenciais ou assinatura para esta rodada. Vinte testes automatizados passaram, incluindo dois novos controles de geometria e os testes existentes das métricas e do comparador FFT. As fontes e os pesos CVRL locais foram conferidos em 17 verificações de SHA-256.

## 6. Artefatos

- [Protocolo de desenvolvimento](../../MELHORIA_RECONHECEDOR_2026-10-20.md).
- [Resultados HDBIF](CONCLUIDO.json).
- [Resultados dos controles de resolução](../melhoria_resolucao_encoder_val_2026-10-20/CONCLUIDO.json).
- [Imagem real da normalização e máscaras polares](qa_normalizacao.png).
- [Intervalos dos ganhos pareados](ganho_pareado_ic95.json).
