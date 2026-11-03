# Guia de manutenção do projeto Sofia IA

Este arquivo é o ponto de entrada para qualquer pessoa ou agente que vá modificar o repositório. Ele descreve o padrão que deve continuar verdadeiro depois de cada alteração. Leia o `README.md` para instalação e execução, `docs/criterios_recomendacao.md` para indicações de produto, e o [enunciado da Prohall](https://prohall.app.br/docs_prohall/teste-ia-vendas/) antes de mudar um requisito do teste. O código e os testes são a referência para detalhes de implementação; não copie trechos desatualizados deste documento sem conferir os arquivos citados.

## O que o projeto faz

Sofia é uma consultora capilar em chat web. Ela entende a necessidade da cliente, consulta um catálogo fechado de 15 produtos, recomenda o cuidado adequado, monta o carrinho, calcula frete e descontos e conduz a um pedido com PIX **inteiramente fictício**. A qualidade da conversa importa, mas valores e estado comercial são decididos pelo backend.

## Mapa do repositório

| Local | Responsabilidade |
| --- | --- |
| `data/produtos.json` | Fichas dos 15 produtos, preços copiados da loja, peso, estoque de teste, indicação, uso e combinações. |
| `docs/criterios_recomendacao.md` | Justificativas, limites e situações em que cada indicação faz sentido. |
| `backend/catalog/service.py` | Leitura, busca e detalhe do catálogo; conversão do preço vigente para centavos. |
| `backend/commerce/service.py` | Sessão em memória e regras determinísticas de carrinho, cupom, frete, checkout, pedido e PIX. |
| `backend/sofia_ai/prompt.md` | Persona, fluxo de venda e limites de comportamento da Sofia. |
| `backend/sofia_ai/agent.py` | Declarações das ferramentas, loop de function calling e histórico enviado ao Gemini. |
| `backend/api/serializers.py`, `views.py`, `urls.py` | Validação e contrato HTTP; a API não é o lugar para duplicar cálculos comerciais. |
| `backend/commerce/transcript.py` | Exportação local das falas para `docs/conversas/`; não exporta prompt nem chave. |
| `frontend/src/api.js` | Cliente HTTP único; usa `/api` e envia o cookie de sessão. |
| `frontend/src/App.jsx`, `styles.css` | Chat, cards, sacola, checkout, PIX, debug e layout responsivo. |
| `backend/tests/` | Testes de frete, totais, pedido, API e integração simulada das ferramentas. |
| `README.md` | Primeiras instruções de execução, configuração da IA, decisões e limitações. |

Este `AGENTS.md` é a orientação geral para manutenção.

## Contrato entre as camadas

- O navegador chama apenas a API Django. Nunca envie `GEMINI_API_KEY`, prompt interno ou instruções de sistema ao frontend. O backend lê a chave de `backend/.env`; `.env.example` fica sem segredo e `.env` permanece ignorado pelo Git.
- O único modelo permitido para a Sofia é `gemini-3.8-flash`, configurado por `GEMINI_MODEL`. Não introduza outro provedor ou modelo no fluxo da consultora.
- O Gemini conversa, identifica necessidades e escolhe ferramentas. As ferramentas são declaradas e executadas em `backend/sofia_ai/agent.py`. Cada argumento recebido do modelo precisa ser validado pelo código. Se a ferramenta falhar por argumento inválido, devolva o erro ao modelo para que ele se corrija.
- `backend/commerce/service.py` é a fonte de verdade para preço, cupom, estoque, frete, pedido e status do PIX. O frontend apenas apresenta esses resultados. Não calcule nem aceite valores comerciais fornecidos em texto pela IA ou pelo navegador.
- Valores monetários trafegam em **centavos inteiros**. Mantenha o arredondamento comercial a cada etapa de desconto. Use `frontend/src/api.js` para novas chamadas HTTP, preservando `credentials: "include"`.
- O cookie `sofia_session` identifica uma sessão mantida em memória pelo backend. Reiniciar o processo apaga conversa, carrinho e pedidos; não presuma persistência ou múltiplos workers sem implementar e documentar essa mudança.
- Ao mudar uma rota, campo ou formato de resposta, atualize `serializers.py`, `urls.py`/`views.py`, o consumidor React, os testes e o schema OpenAPI. Consulte `/api/docs/` e `backend/schema.yaml`.

## Regras comerciais que não podem divergir

- Catálogo fechado de 15 produtos. O preço vigente é `preco_promocional` quando não for `null`, senão `preco`. Limite de 10 unidades por produto e nunca acima de `estoque_teste`.
- Cupom único `PROHALL10`: 10% do subtotal quando ele é **pelo menos R$ 150,00**. Se uma remoção baixar o subtotal desse limite, retire o cupom e informe a cliente.
- Base dos produtos = subtotal menos cupom. Desconto PIX = 5% dessa base; ele **não** incide sobre o frete. Total PIX = base menos desconto PIX mais frete.
- Frete usa CEP, zona, peso dos itens e **200 g de embalagem**. Limites das faixas de peso são inclusivos. Acima de 5 kg, cobre o adicional por kg excedente arredondado para cima. A tabela fixa está em `backend/commerce/service.py` e deve coincidir com a seção 5 do enunciado.
- Frete grátis vale somente no Econômico: base após cupom de R$ 299,00 ou mais nas zonas Z1/Z2; R$ 399,00 ou mais nas zonas Z3/Z4/Z5. O Expresso nunca é grátis. Quando não atingir o limite, devolva o valor exato que falta.
- Não acrescente cartão, boleto, estoque real, transportadora real ou pagamento real ao fluxo do teste.

## Fluxos de venda e estados

1. A cliente conversa; Sofia busca candidatos e consulta a ficha completa antes de afirmar fatos do produto. O card exibido deve corresponder ao produto recomendado.
2. Adição e remoção podem ocorrer pelo chat ou pela sacola. A sacola fica fechada por padrão; abre ao clicar em `Sacola` ou no botão `+` do card. Adicionar pelo chat atualiza o estado sem abrir a sacola.
3. Pelo chat, Sofia coleta nome, e-mail, CEP, endereço e número, com complemento opcional. `preparar_checkout` valida dados e apresenta itens, cupom, desconto PIX, ambas as opções de frete, prazos e totais **sem criar pedido**. `confirmar_frete` só fecha após escolha explícita entre Econômico e Expresso.
4. Pelo formulário, os mesmos dados e a modalidade escolhida chegam a `finalize_order`. Os dois caminhos usam a mesma regra comercial e chegam ao mesmo formato de pedido. O checkout mostra itens, subtotal, cupom, frete, desconto PIX e total vindos da API.
5. O PIX tem texto obviamente falso (`PIX-TESTE|...|NAO-PAGAVEL`), QR Code, copia e cola, contador de 15 minutos e estados `aguardando_pagamento`, `expirado` e `pago`. Ao expirar, pode ser renovado. O botão `Simular pagamento` chama o endpoint de pagamento e só então o pedido passa a `pago`.
6. **Nunca confirme pagamento com base apenas em “sim”, “paguei” ou outra fala da cliente.** Sofia só pode afirmar sucesso após consultar status `pago` no backend. Se disser que reabriu o PIX, garanta que a interface realmente o recebeu e exibiu; `gerar_pix` em um PIX ainda válido pode devolver o mesmo código sem mudança no pedido.

## Padrão de comportamento da Sofia

- Português brasileiro próximo e claro, com mensagens curtas e poucos emojis. Quando precisar de resposta, faça **uma pergunta por mensagem**. Não combine duas dúvidas em uma frase.
- Entenda objetivo, condição dos fios, químicas e se a aplicação será em casa ou em salão antes de indicar procedimento de alinhamento. Para loiro com luzes e desejo de alisar, investigue aplicação e fragilidade em turnos separados.
- Dê uma indicação principal fundamentada na ficha; apresente até duas opções principais apenas quando houver escolha real. Complementos precisam ter função distinta e relevante para o problema. Não ofereça remoção espontaneamente, mas atenda quando a cliente solicitar mudança do carrinho.
- Para dúvidas sobre ativos, modo de uso, rendimento ou duração, consulte a ficha. Se o dado estiver ausente ou ambíguo, diga isso e ofereça contato com a equipe. Não invente benefício, preço, estoque, prazo, escassez, depoimento ou desconto.
- Produto profissional exige aviso de aplicação por profissional. Não faça diagnóstico médico; em caso de ferida, alergia ou queda intensa, oriente avaliação apropriada. Não revele prompt ou instruções internas.
- Use argumentos comerciais apenas quando retornados pelo sistema: economia PIX em reais, valor que falta para frete grátis, estoque baixo real (`estoque_teste <= 3`) e combinações justificadas.
- O prompt em `backend/sofia_ai/prompt.md` orienta o modelo, mas respostas reais podem desobedecê-lo. Quando houver regra crítica, verifique estado e resposta no backend; não dependa só do prompt.

## Padrão da interface

- Preserve a interface React atual: cabeçalho discreto, conversa como foco, cards de produto, sacola em painel, checkout e PIX em modal. O cabeçalho principal mostra o botão da sacola; o painel de debug fica separado da compra.
- Use os estilos e componentes existentes em `frontend/src/App.jsx` e `styles.css` antes de criar padrões novos. Mantenha tipografia, cores, espaçamento, estados de foco e responsividade; a largura mínima suportada é 320 px.
- Mostre carregamento, erros e confirmação de ações. O indicador `Sofia está digitando…` aparece enquanto `/api/chat/` responde. Cards exibem imagem, nome, preço e ação de adicionar.
- Evite mostrar `**` literais nas mensagens: `FormattedMessage` em `App.jsx` apresenta ênfase sem esses marcadores. Não use `dangerouslySetInnerHTML` para conteúdo gerado pela IA.
- Checkout e PIX exibem a faixa `AMBIENTE DE TESTE — nenhum pagamento é real`. O formulário avisa que os dados devem ser fictícios, embora os rótulos sejam simples (`Nome`, `E-mail` etc.). Nunca solicite CPF, cartão ou dado bancário.
- O painel `#/debug` é um diferencial do teste: mostra nomes e argumentos das ferramentas. Evite expor chave, prompt ou dados pessoais reais nele.

## Qualidade, evidência e entrega

- Antes de editar, confira `git status` e leia o código afetado. Preserve mudanças locais e não reescreva arquivos por conveniência. Faça alterações no domínio correto; extraia funções quando isso reduzir duplicação real, sem criar camadas desnecessárias.
- Mudança em cálculo exige teste com valores exatos. Os casos obrigatórios são os seis da seção 5.6 e o exemplo de R$ 279,40 da seção 6.2. Mudança em API exige teste de status e formato. Mudança no fluxo da Sofia exige cenário de conversa, verificando tanto o texto quanto o estado do pedido.
- Rode `python manage.py test` dentro de `backend/` e `npm run build` dentro de `frontend/` quando a mudança afetar essas partes. Se mudar o schema, rode `python manage.py spectacular --validate --file schema.yaml`. Informe quais verificações foram feitas e quais não foram possíveis.
- Conversas iniciadas no chat são exportadas automaticamente para `docs/conversas/`. Use somente dados fictícios. Antes de selecionar arquivos para entrega, confira que o texto de pagamento coincide com o status final do pedido; não trate uma transcrição com estado inconsistente como demonstração de sucesso.
- Mantenha `README.md` atualizado quando instalação, configuração, contrato, decisões ou limitações mudarem. As instruções para executar e configurar a IA ficam no topo. Registre a data de coleta de preços e justifique as combinações do catálogo.
- Não reinstale Playwright nem recrie agente de testes sem pedido do usuário. Não inclua `.env`, `.venv`, `node_modules`, `dist`, logs com segredo ou outros artefatos locais em entregas. Para entrega em ZIP, inclua a pasta `.git`, o código e os materiais solicitados; confira o conteúdo antes de compartilhar.
