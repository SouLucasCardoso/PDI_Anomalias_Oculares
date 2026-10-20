# Liberação dos modelos DINOv3 e SAM 3.1

Os pesos oficiais são *gated*: o aceite é individual e precisa ser feito no
navegador pela mesma conta Hugging Face usada no computador. Não coloque o
token em scripts, commits, prints ou mensagens.

## 1. Solicitar acesso no navegador

1. Crie ou entre em uma conta pessoal em <https://huggingface.co/> e confirme o
   e-mail.
2. Abra o DINOv3 ViT-L/16:
   <https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m>.
3. Clique em **Agree and access repository** ou **Request access**.
4. Leia e aceite a licença. Se houver formulário, use informações acadêmicas
   verdadeiras, por exemplo: UniSatc, estudante/pesquisador, projeto acadêmico
   de segmentação e análise de imagens oculares, sem uso comercial.
5. Repita no SAM 3.1: <https://huggingface.co/facebook/sam3.1>.
6. Aguarde até a página de cada modelo mostrar que o acesso foi concedido.
   Solicitações manuais podem não ser aprovadas imediatamente.

O acesso é concedido ao usuário individual, não automaticamente à organização.

## 2. Criar um token somente de leitura

1. Abra <https://huggingface.co/settings/tokens>.
2. Clique em **Create new token**.
3. Nome sugerido: `pfc-modelos-meta`.
4. Escolha **Read**. Não é necessário token de escrita.
5. Copie o token `hf_...` uma única vez e não o salve no repositório.

## 3. Autenticar este projeto

Abra PowerShell na pasta `pfc1-segmentacao-mmu` e execute:

```powershell
$env:HF_HOME = (Get-Content "data/hf-home.txt" -Raw).Trim()
$pfcPython = (Get-Content "data/python-path.txt" -Raw).Trim()
& $pfcPython -c "from huggingface_hub import login; login()"
```

Cole o token quando o programa solicitar. A entrada não aparece na tela. Quando
perguntar sobre Git credentials, responda `n`; isso não é necessário para baixar
modelos.

## 4. Confirmar a liberação sem baixar os pesos grandes

```powershell
.\executar.ps1 verificar_acesso_meta.py
```

O resultado esperado para os dois modelos é `ACESSO OK`. Um `401` significa que
o login não foi feito nesse `HF_HOME` ou que o acesso ainda não foi concedido.
Um `403` normalmente significa que a conta autenticada não aceitou a licença.

## 5. Baixar pesos completos e testar inferência

Após `ACESSO OK`, baixe os checkpoints completos:

```powershell
.\executar.ps1 baixar_modelos.py
.\executar.ps1 validar_dinov3.py
```

O primeiro comando baixa os pesos de vários GB, não apenas `config.json`.
O segundo testa o DINOv3 offline em duas imagens reais e registra
`outputs/instalacao_2026-10-20/dinov3_smoke/validacao.json`. Espere
`status: inference_ok` e `finite: true`.

Comece com quatro imagens para verificar memória e instalação:

```powershell
.\executar.ps1 avaliar_sam3_1_ubipr.py --model-dir outputs/instalacao_2026-10-20/ubipr_smoke --local-files-only --limit 4 --output-dir outputs/novo_sam3_smoke
```

O comando usa os pesos já baixados e o manifesto local, sem precisar dos pesos
U-Net. Gera no diretório `outputs/novo_sam3_smoke`:

- `metricas.json`;
- `metricas_por_imagem.csv`;
- `amostras_visuais.png`.

Depois do smoke test, remova `--limit` para avaliar toda a partição de teste.
Na instalação de 20/10/2026, o ambiente está em `C:\Users\lucaz\pfc-tcc-venv`,
registrado em `data/python-path.txt`, para evitar os caminhos longos do OneDrive.
O reconhecimento com recorte U-Net ainda requer o checkpoint científico original
ou novo treinamento; consulte `INSTALACAO_LOCAL.md`. Como o SAM 3 tem cerca de
848 milhões de parâmetros e esta máquina possui GPU de 6 GB, comece com lote
unitário. Se ocorrer falta de memória, execute com `--device cpu`.
