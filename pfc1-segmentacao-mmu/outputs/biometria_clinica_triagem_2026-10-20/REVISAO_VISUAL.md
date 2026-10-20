# Revisão visual inicial — 20/10/2026

A prancha `data/qa_clinica/pares_validacao.jpg` contém seis olhos da validação, com galeria mais antiga e consulta mais recente, escolhidos por ordem de identificador, sem consultar resultados biométricos. Observam-se mudanças de enquadramento, rotação, iluminação e tamanho aparente da pupila. A inspeção não comprova identidade e não valida diagnósticos. A transferência da segmentação UBIPr deve ser examinada antes da inferência clínica.

A triagem por dHash de 64 bits sinalizou quatro pares com distância de Hamming 2, incluindo um entre validação e teste. A prancha `data/qa_clinica/candidatos_duplicatas.jpg` foi inspecionada exclusivamente para auditoria de duplicatas, sem acessar escores ou ajustar parâmetros do reconhecedor.

| Par | Decisão de inspeção |
|---|---|
| P0281 OS, 11/06 e 02/03/2025 | Capturas visualmente diferentes do mesmo identificador; posição, pupila e reflexos diferem. Não excluir por dHash. |
| P0845 OS / P0597 OS | Aparências distintas na região pupilar e contexto. Sem evidência visual de duplicata. |
| P0897 OS / P0265 OS | Reflexos, posição e contexto distintos. Sem evidência visual de duplicata. |
| P0984 OD / P0225 OD | Configuração pupilar e iluminação distintas. Sem evidência visual de duplicata entre partições. |

Não foram realizadas exclusões adicionais a partir desse rastreio. dHash global serve para levantar candidatos, mas não elimina todas as possibilidades de duplicação ou atribuição incorreta de identidade. A consistência completa de lateralidade e dos 236 olhos ainda não foi inspecionada. As datas derivam dos nomes dos arquivos; o README informa o formato `date_or_suffix`, sem comprovação independente das datas de aquisição.

A extensão clínica permanece como triagem, sem resultados de reconhecimento. Os cinco registros preliminares normal→alterado são observacionais e insuficientes, por si só, para concluir efeitos causais de doenças.
