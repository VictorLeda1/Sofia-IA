# Agente de frontend — Sofia IA

## Missão

Construir a etapa React da Sofia IA em `frontend/`, no mesmo repositório do backend Django/DRF. A interface é um chat de vendas simples, funcional e responsivo, conforme o [teste da Prohall](https://prohall.app.br/docs_prohall/teste-ia-vendas/).

## Quando começar

Inicie a implementação dos fluxos quando o contrato OpenAPI do backend estiver disponível. Consulte o Swagger e use os endpoints reais; não invente rotas nem copie regras de preço, frete ou estoque para o navegador. O backend é a fonte de verdade para carrinho, cupom, frete, pedido e PIX fictício.

## Escopo

- Conversa com a Sofia, incluindo indicador de resposta em andamento.
- Cards no chat com foto, nome, preço e ação de adicionar.
- Sacola visível com quantidades, cupom, frete, descontos e totais retornados pela API.
- Checkout com aviso permanente de ambiente de teste, resumo e dados fictícios.
- PIX claramente falso: QR Code, texto copia e cola, contador, expiração, renovação e botão para simular pagamento.
- Painel de debug opcional com ferramentas chamadas e argumentos quando a API fornecer esses dados.
- Estados de carregamento, erro, carrinho vazio e tela móvel.

Não implementar chamadas ao Gemini no frontend. Nunca incluir `GEMINI_API_KEY`, prompt interno ou segredos no bundle. O frontend usa somente a API Django.

## Impeccable

Use o [Impeccable](https://impeccable.style/#downloads) na criação e revisão da interface. O plugin não estava disponível quando este agente foi definido; a instalação indicada pelo site é `npx impeccable install` no projeto. Selecione instalação para Codex e escopo do projeto. Após instalar, siga as instruções retornadas pela ferramenta para criar o contexto do produto e revisar a interface. Não afirme que hooks ou verificações automáticas estão ativos sem conferir a configuração.

O teste prioriza a IA de vendas, então o design deve facilitar a conversa e a conclusão do pedido. Preserve a linguagem visual da Prohall e a leitura no celular. Não adicione telas ou animações que atrapalhem o fluxo.

## Critérios de conclusão

O React inicia pelos comandos do README, consome a API real, completa uma venda simulada de ponta a ponta e não expõe segredos. Faça uma verificação em desktop e celular; registre limitações dependentes da chave Gemini.
