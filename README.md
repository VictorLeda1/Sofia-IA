# Sofia Prohall · teste técnico

Consultora capilar com API Django/DRF e chat React. Pedidos, fretes e pagamentos são simulações.

## Executar e configurar a IA

Requisitos: **Python 3.11+**, **Node.js 20+** com npm e uma chave Gemini válida para usar o chat. A chave fica exclusivamente no backend. O modelo permitido pelo [teste da Prohall](https://prohall.app.br/docs_prohall/teste-ia-vendas/) é `gemini-3.8-flash`.

No PowerShell, a partir da raiz do repositório, instale o backend e crie o arquivo de ambiente:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edite `backend/.env` e preencha `GEMINI_API_KEY` com sua chave. Mantenha `GEMINI_MODEL=gemini-3.8-flash`. O `.env` está no `.gitignore`; nunca coloque a chave no frontend ou no Git. Para iniciar a API:

```powershell
cd backend
python manage.py check
python manage.py runserver 8000
```

Em outro terminal, a partir da raiz do repositório, instale e inicie o frontend:

```powershell
cd frontend
npm install
npm run dev
```

Abra `http://127.0.0.1:5173` para conversar com Sofia e [Swagger](http://127.0.0.1:8000/api/docs/) para explorar a API. O Vite encaminha `/api` ao Django. Não execute `migrate`: esta etapa não usa banco de dados.

## Estrutura

- `backend/catalog/`: catálogo e preço vigente.
- `backend/commerce/`: estoque, carrinho, cupom, frete, pedidos e PIX simulado, com cálculos determinísticos.
- `backend/sofia_ai/`: prompt separado, Gemini e ferramentas de venda.
- `backend/api/`: rotas DRF e documentação OpenAPI; `/api/debug/tools/` lista ferramentas e argumentos da sessão.
- `backend/tests/`: testes do cálculo, da API e do uso das ferramentas.
- `frontend/`: chat, cards, sacola, formulário de checkout, PIX e página `#/debug`.
- `data/produtos.json`: as 15 fichas usadas pela aplicação.
- `docs/criterios_recomendacao.md`: critérios de indicação, limites e combinações em detalhe.
- `docs/conversas/`: transcrições em `.txt`, uma por sessão de chat. São atualizadas automaticamente e aparecem como arquivos novos no Git para você escolher quais incluir na entrega. Use apenas dados fictícios nas conversas.
- `agents/`: instruções dos agentes de backend e frontend.

## Decisões técnicas e regras relevantes

O chat e o formulário são **dois caminhos para o mesmo pedido**. Pelo chat, Sofia prepara o resumo, recebe a escolha do frete e gera o PIX de teste. Pelo formulário, a pessoa escolhe o frete e cria o pedido diretamente. Ambos usam as mesmas funções em `backend/commerce/`. O resumo do formulário lê os valores devolvidos pela API.

Valores monetários são enviados em centavos. O cupom `PROHALL10` dá 10% sobre os produtos quando o subtotal chega a R$ 150,00. O PIX reduz 5% do valor dos produtos após o cupom, sem reduzir o frete. A entrega Econômica fica grátis conforme a faixa do CEP e o valor dos produtos após cupom; a Expressa mantém sua tarifa. O backend calcula estoque, descontos, frete e total; o Gemini consulta as ferramentas e não deve calcular valores por conta própria.

O catálogo resumido entra no contexto da IA, e `detalhar_produto` consulta as fichas completas antes de uma indicação. A aplicação usa um cookie HttpOnly para identificar a sessão em memória. O PIX é obviamente falso, não pagável e expira em 15 minutos; o botão de simulação muda o status do pedido para `pago`.

### Combinações úteis

| Produtos | Por que se complementam |
|---|---|
| PH-001 Select Blond + PH-008 Equalize Mask | A ficha da Select Blond orienta usar a Equalize Mask após o procedimento para equilibrar o pH. |
| PH-004 Shampoo Biomask + PH-005 Máscara Biomask | A ficha da máscara orienta lavar previamente com o shampoo Biomask. |
| PH-014 Twist Curls + PH-015 Raízes & Vibes 3ABC | A máscara hidrata fios cacheados; o creme sem enxágue ajuda a definir cachos 3ABC após a lavagem. |

Essas combinações dependem da necessidade da cliente. Consulte [os critérios detalhados](docs/criterios_recomendacao.md) para indicações e cuidados.

## Preços e catálogo

As fichas públicas da [loja Prohall](https://lojaprohall.com.br/collections/all) foram consultadas em **29/10/2026**. O preço vigente usa `preco_promocional` quando existe; caso contrário, `preco`. São dados de referência do teste, sujeitos a mudanças na loja.

## Testes

```powershell
cd backend
python manage.py test
python manage.py spectacular --validate --file schema.yaml
```

Para conferir a compilação da interface:

```powershell
cd frontend
npm run build
```

Os testes do backend cobrem cenários de frete e totais do desafio, cupom, estoque, CEP inválido, PIX, fluxo HTTP, chamadas de ferramentas e o roteiro de perguntas em etapas para cabelo loiro com luzes e interesse em alisar.

## Limitações

O estado vive apenas na memória de um processo: reiniciar o backend apaga conversa, sacola e pedidos; múltiplos workers não compartilham sessões. Não há banco, autenticação de clientes, logística ou pagamento real. O peso de frete de PH-007 foi estimado em 300 g porque o cadastro da loja informa 50 g para uma máscara de 250 g. A ficha de PH-007 não detalha o modo de uso, e a de PH-014 é ambígua sobre enxágue; Sofia deve reconhecer esses limites.
