# Sofia Prohall · teste técnico

Aplicação demonstrativa da consultora capilar Sofia: API Django + DRF e interface React no mesmo repositório, em pastas separadas. Todo pedido, frete, estoque e PIX aqui é fictício.

## Estrutura

- `data/produtos.json`: 15 fichas da [loja Prohall](https://lojaprohall.com.br/collections/all), consultadas em **29/10/2026**. O preço vigente é `preco_promocional` quando existe; do contrário, `preco`.
- `docs/criterios_recomendacao.md`: quando cada produto faz sentido, limitações e justificativas para combinações.
- `backend/catalog/`: leitura do catálogo e preço vigente.
- `backend/commerce/`: funções determinísticas de estoque, carrinho, cupom, frete, pedido e PIX falso.
- `backend/sofia_ai/`: prompt em arquivo próprio, declarações e execução de ferramentas, orquestração do Gemini.
- `backend/api/`: rotas DRF, validação HTTP e documentação OpenAPI.
- `backend/tests/`: casos exatos do desafio e fluxo de API sem banco.
- `frontend/`: chat React, cards de produto, sacola, checkout, PIX e painel de debug. Veja `frontend/README.md`.
- `agents/`: instruções reutilizáveis dos agentes de backend e frontend; o agente de frontend usa o Impeccable instalado no projeto.

## Executar no Windows (PowerShell)

Requisitos: Python 3.11+ e uma chave de teste Gemini fornecida pela Prohall para usar o chat. As demais rotas funcionam sem a chave.

```powershell
cd 'C:\Users\victo\projetos\Sofia IA'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edite **somente** `backend/.env` e preencha `GEMINI_API_KEY`. Não coloque a chave no frontend, no código, no Git, em prints ou no vídeo. O arquivo `.env` está no `.gitignore`; `.env.example` não contém segredo. `GEMINI_MODEL` tem padrão `gemini-3.8-flash`, o único modelo permitido pelo desafio. A chave ainda não foi fornecida, então a chamada real ao Gemini está pendente de validação.

```powershell
cd backend
python manage.py check
python manage.py test
python manage.py runserver 8000
```

Em outro terminal, rode o frontend:

```powershell
cd 'C:\Users\victo\projetos\Sofia IA\frontend'
npm install
npm run dev
```

Abra `http://127.0.0.1:5173`. O Vite encaminha `/api` ao Django; o navegador mantém o cookie de sessão. O frontend não lê a chave Gemini.

Não rode `migrate`: a API não usa banco, models ou tabelas. Abra [Swagger](http://127.0.0.1:8000/api/docs/) para ver e testar os endpoints. O schema também está em `/api/schema/` e em `backend/schema.yaml` como referência gerada.

## Rotas

Todas começam com `/api/` e usam barra final.

| Método e caminho | Função |
|---|---|
| `GET products/` e `GET products/{id}/` | Catálogo e ficha completa |
| `GET session/` | Carrinho, mensagens, chamadas de ferramentas e pedidos da sessão |
| `POST chat/` | Conversa Gemini com function calling (`{"message":"..."}`) |
| `POST cart/items/` | Adicionar (`{"id":"PH-004","quantidade":1}`) |
| `DELETE cart/items/{id}/` | Remover tudo ou `{"quantidade":1}` |
| `POST coupon/` | Aplicar (`{"codigo":"PROHALL10"}`) |
| `POST shipping/` | Frete do carrinho (`{"cep":"01001-000","modalidade_frete":"expressa"}`); modalidade opcional |
| `POST orders/` | Criar pedido com dados fictícios |
| `GET orders/{id}/` | Consultar status e expiração |
| `POST orders/{id}/pix/` | Criar ou renovar PIX falso |
| `POST orders/{id}/simulate-payment/` | Marcar pagamento simulado |

O navegador mantém o cookie `sofia_session` HttpOnly. Para consumir a API do React em `localhost:5173`, use `fetch(..., { credentials: 'include' })`. As respostas trazem dinheiro em **centavos** (`total_pix_centavos`, `valor_frete_centavos` etc.), evitando erros de ponto flutuante. O PIX traz `pix.texto`, `pix.expira_em` e `qr_data_url`. O texto começa com `PIX-TESTE` e termina em `NAO-PAGAVEL`; não é BR Code nem contém chave PIX real.

Exemplo de checkout:

```json
{
  "nome": "Ana Teste",
  "email": "ana@example.com",
  "cep": "01001-000",
  "endereco": "Rua Exemplo",
  "numero": "10",
  "complemento": "Apto 4",
  "modalidade_frete": "economica"
}
```

O pedido pode ser criado por essa rota ou pela Sofia usando `finalizar_pedido`. Os dois caminhos usam a mesma função em `commerce/`.

## Combinações úteis

| Produtos | Por que se complementam |
|---|---|
| PH-001 Select Blond + PH-008 Equalize Mask | A ficha da Select Blond orienta usar a Equalize Mask após o procedimento para equilibrar o pH. |
| PH-004 Shampoo Biomask + PH-005 Máscara Biomask | A ficha da máscara orienta lavar previamente com o shampoo Biomask. |
| PH-014 Twist Curls + PH-015 Raízes & Vibes 3ABC | A máscara hidrata fios cacheados; o creme sem enxágue ajuda a definir cachos 3ABC após a lavagem. |

Essas combinações dependem da necessidade da cliente. Consulte `docs/criterios_recomendacao.md` para indicações e cuidados.

## Decisões e limites desta etapa

- Estado guardado em memória por sessão de navegador. **Reiniciar o processo apaga carrinho, conversa e pedidos.** Use um único processo para o teste; múltiplos workers não compartilham memória.
- O catálogo resumido entra no prompt, e a IA usa `detalhar_produto` para consultar a ficha completa. Isso reduz o contexto inicial sem retirar informações que ela precise conferir.
- O código valida todos os argumentos das ferramentas. Erros de validação voltam à IA para que ela se corrija; os cálculos nunca são feitos pelo modelo.
- O estoque é fictício; `PH-010` tem duas unidades para testar escassez verdadeira.
- O peso de frete de `PH-007` foi estimado em 300 g porque o cadastro da loja informa 50 g para uma máscara de 250 g. O catálogo marca `peso_estimado: true`.
- O modo de uso da `PH-007` não está detalhado na loja, e o da `PH-014` é ambíguo sobre enxágue. A Sofia deve reconhecer esses limites.
- Não há pagamento real, integração logística, persistência ou autenticação de clientes. O vídeo e as três conversas exportadas dependem da chave Gemini para demonstrar uma venda real do começo ao fim.

## Verificação

`python manage.py test` cobre os seis resultados da seção 5.6, o cálculo da seção 6.2, cupom que deixa de valer após remoção, estoque, CEP inválido, expiração/renovação do PIX, fluxo HTTP e uma chamada simulada de ferramenta do Gemini. `python manage.py spectacular --validate --file schema.yaml` valida o Swagger.

No frontend, `npm run build` verifica a compilação de produção. O agente de frontend usou o [Impeccable](https://impeccable.style/#downloads) para revisar a interface; instruções de instalação e uso estão em `frontend/README.md`.
