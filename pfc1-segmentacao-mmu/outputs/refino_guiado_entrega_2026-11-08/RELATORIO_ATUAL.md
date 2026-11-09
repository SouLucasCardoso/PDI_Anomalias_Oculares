# Refino do contorno por bordas e simetria

Candidato selecionado por segmentação: **continuous**. Reconhecimento ainda não validado.

| Método | Dice limpo | Dice perda superior10% | Dice perda inferior10% |
|---|---:|---:|---:|
| continuous | 88.462% | 84.416% | 78.592% |
| flip_mean | 88.393% | 84.900% | 77.454% |
| guided_r2_e0.001 | 88.416% | 84.407% | 78.420% |
| guided_r2_e0.01 | 88.451% | 84.309% | 78.316% |
| guided_r4_e0.001 | 88.362% | 84.146% | 78.194% |
| guided_r4_e0.01 | 88.410% | 84.038% | 78.092% |
| flip_guided_r2_e0.001 | 88.322% | 84.883% | 77.153% |
| flip_guided_r2_e0.01 | 88.350% | 84.771% | 77.042% |
| flip_guided_r4_e0.001 | 88.230% | 84.616% | 76.832% |
| flip_guided_r4_e0.01 | 88.293% | 84.503% | 76.737% |

78 imagens, uma por lado das39pessoas, em3condições. O Dice ocluído considera somente a região anotada ainda visível. Referências nunca entram no extrator. Casos clínicos sem referência especializada permanecem ilustrativos e sujeitos a revisão.

[Método de filtragem guiada, He et al.](https://people.csail.mit.edu/kaiming/eccv10/index.html)