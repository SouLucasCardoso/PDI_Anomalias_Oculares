# Grade de oclusão de 1% a 31%

**Concluído e auditado:** 63 condições da referência e 63 do candidato. A computação terminou em 08/11/2026, por volta das 23h03; a revisão final do artigo foi concluída em 09/11/2026. Não há treino ou inferência desta grade aguardando outra mensagem.

O [relatório final](RESULTADO_GRADE_DENSA_2026-11-08.md) reúne os resultados, as limitações e o artigo atualizado. A grade contém o controle e cada percentual inteiro de 1% a 31%, nas orientações superior e inferior. Treze condições existentes foram reutilizadas após conferência de hashes e contagens; cinquenta foram calculadas nesta rodada. O limiar e os nove descritores da referência permaneceram fixos.

- [Tabela completa da comparação](outputs/grade_densa_analise_2026-11-08/tabela_completa.csv).
- [Curvas e interpretação para a defesa](outputs/grade_densa_analise_2026-11-08/RESULTADO_PARA_DEFESA.md).
- [Auditoria independente das 63 condições](outputs/grade_densa_analise_2026-11-08/AUDITORIA_FINAL.json).
- [Fechamento do documento e dos experimentos](outputs/FECHAMENTO_GRADE_DENSA_2026-11-08.json).
- [Artigo final com 30 páginas de conteúdo e 4 de referências](artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx).

O candidato elevou o evento correto e aceito limpo de 89,51% para 90,12% e reduziu a FMR de 0,864% para 0,823%. A FMR aumentou em 31 condições, por isso a regra completa de substituição foi reprovada e a referência foi mantida. Os arquivos por etapa permanecem disponíveis:

- [Relatório da grade](outputs/grade_densa_1a31_2026-11-08/RELATORIO_ATUAL.md).
- [Estado e contagem de condições](outputs/grade_densa_1a31_2026-11-08/estado.json).
- [Resultados completos por condição](outputs/grade_densa_1a31_2026-11-08/resultados.json).
- [Tabela CSV](outputs/grade_densa_1a31_2026-11-08/resumo.csv).
- [Protocolo registrado](outputs/grade_densa_1a31_2026-11-08/protocolo.json).
- [Refino dos fragmentos, selecionado por segmentação](outputs/contorno_fragmentos_entrega_2026-11-08/RELATORIO_ATUAL.md).
- [Validação de reconhecimento do novo contorno](outputs/contorno_componentes_identidade_2026-11-08/RELATORIO_ATUAL.md): concluída; [estado final](outputs/contorno_componentes_identidade_2026-11-08/estado.json).
- [Mistura polar de 50%, selecionada na validação](outputs/contorno_componentes_misto_2026-11-08/RELATORIO_ATUAL.md).
- [Comparação densa do candidato](outputs/grade_densa_contorno_misto_2026-11-08/estado.json): concluída, sem troca automática de modelo.
- [Fechamento e auditoria automáticos](outputs/grade_densa_1a31_2026-11-08/FECHAMENTO.json).
- [Recortes nativos e comparações](RECORTES_NATIVOS_2026-11-08.md).
- [Ensaio adicional SAM3.1 concluído](outputs/sam31_prompts_exteriores_2026-11-08/RELATORIO_ATUAL.md): melhor procedimento híbrido com Dice de 84,19%, incluindo 40 retornos à máscara inicial; controle contínuo de 88,46% preservado.

O processo percorreu todos os níveis, incluindo os posteriores à primeira reprovação, e terminou antes do corte computacional registrado. Os resultados finais foram salvos; não dependem de manter uma execução ativa.

Todos os 486 casos e suas falhas permanecem nas métricas, com 7.290 pares impostores por condição. A fração de área usa a anotação original e não mede o anel anatômico completo ou a extensão de uma doença. Os novos recortes e o reconhecimento são avaliados separadamente; o modelo do aplicativo não é substituído automaticamente.
