# Agente: Backend Sofia

## Papel

Construir e manter o backend Django + DRF da consultora Sofia. O frontend React fica em `frontend/`, separado no mesmo repositório.

## Etapas

1. Preservar e consultar o catálogo real em `data/produtos.json` e os critérios em `docs/criterios_recomendacao.md`.
2. Implementar regras determinísticas de carrinho, cupom, frete, estoque, pedido e PIX falso em `backend/commerce/`.
3. Integrar o Gemini e as ferramentas em `backend/sofia_ai/`, mantendo prompt em arquivo próprio e a chave somente no backend.
4. Expor API DRF com Swagger em `/api/docs/` e validar os cenários do desafio.

## Critérios de conclusão

- Nenhuma dependência de banco ou migração para operar a API.
- `.env` ignorado pelo Git; `.env.example` sem segredo.
- Casos de frete 5.6 e totais 6.2 testados com valores exatos.
- Um fluxo de pedido e PIX falso pode ser completado pela API.
- O README permite executar e inspecionar os endpoints.
