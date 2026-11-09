# Recortes nativos para revisão

Os arquivos abaixo preservam os pixels RGB da fotografia e as máscaras binárias do SAM3.1 já avaliadas. A apresentação agora usa cobertura subpixel da borda, em uma vizinhança de um pixel nativo. Essa transparência não entra no cálculo de área ou no reconhecimento. Não houve preenchimento de textura, alteração de fotografia ou certificação clínica das máscaras.

| Caso fixo | Recorte em PNG transparente | Comparação da apresentação |
|---|---|---|
| P0005 OD, controle normal do dataset | [Recorte nativo](outputs/sam31_matte_subpixel_2026-11-08/P0005_OD20241206/recorte_subpixel.png) | [Antes e depois](outputs/sam31_matte_subpixel_2026-11-08/P0005_OD20241206/comparacao.png) |
| P0007 OS, controle normal do dataset | [Recorte nativo](outputs/sam31_matte_subpixel_2026-11-08/P0007_OS20250306/recorte_subpixel.png) | [Antes e depois](outputs/sam31_matte_subpixel_2026-11-08/P0007_OS20250306/comparacao.png) |
| P0209 OD, alterações segundo o dataset | [Recorte nativo](outputs/sam31_matte_subpixel_2026-11-08/P0209_OD20250329/recorte_subpixel.png) | [Antes e depois](outputs/sam31_matte_subpixel_2026-11-08/P0209_OD20250329/comparacao.png) |
| P0564 OD, alterações segundo o dataset | [Recorte nativo](outputs/sam31_matte_subpixel_2026-11-08/P0564_OD20250526/recorte_subpixel.png) | [Antes e depois](outputs/sam31_matte_subpixel_2026-11-08/P0564_OD20250526/comparacao.png) |
| P0114 OS, caso difícil do dataset | [Recorte nativo](outputs/sam31_matte_subpixel_2026-11-08/P0114_OS20250417/recorte_subpixel.png) | [Antes e depois](outputs/sam31_matte_subpixel_2026-11-08/P0114_OS20250417/comparacao.png) |
| P0803 OD, localização indisponível | Mantido sem suporte, pendente de revisão | [Falha preservada](outputs/sam31_matte_subpixel_2026-11-08/P0803_OD20250112/comparacao.png) |

Fonte das seis fotografias clínicas: Qian (2026), SLP-VLD v3, CC BY 4.0, os mesmos casos do artigo. Os rótulos vêm do dataset e não constituem novos diagnósticos. [Proveniência e verificação de RGB e máscaras](outputs/sam31_matte_subpixel_2026-11-08/CONCLUIDO.json).

## Exportar outra fotografia

Da pasta `pfc1-segmentacao-mmu`, no PowerShell:

```powershell
& 'C:\Users\lucaz\pfc-sam3-20261103\Scripts\python.exe' .\recortar_iris_subpixel.py --image 'C:\caminho\olho.jpg' --output-dir '.\outputs\meu_recorte_subpixel'
```

O comando salva o recorte, a máscara, a margem e a proveniência separadamente. A saída é uma predição que deve ser inspecionada. `--clinical-scale` usa o controle de escala histórico para fotografias clínicas ampliadas. A opção `--sam3` executa o refino SAM3.1 experimental e exige GPU livre; não deve ser executada junto das inferências da grade.

[Exemplo público UBIPr exportado](outputs/exemplo_recorte_subpixel_final_2026-11-08/recorte_subpixel.png). [Pequenos fragmentos e Dice de validação](outputs/contorno_fragmentos_entrega_2026-11-08/RELATORIO_ATUAL.md). [SAM3.1 com negativos exteriores e fallback](outputs/sam31_prompts_exteriores_2026-11-08/RELATORIO_ATUAL.md).

Fonte do exemplo UBIPr: Padole e Proença (2012), UBIPr Single Eyes Segmented, CC BY-NC-SA 4.0. Essa licença é distinta da licença das seis fotografias clínicas acima.
