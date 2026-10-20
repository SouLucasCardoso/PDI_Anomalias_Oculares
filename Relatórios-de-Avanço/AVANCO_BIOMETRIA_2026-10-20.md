# Avanço da pesquisa biométrica em 20 de outubro de 2026

## Objetivo e conclusão desta rodada

O autor esclareceu que o foco acordado com o orientador é investigar a área preservada da íris necessária para reconhecimento de identidade, com interesse nas limitações associadas a condições oculares. O título e o escopo podem mudar em relação ao pré-projeto. Os planos anteriores de classificação clínica foram preservados como histórico e não constituem o objetivo ativo.

Foram concluídos novos experimentos de segmentação, oclusão e reconhecimento. O mínimo global não foi determinado pelo critério registrado de Rank-1 e TAR de pelo menos 90%. Há, porém, curvas de desempenho, perdas pareadas e uma distribuição exploratória de tolerância entre consultas originalmente identificadas. Não foi produzido um limite anatômico universal nem uma demonstração causal de doença.

## Resultados novos concluídos

| Experimento | Amostra e configuração | Resultado original |
|---|---|---|
| U-Net UBIPr | 30 épocas, checkpoint da época 26 escolhido na validação | Dice de teste da íris 0,9342; primeiro plano 0,8944 |
| DINOv3 com referência da íris | 486 consultas, 16 pessoas, galeria de 32 olhos | Rank-1 13,37%; TAR 7,00%; FMR 1,47% |
| DINOv3 com imagem inteira | Mesmo protocolo UBIPr | Rank-1 46,50%; TAR 25,51%; FMR 0,87%; inclui contexto |
| HDBIF clínico congelado | SLP-VLD, 319 consultas de 107 pessoas, galeria de 176 olhos | Rank-1 15,99%; TAR 50,78%; FMR 2,45% |
| Extrator treinado para identidade | ResNet18 com margem angular; treinamento em 183 pessoas; curva UBIPr exploratória | Rank-1 67,90%; TAR 55,14%; FMR 0,96% |

As 19 condições de oclusão foram concluídas tanto no experimento DINOv3 quanto no extrator treinado. O teste clínico utilizou configuração e limiar congelados na validação. Não foram removidos casos depois de observar seus escores. A diferença de galeria entre validação e teste clínico impede atribuir a queda de Rank-1 somente à condição ocular.

O treinamento de identidade terminou na época 23 por parada antecipada, com checkpoint selecionado na época 15. As duas rodadas UBIPr usam o mesmo teste já examinado; a comparação com o novo extrator foi marcada como exploratória, sem apresentá-la como um novo teste intocado.

## Área e tolerância por consulta

O critério global foi mantido mesmo diante de desempenho insuficiente no original. As porcentagens correspondem à região anotada na imagem, não necessariamente a toda a superfície anatômica da íris. Máscaras vazias são falhas e não recebem uma porcentagem de área válida.

No extrator treinado, 234 das 486 consultas tiveram simultaneamente Rank-1 correto e escore genuíno acima do limiar no original. Com 90% da região preservada, 117 dessas consultas mantiveram a identificação sob oclusão superior, e 115 sob oclusão inferior. Esses 50,00% e 49,15% são retenções condicionais, sem alterar o denominador das métricas globais. Uma mediana interpolada de 95% em estatísticas auxiliares não representa um nível efetivamente testado na grade de dez pontos.

## Qualidade dos dados clínicos

A inspeção completa da validação SLP-VLD identificou capturas oblíquas, reflexos, variações de dilatação e aproximações circulares imprecisas. No teste, dez imagens falharam e três cadastros ficaram indisponíveis. Um diagnóstico posterior mostrou concentração de candidatos errados em cadastros com baixa fração polar prevista. A análise não foi usada para excluir imagens ou recalibrar o teste.

A Nuclear Cataract foi registrada como possível domínio adicional, com partições por paciente. A inspeção dos primeiros oito exemplos da calibração mostrou recortes fragmentados e iluminação em fenda que não sustentavam a inferência proposta. A execução e a curva condicional foram interrompidas antes de escores biométricos. Os dados, protocolos, códigos registrados e evidência visual foram preservados. Essa decisão não demonstra inviabilidade de toda a base para qualquer outro pipeline.

## Artefatos e preservação

- Texto ativo: `pfc1-segmentacao-mmu/artigo/ARTIGO_AREA_IRIS_EM_PRODUCAO.md`, com resumo, métodos, resultados, discussão, conclusões e referências de trabalho.
- Sínteses e figuras: `pfc1-segmentacao-mmu/outputs/consolidacao_biometria_2026-10-20`.
- Pesos treinados e arquivos de reprodução: `pfc1-segmentacao-mmu/backups`.
- Estado verificável: `executar.ps1 status_producao.py` na pasta do projeto.

Os testes de instalação e os pilotos pequenos foram separados das estimativas científicas. Dezoito testes automatizados relevantes passaram. Os pacotes ZIP verificam os arquivos por SHA-256; os pesos únicos de treinamento, fontes e resultados compactos foram preservados. Não houve envio de e-mail, publicação ou redistribuição externa.

As execuções computacionais desta rodada terminaram. Permanecem a revisão científica do texto com o orientador, a normalização bibliográfica e a diagramação no modelo institucional para a entrega de 9 de novembro. Nenhum resultado autoriza anunciar um percentual mínimo global validado.
