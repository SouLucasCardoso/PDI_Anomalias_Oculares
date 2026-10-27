# Quais bases locais possuem anomalias oculares?

**Conferência: 27/10/2026.** Sim: temos fotografias clínicas com alterações reais. Há inclusive registros com diagnóstico que menciona diretamente a íris no SLP-VLD. Isso é diferente de afirmar que as oclusões artificiais UBIPr representam doenças reais ou que já medimos o impacto causal dessas alterações no reconhecimento.

## Inventário da cópia disponível

| Base | O que temos | Anomalias documentadas e limite |
|---|---|---|
| UBIPr | 11.018 pares imagem/máscara de 261 pessoas | Base biométrica principal. Não temos diagnósticos clínicos por imagem; ruído, reflexos e oclusões naturais não são diagnósticos. As perdas de área adicionadas nos testes são sintéticas. |
| MMU | 450 pares de 45 pessoas | Segmentação/biometria, sem rótulos clínicos no protocolo. Não se pode afirmar ausência de doença em todos os participantes. |
| SLP-VLD v3 | 2.228 registros, todos com arquivo local; 2.227 hashes distintos antes da deduplicação | Diagnósticos do segmento anterior. **Nove imagens distintas mencionam diretamente a íris ou iridodiálise**, em oito pessoas/olhos codificados. Há mais quatro imagens com sinéquias anteriores/posteriores sem a palavra íris no diagnóstico. |
| SLID | 2.617 imagens; 2.372 com lesão anotada e 245 sem lesão anotada | Catarata, ceratite, distrofia/cicatriz corneana, pterígio e outras categorias. Não há categoria explícita de defeito da íris na taxonomia local nem IDs de pacientes na versão adquirida. “Sem lesão anotada” não comprova olho saudável. |
| CatScreen, amostra pública | 400 imagens: 200 Clean, 100 Noisy e 100 Unlabelled | Nas 200 Clean: 102 Cataract, 58 Normal e 40 Other. Os rótulos clínicos úteis não se estendem automaticamente às 200 Noisy/Unlabelled; Other não especifica uma lesão da íris. |
| Nuclear Cataract v2 | 1.320 imagens de 115 pacientes; 335 imagens rotuladas recuperadas de 69 pacientes | Graduação de catarata nuclear. Não há controle saudável estabelecido na cópia adquirida. Catarata não é perda de tecido da íris. |

Os números clínicos gerais provêm das auditorias locais de 20/10. Em 27/10, foi refeita a seleção textual dos diagnósticos SLP-VLD e conferida a existência dos 2.228 arquivos; as outras bases foram conferidas pelos relatórios de aquisição, sem reabrir todas as imagens ou repetir uma avaliação médica.

## Alterações com menção explícita à íris no SLP-VLD

| Termo no diagnóstico original, preservando associações no inventário JSON | Imagens |
|---|---:|
| Iridodialysis | 2 |
| Iris cyst | 2 |
| Iris synechiae | 1 |
| Penetrating iris injury | 1 |
| Traumatic iris defect | 1 |
| Iris laceration | 1 |
| Partial iris defect | 1 |
| **Total de imagens distintas com menção explícita** | **9** |

Todas as nove existem localmente e possuem hashes diferentes. Oito pertencem à origem de desenvolvimento e uma à instituição externa. São oito pessoas/olhos conforme os códigos distribuídos, não oito identidades clinicamente revalidadas por nós. Não foram escolhidas por escore de reconhecimento ou aparência.

Separadamente, há uma imagem com `Posterior synechiae` e três com `Anterior synechiae`, em dois olhos codificados. Elas não foram somadas à categoria de menção explícita por não conterem `iris`/`irido` no campo. Uveíte, hifema e outras condições aparecem nos registros, mas não foram automaticamente convertidos em lesão estrutural da íris. A seleção literal é uma triagem rastreável e não uma taxonomia clínica exaustiva.

O inventário preserva o diagnóstico completo, pois várias imagens têm comorbidades, pós-operatório, alterações corneanas ou do cristalino. Não se pode atribuir uma falha de reconhecimento apenas ao termo relacionado à íris.

## O que isso permite estudar

As imagens SLP-VLD são candidatas a uma análise complementar de falhas da segmentação, geometria e extração em alterações reais, mantendo o sistema congelado e reportando casos individualmente. Há rótulos úteis, mas não uma máscara validada de porcentagem de tecido da íris perdido nem amostra suficiente para prometer um mínimo clínico geral.

Para medir identificação em cada condição, ainda é preciso verificar repetição do mesmo olho, cadastro adequado, confiabilidade do vínculo de identidade, sessões/datas, metadados ambíguos e qualidade das capturas. Usar a imagem de um olho diferente como se fosse o mesmo participante ou misturar sensores para criar controles invalidaria a comparação. Uma imagem doente isolada pode servir de inspeção, mas não mede identificação genuína sem cadastro correspondente.

Já existe um ensaio clínico anterior com **HDBIF** no SLP-VLD: 319 consultas, Rank-1 de 15,99%, TAR de 50,78% e FMR de 2,45%. É outro reconhecedor/protocolo, com mudança de domínio; não é a avaliação do sistema de 91,36% nesses nove casos nem prova de efeito causal das anomalias. Consulte [o relatório clínico](outputs/hdbif_slpvld_teste_congelado_2026-10-20/RELATORIO_TESTE.md).

Após este inventário, foi executada também a [primeira avaliação do sistema principal nesses casos](CASOS_OCULARES_REAIS_2026-10-27.md). O sistema original não reconheceu as quatro consultas elegíveis; um controle posterior de escala recuperou uma, mas piorou a disponibilidade de outro cadastro. As falhas e o pequeno número de olhos impedem inferir mínimo anatômico ou efeito causal de doenças. As duas etapas estão preservadas separadamente.

## Como conferir a seleção

Com o manifesto SLP-VLD preparado nesta máquina:

```powershell
.\executar.ps1 auditar_anomalias_disponiveis.py --output-dir "$env:TEMP/pfc-inventario-anomalias"
```

[Inventário conferido em 27/10](outputs/inventario_anomalias_2026-10-27/INVENTARIO_ANOMALIAS.json). O script registra a regra literal, os diagnósticos completos, os nomes dos arquivos, os hashes e a presença dos arquivos. Não executa reconhecimento, não modifica os rótulos e não diagnostica fotografias.

## Fontes e termos

- [UBIPr, autores](https://iris.di.ubi.pt/ubipr.html): reconhecimento periocular, CC BY-NC-SA 4.0.
- [SLP-VLD v3, depósito dos autores](https://doi.org/10.6084/m9.figshare.32576697.v3): diagnósticos do segmento anterior, CC BY 4.0 segundo o catálogo oficial salvo em `data/catalogos/slpvld_figshare.json`. A página não foi recuperada pelo navegador de pesquisa nesta conferência; os nove casos foram verificados no manifesto local previamente pareado às planilhas, e não inferidos da página.
- [SLID, artigo dos autores](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1716501/full) e [repositório](https://github.com/xumingyu-hub/SLID): lesões do segmento anterior. A versão local não fornece vínculo por paciente; a licença do artigo não deve ser presumida como licença separada dos dados.
- [CatScreen, autores](https://www.iab-rubric.org/resources/healthcare-datasets/catscreen): amostra pública e base completa sob acordo; uso de pesquisa/educacional.
- [Nuclear Cataract v2, Mendeley](https://data.mendeley.com/datasets/6wv33nbcvv/2): o depósito descreve 1.437 imagens rotuladas; nossa auditoria encontrou 1.320 arquivos e só 335 rótulos recuperados pela seleção secundária. Manter essa divergência, sem inventar rótulos ausentes.
