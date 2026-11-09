# Fechamento dos testes de 1% a 31% e do recorte

**Concluído: 63 condições da referência e 63 do candidato**, com auditoria independente das contagens. A regra relativa completa de comparação do candidato foi reprovada. Nenhum modelo do aplicativo foi substituído automaticamente.

A grade contém o controle e cada percentual inteiro de 1% a 31%, nas posições superior e inferior. As 13 condições anteriores foram reutilizadas após conferência; 50 foram calculadas nesta rodada. Em cada condição foram preservadas as mesmas 486 consultas e 7.290 comparações impostoras, inclusive falhas. As repetições das mesmas fotografias não constituem pessoas ou observações independentes adicionais.

## Comparação com o contorno selecionado

O candidato mistura, em proporção fixa de 50%, o escore polar original e o obtido com o contorno contínuo sem pequenos fragmentos. Os outros oito componentes, pesos de fusão, calibração e limiar permanecem fixos. A escolha ocorreu na validação, antes da comparação densa do candidato.

| Perda e posição | Versão | Rank-1 | TAR | FMR | Correto e aceito |
|---|---|---:|---:|---:|---:|
| Sem perda | Referência | 91,15% | 92,39% | 0,864% | 89,51% |
| Sem perda | Candidato | 91,15% | 93,00% | 0,823% | 90,12% |
| 1% superior | Referência | 89,92% | 92,18% | 0,878% | 88,48% |
| 1% superior | Candidato | 90,33% | 92,18% | 0,878% | 89,30% |
| 1% inferior | Referência | 90,95% | 91,15% | 0,892% | 88,89% |
| 1% inferior | Candidato | 91,15% | 91,36% | 0,960% | 89,09% |
| 10% superior | Referência | 82,30% | 84,57% | 1,674% | 80,25% |
| 10% superior | Candidato | 81,89% | 84,16% | 1,660% | 79,42% |
| 10% inferior | Referência | 58,23% | 60,91% | 2,565% | 55,56% |
| 10% inferior | Candidato | 59,47% | 61,32% | 2,593% | 56,38% |
| 31% superior | Referência | 69,34% | 70,99% | 2,016% | 66,26% |
| 31% superior | Candidato | 69,34% | 71,40% | 1,975% | 66,87% |
| 31% inferior | Referência | 32,51% | 29,42% | 3,525% | 27,57% |
| 31% inferior | Candidato | 30,86% | 29,01% | 3,608% | 26,95% |

A média do evento correto e aceito nas 63 condições foi de 61,46% na referência e 61,58% no candidato. A FMR aumentou em 31 condições. A regra exigia preservar Rank-1 e TAR limpos, FMR limpa de até 1%, melhorar a média conjunta e não elevar a FMR em nenhum cenário. A aprovação relativa e o atendimento absoluto dos alvos 90/90/1 são questões diferentes.

[Tabela completa de todos os níveis](outputs/grade_densa_analise_2026-11-08/tabela_completa.csv). [Curva, auditoria e fronteiras condicionadas](outputs/grade_densa_analise_2026-11-08/RESULTADO_PARA_DEFESA.md).

Embora o evento conjunto tenha alcançado 90,12% no teste limpo, na validação limpa ficou em 88,59%. Esse resultado não representa aprovação de prontidão clínica nem garantia de desempenho populacional.

## O que mudou no recorte

O filtro remove somente componentes menores que 0,5% do maior componente, sem acrescentar pixels ou fechar oclusões. Nas 78 imagens em três situações, a variação de Dice foi inferior a 0,01 ponto percentual: uma melhora pequena, que não foi confundida com grande ganho anatômico ou de reconhecimento. A filtragem guiada pelas bordas e as combinações de resoluções não superaram o controle nas três situações.

O novo ensaio SAM3.1 com até 24 pontos positivos e negativos exteriores alcançou Dice de 84,19%, incluindo 40 retornos à máscara inicial entre 78 imagens. É um procedimento híbrido; o ganho não é atribuído apenas ao SAM. Ficou acima do refino anterior de 76,70%, mas abaixo dos 88,46% do controle contínuo, que foi preservado.

Nos seis exemplos clínicos fixos, a cobertura subpixel suaviza a apresentação da borda mantendo RGB e máscaras binárias idênticos aos anteriores. Cinco recortes contêm suporte; o caso sem localização permanece indisponível e requer revisão. Nenhuma textura foi gerada ou retocada, e as imagens não receberam nova validação anatômica clínica.

[Recortes em resolução nativa, comparações e comando de exportação](RECORTES_NATIVOS_2026-11-08.md).

## Como interpretar o percentual

- Referência, superior: suporte nominal mínimo no prefixo com critérios marginais = 100%; incluindo correto e aceito≥90% = nenhum nível aprovado.
- Referência, inferior: suporte nominal mínimo no prefixo com critérios marginais = 99%; incluindo correto e aceito≥90% = nenhum nível aprovado.
- Candidato, superior: suporte nominal mínimo no prefixo com critérios marginais = 99%; incluindo correto e aceito≥90% = 100%.
- Candidato, inferior: suporte nominal mínimo no prefixo com critérios marginais = 99%; incluindo correto e aceito≥90% = 100%.

Esses percentuais são condicionados à grade, ao sistema, à galeria e ao suporte originalmente anotado. Não medem o anel anatômico normativo ou a extensão de doença. A posição da perda importa; não foi demonstrado mínimo universal nem efeito causal de patologias. Os intervalos por pessoa permanecem descritivos, com dados reutilizados no desenvolvimento e galeria fixa.

## Entrega

- [Artigo atualizado](artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx): 30 páginas de conteúdo e 4 de referências, 31 referências, 12 tabelas e 5 figuras.
- [Verificação do documento](artigo/verificacao_2026-11-08/VERIFICACAO_FINAL.json).
- [Grade e resultados completos](outputs/grade_densa_analise_2026-11-08/RESULTADO_PARA_DEFESA.md).
- [Protocolo do candidato congelado](outputs/grade_densa_contorno_misto_2026-11-08/protocolo.json).
