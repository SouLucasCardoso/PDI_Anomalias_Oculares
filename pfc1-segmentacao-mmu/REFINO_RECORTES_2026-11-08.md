# Refino do recorte da íris em 8 de novembro de 2026

Os recortes do artigo foram refeitos com a cabeça interativa oficial SAM3.1 e pixels da fotografia original. Os grandes degraus vinham da máscara clínica calculada em 106 × 80 pixels e ampliada depois de se tornar binária. O novo caminho calcula o contorno na resolução nativa, prevê a pupila em uma janela separada e remove componentes desconectados sem pontos de íris. Não foram geradas texturas, preenchidas lacunas ou impostas elipses. As máscaras binárias ficam separadas da transição alfa de um pixel usada na apresentação.

## Comparação medida

Foram sorteadas 78 imagens da validação UBIPr: uma de cada lado de cada uma das 39 pessoas, com semente 20261108. A seleção não usa qualidade, diagnóstico ou acerto. A referência entra somente no cálculo posterior do Dice. Não houve inferência nova no teste de identidade.

| Método | Dice médio neste subconjunto | Melhora sobre a máscara anterior |
|---|---:|---:|
| U-Net congelada, máscara ampliada por vizinho mais próximo | 88,20% | Referência pareada |
| Mesma U-Net, margem contínua interpolada antes do rótulo | 88,46% | 67 de 78 imagens |
| Refino automático interativo SAM3.1 | 76,70% | 3 de 78 imagens |

A correção conservadora ganhou aproximadamente 0,26 ponto percentual e reduz os degraus sem mudar pesos nem impor anatomia. É uma medida de desenvolvimento nesse subconjunto, sem prova de ganho no reconhecimento. O SAM produz contornos mais contínuos em exemplos clínicos, mas foi inferior no controle quantitativo: permaneceu experimental e ilustrativo. O reconhecedor móvel e a cadeia congelada das oclusões não foram substituídos.

As rodadas intermediárias foram preservadas nos diretórios v3, v4 e v5. As primeiras comparações usaram redimensionamento bicúbico na entrada UBIPr; a comparação final usa bilinear, como a inferência histórica. Os três métodos finais têm exatamente as mesmas 78 imagens e o mesmo valor anterior de Dice. Os números intermediários não foram combinados com o resultado final.

## Casos clínicos e revisão

Os seis casos do artigo foram mantidos. Os cinco com localização inicial não vazia produziram máscaras com um componente conectado; isso não é uma medida de correção anatômica. Persistem inclusões indevidas junto à pupila, reflexos e possíveis regiões sem tecido, sobretudo na iridodiálise. P0803 gerou apenas um candidato inadequado perto da pupila; esse candidato ficou separado para auditoria e a saída final continuou vazia, sinalizada para revisão. Não houve revisão clínica manual concluída nesta rodada nem estimativa de Dice clínico.

O artigo atualizado tem 30 páginas de conteúdo, 4 de referências, 31 referências e 5 figuras. As páginas alteradas foram renderizadas e inspecionadas; as demais têm imagens renderizadas idênticas à versão já revisada. A verificação também confirmou que os 13 resultados de oclusão e as fontes registradas da execução congelada permanecem preservados.

## Arquivos

- `artigo/ARTIGO_AREA_IRIS_UNISATC_2026-11-08.docx`: artigo atualizado.
- `artigo/figuras_2026-11-08/`: três composições e proveniência dos seis casos.
- `outputs/refino_recorte_sam31_final_2026-11-08/comparacao_antes_depois.png`: comparação dos seis exemplos.
- `outputs/refino_recorte_sam31_final_2026-11-08/`: máscaras anteriores e novas, recortes nativos, metadados e protocolo registrado antes da inferência.
- `outputs/refino_recorte_validacao_final_2026-11-08/`: validação final do SAM, com todas as 78 observações.
- `outputs/contorno_continuo_2026-11-08/`: comparação da margem contínua, sem alteração topológica deliberada.
- `outputs/exemplo_contorno_continuo_2026-11-08/comparacao.png`: exemplo executado pela ferramenta de foto local.
- `artigo/verificacao_2026-11-08/VERIFICACAO_FINAL.json`: paginação, hashes, preservação do modelo UniSatc e auditoria científica.

## Uso em uma fotografia local

No ambiente SAM já preparado, a ferramenta abaixo salva uma máscara binária, recorte RGBA com RGB original, comparação e proveniência. A opção `--clinical-scale` reproduz a localização de um terço para fotografias clínicas ampliadas; omita-a para a entrada UBIPr normal.

```powershell
& 'C:/Users/lucaz/pfc-sam3-20261103/Scripts/python.exe' `
  pfc1-segmentacao-mmu/recortar_iris_alta_res.py `
  --image 'caminho/olho.jpg' --output-dir 'outputs/recorte_novo' --clinical-scale
```

`--sam31-experimental` ativa a alternativa SAM com revisão necessária. O diretório de saída deve ser novo para preservar resultados existentes. Essa ferramenta não modifica cadastros nem descritores do aplicativo.

Quatro testes passaram: pontos internos, remoção de fragmentos sem prompts, preservação exata do RGB e da pupila na transparência, e regressão que distingue interpolar confiança de ampliar rótulos binários. A ferramenta também foi executada em uma fotografia pública do artigo.

## Tecnologia verificada

Código oficial SAM 3: revisão `f1647e8d0c1d280991f4d1b7d974c2704537fe66`. Checkpoint oficial SAM3.1: revisão `daa63191845a41281374e725f4c9e51c7a824460`, SHA-256 `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`. Foram carregados estritamente 474 tensores do extrator e ramos visuais, 17 do codificador de prompts e 131 do decodificador, sem pesos ausentes aleatórios. O ambiente existente foi mantido.

Fontes oficiais consultadas em 08/11/2026: [código Meta](https://github.com/facebookresearch/sam3/commit/f1647e8d0c1d280991f4d1b7d974c2704537fe66), [checkpoint Meta](https://huggingface.co/facebook/sam3.1/tree/daa63191845a41281374e725f4c9e51c7a824460). Os hashes das fontes de cada execução constam dos respectivos protocolos.
