# Relatório de avanço — consolidação para orientação

**Data:** 27 de outubro de 2026  
**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Período consolidado:** 20 a 24/10, com conferência documental e novas amostras visuais em 27/10  
**Entrega prevista do artigo:** 09/11/2026 — 13 dias após esta consolidação.

## 1. Situação atual

O projeto dispõe de um pipeline de segmentação automática, recortes RGB e normalização polar, reconhecimento por fusão de descritores e avaliação de perda simulada de área. A referência principal permanece em **444/486 identificações corretas (91,36%)**, sem oclusão artificial adicional. As tentativas posteriores não superaram conjuntamente os critérios estabelecidos e não substituíram essa referência.

A pergunta sobre área já tem uma resposta experimental limitada: na grade irregular avaliada, a menor área nominal aprovada foi **99,5% na oclusão superior e 99% na inferior**. Isso não estabelece um mínimo global válido para qualquer região, pessoa ou anomalia clínica. O resultado caracteriza a sensibilidade deste pipeline às intervenções estudadas.

## 2. Avanço em relação ao início da semana passada

Em 20/10, o extrator treinado com recortes de referência atingia **67,90% de Rank-1 (330/486)**. A referência atual atinge **91,36% (444/486)**: diferença descritiva de **23,46 pontos percentuais e 114 identificações corretas**. A comparação não isola um único fator: mudaram descritores, fusão, pré-processamento e o protocolo passou a usar o lado informado, com 16 candidatos do mesmo lado. A validação e o teste já foram examinados anteriormente; não é confirmação independente.

Desde o congelamento do resultado de 91,36%, houve avanço no diagnóstico, na delimitação da área aprovada e na rastreabilidade, mas **não houve ganho aprovado de reconhecimento**. Foram estudados localização da pupila, geometria elíptica, adaptação do descritor polar, penalização de impostores, normalização dos escores e diversidade das oclusões no treinamento. Os controles evitaram promover ganhos locais que não se sustentaram nos critérios completos.

## 3. Resultados da referência congelada

Todas as condições abaixo mantêm 486 consultas, uma foto por consulta, lado informado, cadastro fixo da sessão 1, consulta na sessão 2 e o mesmo limiar. Rank-1 é identificação do primeiro candidato; TAR é aceitação genuína; FMR é falsa correspondência entre olhos diferentes. O critério adotado exige separadamente Rank-1 e TAR de pelo menos 90%, com FMR de até 1%.

| Condição | Área nominal preservada | Rank-1 | TAR | FMR | Critérios |
|---|---:|---:|---:|---:|---|
| Original, sem perda artificial | 100% | 91,36% | 92,39% | 0,8779% | Aprovados |
| Perda superior de 0,5% | 99,5% | 91,15% | 92,39% | 0,8916% | Aprovados |
| Perda superior de 1% | 99% | 89,92% | 92,39% | 0,88% | Reprovados |
| Perda inferior de 1% | 99% | 90,95% | 91,36% | 0,93% | Aprovados |
| Perda inferior de 1,5% | 98,5% | 89,09% | 88,89% | 1,0151% | Reprovados |
| Perda superior de 10% | 90% | 82,30% | 84,98% | 1,69% | Reprovados |
| Perda inferior de 10% | 90% | 58,23% | 60,29% | 2,61% | Reprovados |

Os números percentuais arredondados não substituem as contagens e escores preservados. Não foi avaliada perda inferior de 0,5%; portanto, 99,5% não é um nível aprovado em ambas as orientações. Entre os níveis coincidentes avaliados, somente a condição original passou nas duas. As seis consultas com referência vazia permaneceram inalteradas e no denominador; duas consultas do original tiveram falha de extração. A área nominal se refere à região visível anotada, não à anatomia inteira.

Identificar corretamente e aceitar são eventos distintos: na condição original, **436/486 (89,71%)** satisfizeram ambos simultaneamente. A aprovação pelos critérios separados não significa aprovação de um critério conjunto de 90%.

## 4. O que os últimos testes acrescentaram

- **Segmentação e geometria:** foi demonstrado que maior sobreposição da máscara com a anotação não garante maior reconhecimento. O diagnóstico com geometria da foto limpa recuperou desempenho sob oclusão, mas usa informação indisponível na captura de uma única foto ocluída e não é solução operacional.
- **Calibração:** um limiar global estimado nas perturbações internas controlou a FMR no monitor, mas, na validação limpa de 482 consultas, apresentou Rank-1 de 90,46%, TAR de apenas 64,32% e FMR de 0,2075%. A rejeição de genuínos impediu aprovação.
- **Troca isolada do polar:** preservando os parâmetros originais da fusão, a validação limpa ficou em 89,83% de Rank-1, 90,25% de TAR e 1,0235% de FMR. O candidato foi rejeitado antes de abrir novas oclusões ou teste.
- **Diversidade de treinamento:** foram preparadas 3.222 intervenções de 1% a 20% sobre 1.611 consultas de ajuste e concluídas oito épocas. No monitor reutilizado de 480 consultas, as perdas superior/inferior de 10% resultaram em Rank-1 de 82,92%/65,63% e FMR de 1,4028%/1,2917%. Não houve melhoria conjunta sobre o controle. Dez vistas sem extração útil ainda receberam perda de identidade; esse tratamento é uma limitação identificada e ainda não corrigida nesta consolidação.
- **Auditoria e recuperação:** resultados, decisões e checkpoints dos pilotos foram preservados com hashes e restauração conferida. A gravação local não comprova sincronização na nuvem.

O monitor de treino reutilizado não é comparável diretamente ao teste principal. Nenhum percentual interno próximo de 99% substitui os 91,36% da referência. Em 27/10, esta etapa produziu consolidação e visualização; não foi executado novo treinamento nem uma nova medição de reconhecimento.

## 5. Novas amostras dos recortes

![Recortes reais e faixas polares produzidos em 27/10](C:/Users/lucaz/AppData/Local/Temp/pfc-amostras-20261027/AMOSTRAS_RECORTES_IRIS_2026-10-27.png)

A gravação direta do PNG na pasta do OneDrive falhou. O arquivo pronto está em `%TEMP%/pfc-amostras-20261027/AMOSTRAS_RECORTES_IRIS_2026-10-27.png`. Uma cópia recuperável dos mesmos bytes foi preservada junto deste relatório como `AMOSTRAS_RECORTES_IRIS_2026-10-27.png.b64`, acompanhada do JSON legível. SHA-256 do PNG: `44fa98c4670ac882c9699e1736ce0a8d15637dd1d570c50a277f9750b55f5b68`. Nenhuma proteção do Windows foi alterada. O PNG foi inspecionado visualmente; títulos, quatro linhas e rodapés estão legíveis.

A prancha mostra quatro outras pessoas da validação: foram ignoradas as primeiras quatro pessoas elegíveis usadas na prancha anterior e selecionadas as quatro seguintes pela ordem do manifesto, sem consultar escores de reconhecimento. Cada linha contém foto original, máscara automática em verde, entradas RGB de 128 e 224 pixels e texturas polares CLAHE e canal vermelho. O segmentador é o da referência preservada; as imagens não representam um segmentador novo nem demonstram identificação correta. O JSON acompanhante registra os arquivos de origem, a seleção e os hashes.

## 6. O que falta e prioridade até a entrega

O pipeline e os resultados necessários para um estudo de sensibilidade já existem. Falta obter evidência de robustez suficiente para sustentar uma redução expressiva da área necessária; as novas tentativas ainda não entregaram isso. A correção do tratamento de vistas inválidas pode ser testada como hipótese controlada, sem prometer ganho e sem ajustar critérios aos casos que falharam. Devem ser preservadas a definição da FMR por pares e a separação entre calibração e avaliação.

É necessário fechar no artigo a interpretação da grade irregular, a incerteza, a exposição anterior dos conjuntos e a distinção entre oclusões artificiais e anomalias reais. Não há dados clínicos suficientes nesta evidência para quantificar diretamente o impacto de doenças. Não é possível atribuir uma porcentagem confiável de conclusão científica ao objetivo de um mínimo universal; o resultado atual é uma fronteira experimental condicionada ao protocolo.

Com 13 dias até a entrega, a prioridade é uma hipótese adicional limitada e bem controlada, acompanhada da consolidação do artigo, figuras e tabelas. O estudo não deve depender de uma promessa de atingir uma área menor antes de 09/11.

## 7. Evidências

- [Relatório de 20/10](RELATORIO_AVANCO_2026-10-20.md): reconstrução, segmentação e referência inicial de 67,90%.
- [Relatório de 21/10](RELATORIO_AVANCO_2026-10-21.md): congelamento e teste de 91,36%.
- [Relatório de 23/10](RELATORIO_AVANCO_2026-10-23.md): refinamento da fronteira para 99,5%/99%.
- [Rodada de refinamento](../pfc1-segmentacao-mmu/outputs/fronteira_meio_ponto_2026-10-23/CONCLUIDO.json): métricas dos dois pontos adicionais.
- [Relatório de 24/10](RELATORIO_AVANCO_2026-10-24.md): candidatos rejeitados e auditorias.
- [Diversidade de oclusão](../pfc1-segmentacao-mmu/DIVERSIDADE_OCLUSAO_2026-10-24.md): método, resultados e limitações do último piloto.

