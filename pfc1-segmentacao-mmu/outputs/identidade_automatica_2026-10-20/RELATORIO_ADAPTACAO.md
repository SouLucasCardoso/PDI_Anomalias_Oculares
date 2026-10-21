# Adaptação ao recorte automático — 20/10/2026

## 1. Treinamento executado

Foi concluído um ajuste do encoder anterior em recortes produzidos exclusivamente pela U-Net congelada. O treinamento usou 7.716 imagens de 183 pessoas e 366 classes de olho antes da exclusão de máscaras previstas vazias. Foram executadas 6 épocas de ajuste, com seleção da época 0. A época zero contém os pesos anteriores, permitindo conservar o modelo inicial caso não haja melhora pelo critério registrado.

Os parâmetros atualizados são do encoder e da cabeça angular; a U-Net não foi retreinada. A cabeça foi inicializada do checkpoint anterior, com a mesma ordem das classes. Foram usados AdamW, taxas de aprendizado de 0,00003 para encoder e 0,0001 para cabeça, margem angular 0,3, batch 64 e semente 43. As ampliações de treino incluem rotação e brilho/contraste, sem oclusão artificial.

## 2. Comparação no original

As 482 consultas pertencem a 16 pessoas distintas das pessoas de treino; a galeria contém as capturas da sessão 1 de 32 olhos. A comparação usa média das três melhores correspondências por olho. O limiar é recalibrado na validação para cada checkpoint, com FMR empírica de até 1%. As mesmas máscaras automáticas, consultas e capturas de cadastro são usadas na época zero e no modelo selecionado.

| Configuração | Rank-1 | TAR | FMR | Identificação e aceitação conjuntas | Falhas de consulta |
|---|---:|---:|---:|---:|---:|
| Modelo anterior, época zero | 66,80% | 59,34% | 0,99% | 54,77% | 4 |
| Modelo selecionado, época 0 | 66,80% | 59,34% | 0,99% | 54,77% | 4 |

A época selecionada foi zero: a adaptação simples não superou a TAR inicial e os parâmetros anteriores foram mantidos.

Os intervalos de ganho são condicionais à galeria e aos modelos escolhidos. Como o mesmo conjunto selecionou o checkpoint, eles não corrigem o viés de seleção e não devem ser interpretados como confirmação independente.

- RANK1: ganho de 0.00 pp; IC 95% pontual 0.00 a 0.00 pp.
- TAR: ganho de 0.00 pp; IC 95% pontual 0.00 a 0.00 pp.

## 3. Limites e mínimo de área

Essa validação já foi utilizada repetidamente no desenvolvimento, inclusive para selecionar o checkpoint inicial. A melhora ou ausência de melhora deve ser descrita como exploratória. As imagens de teste e as bases clínicas não receberam nova inferência. A validação mede reconhecimento com máscaras automáticas, mas não prova que o encoder use exclusivamente textura anatômica de íris: erros de máscara podem incluir contexto externo.

O limiar biométrico pode mudar com o checkpoint; por isso a TAR compara os sistemas calibrados no mesmo alvo, não uma única escala absoluta de similaridade. Nenhum ganho pode ser atribuído somente à máscara: o ajuste muda os pesos e a distribuição de treino.

No modelo selecionado, faltam 23.20 pp de Rank-1 e 30.66 pp de TAR para o critério operacional de 90%. Essa distância não é uma previsão de épocas necessárias. Sem alcançar e confirmar o desempenho original, não se estabelece uma área mínima global. Não foi produzida nova curva de oclusão nesta rodada.

## 4. Auditoria e reprodução

Os recortes foram produzidos em lotes de 32 pela U-Net em FP32; o encoder foi avaliado em lotes de 128, em vez dos 64 anteriores. Frente ao controle anterior, as identidades e a validade das consultas foram idênticas, houve uma decisão Rank-1 diferente e duas decisões de aceitação diferentes nos respectivos limiares. A maior diferença absoluta de escore foi 0,02443. As duas mudanças de lote não foram isoladas causalmente. A época zero desta execução é a referência pareada principal, sem atribuir essas diferenças a treinamento. Máscaras vazias são excluídas só do treino e permanecem como falhas na validação.

Vinte e seis testes automatizados passaram, incluindo controles de retenção de falhas e de cadastro sem máscara. O piloto técnico ficou separado das estimativas científicas. Pesos anteriores, novos pesos selecionados, protocolo, histórico, auditoria e escores foram preservados.

- [Protocolo de adaptação](../../PROTOCOLO_ADAPTACAO_AUTOMATICA_2026-10-20.md).
- [Registro e hashes](protocolo.json).
- [Histórico completo](historico.csv).
- [Conclusão da execução](CONCLUIDO.json).
- [Comparação e intervalos](comparacao_pareada.json).
