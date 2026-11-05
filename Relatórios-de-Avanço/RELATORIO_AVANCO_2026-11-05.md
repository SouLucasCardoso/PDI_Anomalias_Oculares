# Relatório de avanço — 5 de novembro de 2026

**Acadêmico:** Lucas Cardoso Rodrigues  
**Orientador:** Rodrigo Ramos Silva  
**Dia:** quinta-feira  
**Escopo:** continuação dos experimentos, pesquisa bibliográfica, demonstrador móvel e organização da entrega no GitHub.

## Encerramento da continuação e novo modelo residual

A rodada de negativos internos terminou após quatro épocas sem melhora elegível. A época zero foi selecionada, preservando os mesmos pesos anteriores; um arquivo de checkpoint diferente por metadados não foi tratado como um novo modelo melhor.

Foi implementado um corretor residual limitado, mantendo o modelo anterior congelado e a saída inicial equivalente ao controle. O treino foi registrado às 08h59 e terminou após 14 épocas, com seleção da época **8**. Checkpoint SHA-256: `fbe9a56276c115de41a5b7ba0c00cab2d4d99ff87930d802dad3a52d97fce5f6`.

| Condição de segmentação | Dice médio |
|---|---:|
| Original | 88,65% |
| Zoom 3× | 86,65% |
| Oblíqua | 87,63% |
| Óculos sintéticos | 88,40% |

| Identidade limpa — 482 consultas | Resultado |
|---|---:|
| Rank-1 | 431/482 — 89,42% |
| Aceitação genuína | 432/482 — 89,63% |
| Correto e aceito | 421/482 — 87,34% |
| Falsas correspondências | 67/7.230 — 0,927% |

A FMR ficou abaixo de 1%, mas os outros requisitos de prontidão não foram atingidos. A fronteira permanece vazia: nenhum novo mínimo foi atribuído. As quatro condições de Dice também não alcançaram 90%. Essas métricas pertencem à validação desta rodada e não se confundem com o teste histórico de 486 consultas.

## Pesquisa para o artigo

Foram reunidas **26 referências**, com 23 DOIs distintos e três documentos ISO, incluindo reconhecimento parcial, qualidade da imagem, segmentação e alterações oculares. Foram produzidos relatório, matriz de evidências, referências comentadas e BibTeX.

O requisito de área utilizável ≥70% da ISO/IEC 29794-6:2015 foi distinguido de uma garantia universal de identificação. Também se distinguiu a área anatômica do anel da íris da fração retida de suporte visível anotado nos nossos ensaios. Estudos de reconhecimento parcial e patologias não sustentam a substituição dessas definições por um único corte universal.

Foi documentada uma possibilidade de encerramento como estudo exploratório, com resultados negativos/insuficientes para a hipótese geral e limitações explícitas. Isso não declara o manuscrito finalizado nem estabelece efeito causal de doenças.

## Reconhecedor móvel

Foi criado um aplicativo web privado para **Samsung Galaxy S23 base, Android 15**, com processamento no Dell G15:

- Captura pela câmera nativa ou escolha de foto; enquadramento de um olho na resolução original.
- Segmentação SAM3.1 residual, visualização da região prevista e faixa polar, nove componentes de identidade e cadastro por pessoa/lado do olho.
- Comparação de uma nova foto com o cadastro, apresentando candidatos e escores experimentais. Não há probabilidade de identidade nem limiar validado para celular.
- Revisão visual antes do cadastro, bloqueio de repetição exata de uma imagem cadastrada como teste independente, registro posterior de testes e exclusão local.
- Funcionamento por USB-C com `adb reverse`, mantendo o servidor no loopback e dispensando internet. Android Platform-Tools 37.0.1 estável foi preparado com origem e checksums oficiais.

Passaram quatro testes automatizados de fronteira HTTP e isolamento. A inferência real offline produziu os nove descritores em três fotos VAL existentes; uma consulta entre sessões colocou a pessoa esperada em primeiro entre dois candidatos. Isso é teste funcional, não estimativa de acurácia do celular. O recorte vertical foi verificado com coordenadas em ambiente simulado; a inspeção visual automatizada do navegador não pôde ser concluída por indisponibilidade da ferramenta.

No primeiro preparo, o USB ainda não enumerava um aparelho. Na organização posterior deste mesmo dia, o S23 foi detectado como autorizado e o encaminhamento foi restabelecido. Cadastros e testes locais já existentes foram preservados, sem publicar nomes, fotos, escores individuais do usuário ou credenciais. Não foi atribuída uma taxa de desempenho a esses testes manuais.

## Organização para publicação

O aplicativo passou a ocupar [reconhecedor-iris/](../reconhecedor-iris/README.md), com interface, servidor, iniciadores e documentação próprios. Os atalhos antigos continuam redirecionando para a nova pasta. O núcleo de inferência permanece congelado na pesquisa, preservando o identificador do motor e a compatibilidade dos descritores cadastrados.

O controle de versão foi ajustado para excluir ambientes, ferramentas baixadas, pesos, caches, bancos privados, fotografias e arquivos integrais de fontes bibliográficas. Código, relatórios e evidências textuais selecionadas compõem a atualização da branch de pesquisa; os registros detalhados por imagem permanecem locais.

## Próximos passos e limites

Antes da apresentação, ensaiar o fluxo completo no S23 com cabo de dados, nova captura, variação de foco e pessoa não cadastrada, incluindo execução sem Wi-Fi/dados móveis. Uma demonstração favorável não comprova mínimo de área ou desempenho clínico. A alternativa hotspot existe no iniciador, mas a alteração persistente do firewall não foi autorizada/aplicada; USB é o modo preparado.

## Registros técnicos

- [Rodada residual e critérios](../pfc1-segmentacao-mmu/SAM3_RESIDUAL_2026-11-05.md).
- [Resultado final do treinamento](../pfc1-segmentacao-mmu/outputs/sam31_residual_2026-11-05/CONCLUIDO.json).
- [Fechamento de identidade](../pfc1-segmentacao-mmu/outputs/sam31_residual_2026-11-05/identidade/CONCLUIDO.json).
- [Pesquisa bibliográfica](../pfc1-segmentacao-mmu/artigo/revisao_bibliografica_2026-11-05/RELATORIO_PESQUISA.md).
- [Delimitação do encerramento](../pfc1-segmentacao-mmu/artigo/revisao_bibliografica_2026-11-05/ENCERRAMENTO_EXPERIMENTAL.md).
- [Guia do reconhecedor](../reconhecedor-iris/README.md).
