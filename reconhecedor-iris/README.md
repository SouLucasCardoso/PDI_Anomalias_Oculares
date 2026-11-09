# Íris · laboratório móvel

Protótipo privado para Samsung Galaxy S23 base, Android 15, com inferência no Dell G15. Não instala APK nem publica serviço. Câmera RGB do aparelho; não presume capacidade de reconhecimento de um sensor dedicado de íris.

**Documentação atualizada em 09/11/2026.** O cadastro permite dar um nome a cada novo olho e adicionar fotos a um registro escolhido explicitamente. Os [ensaios acadêmicos de oclusão](../pfc1-segmentacao-mmu/RESULTADO_GRADE_DENSA_2026-11-08.md) foram concluídos separadamente; suas taxas não representam desempenho das fotografias do S23. O motor deste demonstrador foi preservado.

## Organização e preparação

Esta é a pasta própria do reconhecedor. `app_celular/web/` contém a interface, `servidor.py` o serviço local e `store.py` o cadastro. Os iniciadores ficam nesta pasta. `app_celular/motor.py` é uma ponte para o [núcleo de inferência congelado](../pfc1-segmentacao-mmu/app_celular/motor.py): o código científico e os pesos continuam em `../pfc1-segmentacao-mmu/`. Essa separação preserva o identificador do motor e os descritores já cadastrados.

O clone do GitHub contém o código, **não** os datasets, pesos, cadastros ou ferramentas baixadas. Não é um aplicativo autossuficiente para uma máquina nova sem esses recursos. Prepare o [ambiente de pesquisa](../pfc1-segmentacao-mmu/TECNOLOGIAS_ATUAIS_2026-11-03.md) e obtenha os modelos pelas fontes e licenças registradas antes de usar o reconhecedor. O ambiente local existente não precisa ser retreinado.

Na primeira preparação, com internet, execute a partir desta pasta:

```powershell
$pfcPython=(Get-Content ../pfc1-segmentacao-mmu/data/python-sam3-atual.txt -Raw).Trim()
& $pfcPython -m pip install --no-deps --target .runtime/iris_mobile_deps -r requirements-app.txt
& $pfcPython app_celular/preparar_usb.py
& $pfcPython -m unittest test_app_celular -v
```

Os comandos instalam somente o gerador de QR e preparam as ferramentas USB em `.runtime/`, sem atualizar os pacotes da rodada científica. Depois da preparação dos recursos locais e do aparelho, a apresentação por USB não requer internet. Os atalhos antigos em `../pfc1-segmentacao-mmu/` continuam redirecionando para esta pasta.

## Apresentação por USB-C — opção principal

Não depende de internet, roteador, endereço IP da rede ou regra de firewall. O aplicativo permanece em `127.0.0.1:8787` no PC; `adb reverse` encaminha essa porta pelo cabo. Todos os modelos e recursos da página são locais. O servidor não altera nenhuma configuração do telefone.

Primeira configuração, feita pelo dono do celular:

1. Use um cabo USB-C **de dados**, conectando o S23 ao Dell. Desbloqueie o aparelho.
2. Nas Configurações do Samsung, abra **Sobre o telefone → Informações do software** e toque sete vezes em **Número de compilação** para disponibilizar as Opções do desenvolvedor, se ainda não estiverem disponíveis. O telefone pode pedir sua autenticação.
3. Nas **Opções do desenvolvedor**, habilite **Depuração USB**. Ao conectar, autorize o Dell no diálogo exibido pelo próprio Android. Isso concede comunicação de desenvolvimento ao computador; faça essa autorização somente no seu PC. O programa não confirma o diálogo por você.
4. No PC, abra **ABRIR_IRIS_USB.cmd** dentro desta pasta. Alternativa no PowerShell: `./conectar_app_usb.ps1`.
5. No navegador do S23, abra **http://127.0.0.1:8787**. Toque em **Conectar** com o código exibido. No PC, a mesma página pode ser aberta em **http://localhost:8787**.
6. Mantenha o cabo conectado durante o uso. Se desconectar ou reiniciar o telefone, execute o iniciador novamente: o encaminhamento USB precisa ser restabelecido.

Ao terminar, abra **FECHAR_IRIS_USB.cmd**. O script remove somente o encaminhamento de `8787` deste demonstrador e encerra seu servidor, preservando o cadastro. Desative a depuração USB no telefone quando não for mais usá-la.

Se o aparelho não aparecer como `device`, confira o cabo, desbloqueio e o diálogo de autorização. No Windows, pode ser necessário o [driver USB oficial da Samsung](https://developer.samsung.com/android-usb-driver). Nenhum driver foi instalado automaticamente. Se uma política do aparelho impedir depuração, use a alternativa Wi-Fi após a configuração autorizada da rede; o aplicativo não remove proteções do telefone.

Ferramentas preparadas: Android Platform-Tools **37.0.1 estável**. A versão 37.0.2 disponível no catálogo consultado é Canary e não foi adotada. Download oficial, checksum do catálogo, SHA-256 local e saída de `adb version` foram registrados na [verificação inicial](../pfc1-segmentacao-mmu/outputs/app_celular_2026-11-05/ANDROID_TOOLS.json). Novas preparações gravam seu registro em `outputs/app_celular_2026-11-05/`. O ADB deste demonstrador usa a porta local **5038** e sua configuração privada em `dados_app_celular/android`, sem encerrar servidores ADB de outros projetos.

## Alternativa: hotspot do próprio S23

Ative o roteador Wi-Fi no celular e conecte o Dell à rede criada. O tráfego das fotos é local; a inferência não consome dados móveis. Esse modo está implementado por `./iniciar_app_celular.ps1 -RedeLocal`, mas **a liberação de entrada no firewall não foi aplicada**: a revisão automática de aprovação rejeitou a mudança persistente sem autorização explícita. Não desative o firewall.

Depois de uma configuração de rede autorizada, o iniciador descobre o IPv4 atual do Dell e a página do PC apresenta o endereço e o QR Code corretos. O endereço da rede doméstica não deve ser salvo como se valesse no hotspot. Use uma rede confiável: o modo LAN usa HTTP e código de pareamento, sem criptografia do transporte. USB é a opção preparada para evitar essa dependência na apresentação.

## Primeiro experimento no telefone

1. Em **Cadastrar olho**, escolha o olho **da pessoa fotografada** (direito ou esquerdo).
2. Use **Abrir câmera**. A captura abre o aplicativo de câmera do Android; não depende de transmissão de vídeo ao vivo. Também pode escolher uma foto existente.
3. Arraste o quadro e ajuste o enquadramento para incluir um olho inteiro e as pálpebras. O recorte é feito na resolução original, antes de limitar o envio a 2560 px no maior lado. O restante da foto não é enviado.
4. Toque em **Analisar recorte no PC**. A primeira análise também carrega os modelos; as seguintes usam os modelos em memória. A página mostra as etapas reais de processamento.
5. Confira a região verde prevista. Se a segmentação estiver errada, descarte a captura e tente novamente. Se estiver adequada, escolha **Novo registro**, digite um nome para aquele olho (por exemplo, “Ana — direito”) e confirme a revisão para salvar. Cada nova captura começa com o nome vazio; nomes iguais aos de outro registro são recusados para evitar confusão.
6. Para mais fotos independentes do **mesmo olho**, escolha explicitamente **Adicionar foto** e selecione o registro que deve recebê-las. A lista mostra somente o mesmo lado do olho. Para outro registro, use **Novo registro** e escolha outro nome. Após salvar, **Fazer nova captura** limpa a foto e o formulário.
7. Mude para **Reconhecer** e tire **uma nova foto**. O aplicativo compara apenas com o mesmo lado do olho e a mesma versão do motor.
8. Confira a lista de candidatos e só então informe quem foi fotografado para registrar o teste. Inclua também pessoas não cadastradas para observar o comportamento; isso ainda não produz uma taxa de falsas aceitações, pois não há limiar para celular.

A captura RGB pode não apresentar textura suficiente para uma comparação estável. Os avisos de largura e foco são heurísticas de engenharia; não são critérios ISO ou medidas clínicas. A faixa polar depende de geometria automática aproximada e não constitui anotação anatômica da pupila. Nenhum percentual de área anatômica é exibido.

## Como interpretar

O resultado é uma **ordenação experimental por semelhança**, sem confirmação automática de identidade. Os escores não são probabilidades. Uma única pessoa cadastrada sempre será a única candidata quando a extração funcionar; isso não comprova reconhecimento. O hash da imagem normalizada bloqueia uma repetição exata da foto cadastrada como teste independente, mas não detecta todas as recodificações nem ataques de apresentação.

Foram reaproveitados, em leitura, o extrator visual oficial SAM3.1 com decodificador residual selecionado na época 8 e os nove componentes de identidade já existentes. Não é segmentação textual com o SAM original nem treinamento novo no telefone. A fusão mantém as padronizações e pesos relativos históricos **antes da normalização por consulta/galeria**; não transfere o limiar do banco acadêmico para o celular. Isso evita fabricar confiança em galerias pequenas. Falta calibração independente com fotos do S23 e identidades de desenvolvimento/avaliação separadas.

## Dados, acompanhamento e encerramento

- Página: `http://localhost:8787` no PC; `http://127.0.0.1:8787` no S23 após encaminhar USB.
- Log: `dados_app_celular/execucao.log`; falhas de inicialização: `stderr.log`.
- Cadastro, fotos recortadas, descritores e testes: `dados_app_celular/`, excluído do Git por `.gitignore` interno. A pasta fica dentro do workspace OneDrive: exclusão do Git **não** desativa eventual sincronização do OneDrive do usuário.
- A foto original completa fica no celular; o aplicativo armazena no PC o recorte, a máscara, a visualização e os descritores. Capturas ficam guardadas até serem descartadas ou excluídas. Cadastros exigem revisão visual.
- **Excluir pessoa e fotos** remove o cadastro dessa pessoa e limpa todos os testes e capturas avulsas para retirar referências a ela nos resultados. Não altera bancos de pesquisa, anotações clínicas ou pesos.
- **Renomear registro**, na Galeria, permite corrigir nomes salvos anteriormente. Mantém os identificadores, fotos, descritores e testes; resultados históricos podem preservar o nome utilizado quando foram calculados. O programa não tenta adivinhar a quem pertence uma foto nem reatribui capturas automaticamente.
- Suspender o PC interrompe temporariamente o processamento. Reinicie o aplicativo e restabeleça USB se necessário; os cadastros salvos persistem. Uma análise interrompida deve ser refeita.
- Não é um autenticador de segurança, não possui teste de vivacidade e não diagnostica anomalias.

## Antes de sair para apresentar

Teste **no S23 real**, com o mesmo cabo: cadastro, nova foto de reconhecimento, pessoa não cadastrada, desconexão/reconexão USB e funcionamento com Wi-Fi e dados móveis desligados. Deixe o Dell ligado à tomada e evite suspensão durante a demonstração. Faça uma primeira captura antes de apresentar para carregar os modelos. Guarde os arquivos necessários localmente, sem depender de placeholders do OneDrive.

As [verificações iniciais](../pfc1-segmentacao-mmu/outputs/app_celular_2026-11-05/RELATORIO.md) registram testes HTTP/isolamento com motor simulado e inferência real em imagens VAL existentes. A [reorganização foi verificada separadamente](outputs/RELATORIO_REORGANIZACAO_2026-11-05.md), com preservação exata dos 27 arrays comparados e do identificador do motor. Essas verificações não medem desempenho do S23. A inspeção visual automatizada do navegador não pôde ser realizada porque o host de Browser/Computer Use estava indisponível nesta sessão.

Fontes técnicas: [ADB e autorização USB](https://developer.android.com/tools/adb), [encaminhamento reverso](https://android.googlesource.com/platform/packages/modules/adb/+/HEAD/docs/user/adb.1.md), [Platform-Tools oficiais](https://developer.android.com/tools/releases/platform-tools), [captura de foto no HTML](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/capture), [restrições de câmera ao vivo](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).
