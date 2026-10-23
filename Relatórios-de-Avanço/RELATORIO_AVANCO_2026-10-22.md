# Relatório de avanço — diagnóstico dos recortes e da normalização

**Data:** 22 de outubro de 2026
**Projeto — foco atual:** Influência da área preservada da íris no reconhecimento de identidade
**Acadêmico:** Lucas Cardoso Rodrigues
**Orientador:** Rodrigo Ramos Silva
**Entrega prevista do artigo:** 9 de novembro de 2026

## 1. Objetivo da etapa

Investigar os erros restantes antes de realizar outro treinamento. Foi executada uma análise descritiva da resolução nativa dos recortes, da concordância da segmentação com as anotações e da geometria usada na normalização polar. Nenhum modelo ou limiar foi ajustado, nenhuma consulta foi excluída e nenhuma imagem de teste recebeu nova inferência.

## 2. Dados e verificações

Foram mantidas as 482 consultas da validação UBIPr, de 16 pessoas, com uma foto por consulta e lado informado. O reconhecedor congelado mantém 434 acertos, Rank-1 de 90,04%, TAR de 90,66% e FMR de 0,98%. As quatro falhas de extração continuam no denominador.

A U-Net congelada foi novamente executada nas fotos originais. Todos os recortes RGB e todas as faixas polares foram reproduzidos com igualdade exata em relação às entradas previamente usadas pelo candidato. As anotações foram usadas somente para diagnosticar a segmentação. Dez consultas têm referência de íris vazia: o Dice foi registrado como indefinido, sem atribuir nota perfeita, e todas permaneceram na análise.

## 3. Relação entre segmentação e identificação

| Dice da íris versus anotação | Consultas | Identificações corretas | Rank-1 |
|---|---:|---:|---:|
| Menor que 0,80 | 44 | 37 | 84,09% |
| De 0,80 a menos de 0,90 | 57 | 45 | 78,95% |
| De 0,90 a menos de 0,95 | 173 | 155 | 89,60% |
| De 0,95 a 1,00 | 198 | 193 | 97,47% |
| Referência indefinida | 10 | 4 | 40,00% |
| **Todas as consultas** | **482** | **434** | **90,04%** |

Dos 48 erros, 37 ocorreram com Dice abaixo de 0,95, cinco com Dice de pelo menos 0,95 e seis com referência indefinida. A associação não prova causalidade: condições da foto, características do participante e geometria podem afetar ambas as medidas. O Dice depende de anotação e não constitui um filtro disponível na captura. Os 97,47% de um subgrupo NÃO são um novo resultado global do reconhecedor, nem demonstram aprovação dos critérios completos nesse subgrupo.

## 4. Geometria da pupila e tamanho nativo

| Origem da geometria da pupila | Consultas | Acertos | Rank-1 |
|---|---:|---:|---:|
| Maior buraco interno da máscara | 439 | 406 | 92,48% |
| Alternativa geométrica concêntrica | 39 | 28 | 71,79% |
| Geometria indefinida | 4 | 0 | 0,00% |

A alternativa geométrica responde por 11 dos 48 erros. Mesmo restringindo a descrição às referências não vazias, ela tem 24 acertos em 34 consultas (70,59%). Isso sugere investigar localização da pupila e normalização, sem atribuir a elas todos os erros. O campo legado `circle_regressor_fallback` representa aqui um círculo concêntrico calculado da caixa da máscara, não a saída de um regressor treinado.

O menor lado da caixa da máscara predita foi agrupado em intervalos fixados antes do cálculo dos resultados: menos de 64 pixels, 64–95, 96–127 e pelo menos 128. Os respectivos Rank-1 limpos foram 88,80%, 92,20%, 90,91% e 89,80%. Não apareceu uma relação monotônica simples que justifique escolher uma resolução mínima a partir desta rodada. A caixa da região visível segmentada não equivale ao diâmetro anatômico completo da íris.

Sob oclusão inferior artificial de 10%, o grupo com menos de 64 pixels teve Rank-1 de 48,80%, contra aproximadamente 64–66% nos demais grupos. Essas associações são exploratórias e confundidas por pessoa, aquisição e segmentação; não foram usadas para remover consultas ou escolher um limiar.

## 5. Resultados preservados e próximo desenvolvimento

O resultado anterior de teste permanece 91,36% de Rank-1 sem oclusão artificial, com TAR de 92,39% e FMR de 0,88%. As fronteiras nominais anteriormente aprovadas na grade explorada continuam em 100% de aproveitamento para oclusão superior e 99% para inferior. Não são mínimos anatômicos ou clínicos universais. Esta etapa não mudou esses números.

A análise direciona a próxima hipótese para localização da pupila e estabilidade da normalização, preservando controles que separem mudança de geometria, segmentação e descritor. No diagnóstico inicial, a hipótese ainda não havia sido treinada; a continuação está registrada na seção 7. Não há justificativa para prometer que corrigir a pupila recuperará todos os erros ou atingirá um mínimo global de área.

## 6. Arquivos produzidos

- [Código do diagnóstico](../pfc1-segmentacao-mmu/diagnosticar_resolucao_geometria.py).
- [Resultados completos e protocolo](../pfc1-segmentacao-mmu/outputs/diagnostico_resolucao_geometria_val_2026-10-22/CONCLUIDO.json).
- [Métricas por consulta](../pfc1-segmentacao-mmu/outputs/diagnostico_resolucao_geometria_val_2026-10-22/consultas.csv).
- [Grupos e transições sob oclusão](../pfc1-segmentacao-mmu/outputs/diagnostico_resolucao_geometria_val_2026-10-22/grupos.csv).
- [Imagem com fotos e recortes reais](../pfc1-segmentacao-mmu/outputs/diagnostico_resolucao_geometria_val_2026-10-22/amostras_recortes_diagnostico.png).

A imagem apresenta os primeiros dois erros e primeiros dois acertos por ordem de arquivo, com pessoas distintas dentro de cada grupo. Não houve seleção por nota, resolução ou aparência. Os exemplos são ilustrativos; as estatísticas usam todas as consultas. Os arquivos foram gravados diretamente no projeto dentro da pasta sincronizada do OneDrive; o upload na nuvem não foi confirmado por este diagnóstico. A figura com imagens biométricas permanece fora do Git, conforme o padrão do repositório.

Foram aprovados 84 testes automatizados, incluindo os casos de referência vazia, caixas nativas, limites dos intervalos e controles anteriores. A conferência das transições reproduziu as perdas e recuperações previamente registradas: 55 perdas/10 recuperações na superior e 152 perdas/7 recuperações na inferior. Os arquivos CSV e JSON permitem conferir todas as contagens.


## 7. Continuação: localização aprendida da pupila

Foi treinado um localizador auxiliar em 6.282 exemplos de 167 participantes, com seleção interna em 879 exemplos de outros 16 participantes do treino original. Foram concluídas 12 épocas e selecionada a época 8. A perda geométrica aproximada caiu de 0,0008265906 para 0,0001663508. Os alvos vieram de buracos na anotação da íris; essa perda não comprova precisão anatômica.

Todas as 482 consultas foram mantidas. O Rank-1 limpo permaneceu em 90,0415% (434 acertos). A calibração fixa produziu TAR de 90,2490% e FMR de 1,0235%, acima do máximo. A recalibração limpa produziu TAR de 89,8340%, abaixo da meta, e FMR de 0,9820%. Nenhuma variante cumpriu todos os critérios. Na oclusão inferior de 10%, o Rank-1 subiu de 59,96% para 61,00% ou 61,20%, mas o TAR não melhorou e os intervalos dos ganhos incluem zero.

Não houve promoção, nova inferência no teste ou mudança nas áreas nominais anteriormente aprovadas. O resultado anterior de teste permanece 91,36%, nas condições já documentadas. A reprodução dos escores teve diferença máxima zero e a suíte completa passou em 87 testes. Os arquivos foram salvos no projeto dentro do OneDrive; o upload na nuvem não foi verificado.

Detalhes e imagem com fotos reais e texturas: [relatório da localização da pupila](../pfc1-segmentacao-mmu/PUPILA_APRENDIDA_2026-10-22.md).
