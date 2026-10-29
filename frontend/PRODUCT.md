# Sofia IA — contexto para o frontend

## Produto

Um chat web de vendas de cosméticos capilares Prohall. A consultora Sofia entende o cabelo e o objetivo da cliente, recomenda produtos com fichas reais, monta a sacola, calcula frete e conduz até um PIX simulado. O ambiente inteiro é de teste.

## Pessoas e tarefa principal

Cliente em celular, conversando como no WhatsApp. Ela quer explicar uma necessidade capilar, comparar uma indicação, conferir frete e concluir um pedido fictício com pouco esforço. Quem avalia o teste precisa acompanhar o fluxo e verificar as ferramentas chamadas.

## Princípios de interface

- Conversa em primeiro plano; uma ação principal por etapa.
- Produto recomendado aparece junto da mensagem que o explica.
- Sacola e total são fáceis de encontrar sem encobrir a conversa.
- Valores, prazos, desconto e estoque vêm da API, nunca de cálculo no React.
- Aviso de ambiente de teste visível no checkout e no PIX.
- Texto legível e controles utilizáveis em celular.
- Identidade alinhada à Prohall, com interface simples como o desafio pede.

## Fluxo

Chat → card de produto → sacola → CEP e modalidade → checkout com dados fictícios → QR e copia e cola não pagáveis → pagamento simulado ou expiração e renovação.

## Estados que precisam de desenho

Carregamento da resposta da Sofia, erro de API ou Gemini indisponível, nenhum produto encontrado, sacola vazia, cupom inválido, CEP inválido, estoque insuficiente, pedido criado, PIX aguardando, expirado e pago.
