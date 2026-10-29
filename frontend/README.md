# Sofia IA — frontend React

## Rodar

Com o backend Django em `http://127.0.0.1:8000`:

```bash
cd frontend
npm install
npm run dev
```

Abra `http://127.0.0.1:5173`. O Vite encaminha `/api` ao Django e mantém o cookie de sessão. Para um backend em outro endereço, defina `VITE_API_BASE_URL` antes de iniciar; essa variável contém apenas a URL pública da API, nunca a chave Gemini.

```bash
npm run build
```

O chat chama somente a API Django. Produto, preço, cupom, frete, total e pedido vêm do backend. Sem `GEMINI_API_KEY` configurada no backend, o envio de mensagem mostra o erro da API; a chave não entra no frontend.

## Impeccable

Impeccable foi instalado no escopo do projeto em `.agents/` por `npx impeccable install --providers=codex --scope=project --yes`. O contexto de produto está em `PRODUCT.md`. O detector foi executado após a implementação e não retornou achados. Os hooks instalados ainda dependem da confiança/configuração do Codex para rodar automaticamente; a instalação por si só não os ativa.

Fonte: [instalação do Impeccable](https://impeccable.style/#downloads).
