# Inspeção visual da validação — 20/10/2026

As nove páginas em `data/qa_biometria/slpvld_pranchas` foram inspecionadas. Elas incluem as 171 imagens da validação, ordenadas por identificador, lado e data, sem selecionar por acerto. O índice das páginas está em `indice.json` nessa pasta.

O círculo vermelho indica a aproximação pupilar; o verde, a aproximação externa da íris. O valor “polar válido” é uma fração estimada pela máscara prevista no espaço normalizado. Não é porcentagem de íris clinicamente aproveitável, grau de doença nem área verdadeira anotada.

Observações:

- Há diferenças grandes de dilatação, enquadramento, rotação, reflexos e cobertura por pálpebras entre capturas do mesmo identificador.
- As aproximações circulares nem sempre acompanham a borda visível. Exemplos merecendo investigação incluem P0432_OS20250213 e P0721_OS20250429. Não se quantificou erro de contorno por falta de referência manual.
- P0885_OD20250505 e P0885_OD20250602 apresentaram máscara polar vazia. São capturas muito oblíquas ou sem região da íris corretamente localizada. A consulta P0885_OS20250505 também apresenta localização fora da região central visível e fração prevista que, isoladamente, não comprova qualidade.
- Há exemplos com baixa fração polar prevista e pupila muito diferente entre sessões, como P0575_OS20250113. A diferença não deve ser atribuída automaticamente a doença ou à perda de área verdadeira.
- Reflexos e pálpebras podem interferir no processamento mesmo quando os círculos parecem aproximadamente posicionados. As pranchas não fornecem uma validação quantitativa da máscara.

Não foram excluídas imagens após observar acertos ou erros. As falhas operacionais continuam no denominador e as comparações indisponíveis são rejeitadas. As observações justificam analisar reconhecimento ponta a ponta e qualidade estimada separadamente. A validade de um percentual de área clínica exige definição operacional explícita e referência adequada.

O teste clínico reservado não foi avaliado nesta etapa. A inspeção é computacional, não validação de diagnóstico por especialista.
