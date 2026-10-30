import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Bug,
  Check,
  Copy,
  LoaderCircle,
  Minus,
  Plus,
  Send,
  ShoppingBag,
  X,
} from "lucide-react";
import { request } from "./api";

const money = (cents) =>
  cents == null
    ? "—"
    : (cents / 100).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
      });
const digits = (value) => String(value || "").replace(/\D/g, "");
const emptyCheckout = {
  nome: "",
  email: "",
  cep: "",
  endereco: "",
  numero: "",
  complemento: "",
  modalidade_frete: "economica",
};
const welcome = {
  role: "assistant",
  text: "Oi! Eu sou a Sofia 💕 Me conta: o que você gostaria de melhorar no seu cabelo?",
};

function FormattedMessage({ text }) {
  return String(text || "")
    .split(/(\*\*[\s\S]+?\*\*)/g)
    .map((part, index) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <strong key={index}>{part.slice(2, -2)}</strong>
      ) : (
        <span key={index}>{part.replace(/\*\*/g, "")}</span>
      ),
    );
}

function ProductCard({ item, onAdd, busy }) {
  return (
    <article className="product-card">
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer"
        className="product-image"
      >
        <img src={item.imagem_url} alt={item.nome} loading="lazy" />
      </a>
      <div className="product-card-body">
        <span className="product-kind">
          {item.uso === "profissional"
            ? "Uso profissional"
            : item.categoria?.replace("_", " ")}
        </span>
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="product-name"
        >
          {item.nome}
        </a>
        <div className="product-foot">
          <strong>
            {money(
              item.preco_vigente_centavos ??
                Math.round((item.preco_promocional ?? item.preco) * 100),
            )}
          </strong>
          <button
            aria-label={`Adicionar ${item.nome} à sacola`}
            onClick={() => onAdd(item.id)}
            disabled={busy}
          >
            <Plus size={17} />
          </button>
        </div>
      </div>
    </article>
  );
}

function PriceLine({ label, value, strong = false, negative = false }) {
  return (
    <div className={`price-line ${strong ? "strong" : ""}`}>
      <span>{label}</span>
      <span>
        {value == null ? "—" : `${negative ? "− " : ""}${money(value)}`}
      </span>
    </div>
  );
}

function FreeShippingNote({ quote, coupon }) {
  if (!quote) return null;
  const base = coupon ? "em produtos após o cupom" : "em produtos";
  return (
    <p className="shipping-explanation">
      {quote.opcoes.economica.gratis
        ? `Frete Econômico grátis a partir de ${money(quote.limite_frete_gratis_centavos)} ${base} para este CEP.`
        : `Faltam ${money(quote.faltam_frete_gratis_centavos)} ${base} para o frete Econômico grátis.`}
    </p>
  );
}

function CheckoutPreview({ preview, onSelect, busy, active }) {
  const { cliente, resumo, totais_por_frete: shipping } = preview;
  return (
    <section className="chat-checkout-preview" aria-label="Resumo do pedido de teste">
      <strong>Resumo antes de finalizar</strong>
      <small>
        {cliente.nome} · {cliente.email} · CEP {cliente.cep}
        <br />
        {cliente.endereco}, {cliente.numero}
        {cliente.complemento ? ` · ${cliente.complemento}` : ""}
      </small>
      <div className="preview-items">
        {resumo.items.map((item) => (
          <div key={item.id}>
            <span>{item.quantidade}× {item.nome}</span>
            <b>{money(item.total_centavos)}</b>
          </div>
        ))}
      </div>
      <PriceLine label="Subtotal" value={resumo.subtotal_centavos} />
      {resumo.cupom && (
        <PriceLine label={`Cupom ${resumo.cupom}`} value={resumo.desconto_cupom_centavos} negative />
      )}
      <PriceLine label="Desconto PIX" value={resumo.desconto_pix_centavos} negative />
      <PriceLine label="Produtos no PIX" value={resumo.base_produtos_centavos - resumo.desconto_pix_centavos} />
      <FreeShippingNote quote={resumo.frete} coupon={resumo.cupom} />
      <p>Qual frete você prefere?</p>
      <div className="preview-shipping">
        {[["economica", "Econômico"], ["expressa", "Expresso"]].map(([mode, label]) => (
          <button key={mode} type="button" disabled={busy || !active} onClick={() => onSelect(label)}>
            <span><strong>{label}</strong><small>{shipping[mode].prazo_dias_uteis} dias úteis · frete {money(shipping[mode].frete_centavos)}{shipping[mode].frete_centavos === 0 ? " (grátis)" : ""}</small></span>
            <b>Total do pedido no PIX: {money(shipping[mode].total_pix_centavos)}</b>
          </button>
        ))}
      </div>
      <small>Pedido e pagamento são apenas simulações.</small>
    </section>
  );
}

function DebugPage({ calls, error, onBack, onRefresh }) {
  return (
    <main className="debug-page">
      <div className="debug-page-head">
        <button type="button" className="debug-back" onClick={onBack}><ArrowLeft size={17} /> Voltar para a conversa</button>
        <button type="button" className="debug-refresh" onClick={onRefresh}>Atualizar</button>
      </div>
      <h1>Painel de debug</h1>
      <p>Ferramentas chamadas pela Sofia nesta conversa e os argumentos enviados em cada chamada.</p>
      {error && <p className="inline-error" role="alert">{error}</p>}
      {!error && calls.length === 0 && <p className="debug-empty">Nenhuma ferramenta foi chamada nesta conversa.</p>}
      <div className="debug-calls">
        {calls.map((call, index) => (
          <article className="debug-call" key={index}>
            <div><span>Chamada {index + 1}</span><strong>{call.name}</strong></div>
            <pre>{JSON.stringify(call.args || {}, null, 2)}</pre>
          </article>
        ))}
      </div>
    </main>
  );
}

function Cart({
  cart,
  onAdd,
  onRemove,
  onCoupon,
  onShipping,
  onCheckout,
  busy,
  couponInput,
  setCouponInput,
  cepInput,
  setCepInput,
}) {
  const [localError, setLocalError] = useState("");
  const submit = async (action) => {
    setLocalError("");
    try {
      await action();
    } catch (error) {
      setLocalError(error.message);
    }
  };
  if (!cart?.items?.length)
    return (
      <div className="empty-cart">
        <ShoppingBag size={26} strokeWidth={1.6} />
        <h3>Sua sacola está vazia</h3>
        <p>
          Converse com a Sofia para encontrar o cuidado certo para o seu cabelo.
        </p>
      </div>
    );
  return (
    <div className="cart-body">
      <div className="cart-items">
        {cart.items.map((item) => (
          <div className="cart-item" key={item.id}>
            <img src={item.imagem_url} alt="" />
            <div className="cart-item-main">
              <strong>{item.nome}</strong>
              <span>{money(item.preco_unitario_centavos)}</span>
              <div className="quantity">
                <button
                  onClick={() => submit(() => onRemove(item.id))}
                  disabled={busy}
                  aria-label={`Diminuir ${item.nome}`}
                >
                  <Minus size={13} />
                </button>
                <b>{item.quantidade}</b>
                <button
                  onClick={() => submit(() => onAdd(item.id))}
                  disabled={busy}
                  aria-label={`Aumentar ${item.nome}`}
                >
                  <Plus size={13} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <form
        className="inline-form"
        onSubmit={(event) => {
          event.preventDefault();
          submit(() => onCoupon(couponInput));
        }}
      >
        <label htmlFor="coupon">Cupom</label>
        <div>
          <input
            id="coupon"
            value={couponInput}
            onChange={(e) => setCouponInput(e.target.value)}
            placeholder="Código do cupom"
          />
          <button disabled={busy || !couponInput.trim()}>Aplicar</button>
        </div>
      </form>
      <form
        className="inline-form"
        onSubmit={(event) => {
          event.preventDefault();
          submit(() => onShipping(cepInput, "economica"));
        }}
      >
        <label htmlFor="cart-cep">Calcule sua entrega</label>
        <div>
          <input
            id="cart-cep"
            inputMode="numeric"
            value={cepInput}
            onChange={(e) => setCepInput(e.target.value)}
            placeholder="CEP de 8 dígitos"
          />
          <button disabled={busy || digits(cepInput).length !== 8}>
            Calcular
          </button>
        </div>
      </form>
      {localError && (
        <p className="inline-error" role="alert">
          {localError}
        </p>
      )}
      {cart.frete && (
        <div className="shipping-options">
          <div>
            <span>
              Econômica · {cart.frete.opcoes.economica.prazo_dias_uteis} dias
              úteis
            </span>
            <strong>
              {cart.frete.opcoes.economica.gratis
                ? "Grátis"
                : money(cart.frete.opcoes.economica.valor_centavos)}
            </strong>
          </div>
          <div>
            <span>
              Expressa · {cart.frete.opcoes.expressa.prazo_dias_uteis} dias
              úteis
            </span>
            <strong>{money(cart.frete.opcoes.expressa.valor_centavos)}</strong>
          </div>
        </div>
      )}
      <FreeShippingNote quote={cart.frete} coupon={cart.cupom} />
      <div className="cart-totals">
        <PriceLine label="Subtotal" value={cart.subtotal_centavos} />
        {cart.cupom && (
          <PriceLine
            label={`Cupom ${cart.cupom}`}
            value={cart.desconto_cupom_centavos}
            negative
          />
        )}
        <PriceLine
          label="Desconto no PIX"
          value={cart.desconto_pix_centavos}
          negative
        />
        <PriceLine label="Produtos no PIX" value={cart.base_produtos_centavos - cart.desconto_pix_centavos} />
        <PriceLine
          label={`Entrega ${cart.modalidade_frete || ""}`}
          value={cart.valor_frete_centavos}
        />
        <PriceLine
          label="Total do pedido no PIX"
          value={cart.total_pix_centavos}
          strong
        />
      </div>
      <button
        className="primary-button full"
        onClick={onCheckout}
        disabled={busy}
      >
        Finalizar pedido de teste <ArrowRight size={17} />
      </button>
    </div>
  );
}

function Checkout({ cart, initialCep, onClose, onShipping, onCreate, busy }) {
  const [form, setForm] = useState({
    ...emptyCheckout,
    cep: initialCep || "",
    modalidade_frete: cart?.modalidade_frete || "economica",
  });
  const [error, setError] = useState("");
  const quoteMatches =
    cart?.frete &&
    digits(form.cep) === digits(cart.frete.cep) &&
    cart.modalidade_frete === form.modalidade_frete;
  const field = (name, value) => setForm((old) => ({ ...old, [name]: value }));
  const quote = async (mode = form.modalidade_frete) => {
    setError("");
    try {
      await onShipping(form.cep, mode);
    } catch (e) {
      setError(e.message);
    }
  };
  const selectShipping = (mode) => {
    field("modalidade_frete", mode);
    if (digits(form.cep).length === 8) quote(mode);
  };
  const quotedCep =
    cart?.frete && digits(form.cep) === digits(cart.frete.cep);
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!quoteMatches) {
      setError(
        "Calcule a entrega para conferir o total antes de criar o pedido.",
      );
      return;
    }
    try {
      await onCreate(form);
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="modal checkout-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="checkout-title"
      >
        <div className="test-banner">
          AMBIENTE DE TESTE — nenhum pagamento é real
        </div>
        <button className="modal-close" onClick={onClose} aria-label="Fechar">
          <X size={20} />
        </button>
        <div className="modal-content">
          <h2 id="checkout-title">Finalizar pedido</h2>
          <p className="modal-intro">
            Use apenas dados fictícios neste formulário.
          </p>
          <div className="checkout-summary">
            <div className="checkout-summary-items">
              {cart.items.map((item) => (
                <div key={item.id}>
                  <span>{item.quantidade}× {item.nome}<small>{money(item.preco_unitario_centavos)} por unidade</small></span>
                  <strong>{money(item.total_centavos)}</strong>
                </div>
              ))}
            </div>
            <PriceLine label="Subtotal" value={cart.subtotal_centavos} />
            {cart.cupom && <PriceLine label={`Cupom ${cart.cupom}`} value={cart.desconto_cupom_centavos} negative />}
            <PriceLine label={`Frete ${form.modalidade_frete === "expressa" ? "Expresso" : "Econômico"}`} value={quoteMatches ? cart.valor_frete_centavos : null} />
            <PriceLine
              label="Desconto PIX"
              value={cart.desconto_pix_centavos}
              negative
            />
            <PriceLine
              label="Total no PIX"
              value={quoteMatches ? cart.total_pix_centavos : null}
              strong
            />
          </div>
          <form onSubmit={submit} className="checkout-form">
            <label>
              Nome
              <input
                required
                minLength="2"
                value={form.nome}
                onChange={(e) => field("nome", e.target.value)}
                placeholder="Ana Exemplo"
              />
            </label>
            <label>
              E-mail
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => field("email", e.target.value)}
                placeholder="ana@exemplo.com"
              />
            </label>
            <label>
              CEP para entrega
              <input
                inputMode="numeric"
                required
                pattern="[0-9]{5}-?[0-9]{3}"
                value={form.cep}
                onChange={(e) => field("cep", e.target.value)}
                placeholder="01001-000"
              />
            </label>
            <button
              type="button"
              className="text-button"
              onClick={() => quote()}
              disabled={busy || digits(form.cep).length !== 8}
            >
              Calcular opções de entrega
            </button>
            <fieldset className="freight-options">
              <legend>Escolha o frete</legend>
              {[
                ["economica", "Econômico"],
                ["expressa", "Expresso"],
              ].map(([mode, label]) => {
                const option = quotedCep ? cart.frete.opcoes[mode] : null;
                return (
                  <label className="freight-option" key={mode}>
                    <input
                      type="radio"
                      name="modalidade_frete"
                      value={mode}
                      checked={form.modalidade_frete === mode}
                      onChange={() => selectShipping(mode)}
                      disabled={busy || digits(form.cep).length !== 8}
                    />
                    <span>
                      <strong>{label}</strong>
                      <small>
                        {option
                          ? `${option.prazo_dias_uteis} dias úteis`
                          : "Calcule pelo CEP"}
                      </small>
                    </span>
                    <b>
                      {option
                        ? option.gratis
                          ? "Grátis"
                          : money(option.valor_centavos)
                        : "—"}
                    </b>
                  </label>
                );
              })}
            </fieldset>
            <label>
              Endereço
              <input
                required
                minLength="3"
                value={form.endereco}
                onChange={(e) => field("endereco", e.target.value)}
                placeholder="Rua Exemplo"
              />
            </label>
            <div className="field-pair">
              <label>
                Número
                <input
                  required
                  value={form.numero}
                  onChange={(e) => field("numero", e.target.value)}
                  placeholder="123"
                />
              </label>
              <label>
                Complemento
                <input
                  value={form.complemento}
                  onChange={(e) => field("complemento", e.target.value)}
                  placeholder="Opcional"
                />
              </label>
            </div>
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="primary-button full"
              disabled={busy || !quoteMatches}
            >
              {busy ? "Criando pedido…" : "Criar pedido de teste"}{" "}
              <ArrowRight size={17} />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

function Pix({ order, onClose, onRenew, onPay, busy }) {
  const [now, setNow] = useState(Date.now());
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const seconds = order.pix
    ? Math.max(0, Math.ceil((Date.parse(order.pix.expira_em) - now) / 1000))
    : 0;
  const expired =
    order.status === "expirado" ||
    (order.status === "aguardando_pagamento" && seconds === 0);
  const status =
    order.status === "pago"
      ? "Pagamento simulado confirmado"
      : expired
        ? "PIX de teste expirado"
        : "Aguardando simulação";
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(order.pix.texto);
      setCopied(true);
    } catch {
      setError(
        "Não foi possível copiar. Selecione o texto abaixo manualmente.",
      );
    }
  };
  const act = async (fn) => {
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="modal pix-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pix-title"
      >
        <div className="test-banner">
          AMBIENTE DE TESTE — nenhum pagamento é real
        </div>
        <button className="modal-close" onClick={onClose} aria-label="Fechar">
          <X size={20} />
        </button>
        <div className="modal-content">
          <h2 id="pix-title">PIX de mentira</h2>
          <p className="modal-intro">
            Este QR Code não pode ser pago em nenhum aplicativo bancário.
          </p>
          <div className="pix-order">Pedido {order.id}</div>
          <div className="pix-value">
            {money(order.resumo.total_pix_centavos)}
          </div>
          {order.qr_data_url && (
            <img
              className="qr-code"
              src={order.qr_data_url}
              alt="QR Code fictício e não pagável"
            />
          )}
          <div className="pix-status">
            {order.status === "pago" ? (
              <Check size={16} />
            ) : (
              <span className="status-dot" />
            )}
            {status}
          </div>
          {order.status === "aguardando_pagamento" && !expired && (
            <p className="countdown">
              Expira em {String(Math.floor(seconds / 60)).padStart(2, "0")}:
              {String(seconds % 60).padStart(2, "0")}
            </p>
          )}
          {order.pix && (
            <>
              <label className="copy-label" htmlFor="pix-text">
                Copia e cola fictício
              </label>
              <div className="copy-row">
                <input
                  id="pix-text"
                  readOnly
                  value={order.pix.texto}
                  onFocus={(e) => e.target.select()}
                />
                <button onClick={copy} aria-label="Copiar código PIX fictício">
                  <Copy size={17} />
                </button>
              </div>
              {copied && (
                <p className="copy-confirm">Código fictício copiado.</p>
              )}
            </>
          )}
          {error && (
            <p className="inline-error" role="alert">
              {error}
            </p>
          )}
          {expired && (
            <button
              className="primary-button full"
              disabled={busy}
              onClick={() => act(onRenew)}
            >
              Gerar outro PIX falso
            </button>
          )}
          {order.status === "aguardando_pagamento" && !expired && (
            <button
              className="primary-button full"
              disabled={busy}
              onClick={() => act(onPay)}
            >
              Simular pagamento
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState(() => window.location.hash === "#/debug" ? "debug" : "chat");
  const [debugCalls, setDebugCalls] = useState([]);
  const [debugError, setDebugError] = useState("");
  const [products, setProducts] = useState([]);
  const [session, setSession] = useState({
    cart: null,
    messages: [],
    debug: [],
    orders: [],
  });
  const [message, setMessage] = useState("");
  const [pendingMessage, setPendingMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState(false);
  const [error, setError] = useState("");
  const [couponInput, setCouponInput] = useState("");
  const [cepInput, setCepInput] = useState("");
  const [drawer, setDrawer] = useState(false);
  const [checkout, setCheckout] = useState(false);
  const [pix, setPix] = useState(null);
  const conversationRef = useRef(null);

  useEffect(() => {
    const syncPage = () => setPage(window.location.hash === "#/debug" ? "debug" : "chat");
    window.addEventListener("hashchange", syncPage);
    return () => window.removeEventListener("hashchange", syncPage);
  }, []);
  const refreshDebug = async () => {
    try {
      setDebugError("");
      const data = await request("/debug/tools/");
      setDebugCalls(data.calls);
    } catch (e) {
      setDebugError(e.message);
    }
  };
  useEffect(() => {
    if (page === "debug" && session.cart) refreshDebug();
  }, [page, session.cart]);

  const refresh = async () => {
    const data = await request("/session/");
    setSession(data);
    setCouponInput(data.cart?.cupom || "");
    setCepInput(data.cart?.frete?.cep || "");
    return data;
  };
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await request("/session/");
        const p = await request("/products/");
        if (!cancelled) {
          setSession(s);
          setProducts(p);
          setCouponInput(s.cart?.cupom || "");
          setCepInput(s.cart?.frete?.cep || "");
        }
      } catch (e) {
        if (!cancelled)
          setError(`Não foi possível carregar a Sofia: ${e.message}`);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  useLayoutEffect(() => {
    const conversation = conversationRef.current;
    if (conversation) conversation.scrollTop = conversation.scrollHeight;
  }, [session.messages, pendingMessage, typing, error]);
  useEffect(() => {
    if (!pix || pix.status !== "aguardando_pagamento" || !pix.pix) return;
    const id = setInterval(async () => {
      if (Date.now() >= Date.parse(pix.pix.expira_em)) {
        try {
          setPix(await request(`/orders/${pix.id}/`));
        } catch {}
      }
    }, 2000);
    return () => clearInterval(id);
  }, [pix]);
  const transact = async (fn) => {
    setBusy(true);
    setError("");
    try {
      const result = await fn();
      await refresh();
      return result;
    } finally {
      setBusy(false);
    }
  };
  const add = (id) =>
    transact(() =>
      request("/cart/items/", { method: "POST", body: { id, quantidade: 1 } }),
    );
  const addFromCard = async (id) => {
    try {
      await add(id);
      setDrawer(true);
    } catch (e) {
      setError(e.message);
    }
  };
  const remove = (id) =>
    transact(() =>
      request(`/cart/items/${id}/`, {
        method: "DELETE",
        body: { quantidade: 1 },
      }),
    );
  const coupon = (codigo) =>
    transact(() => request("/coupon/", { method: "POST", body: { codigo } }));
  const shipping = (cep, modalidade_frete = "economica") =>
    transact(() =>
      request("/shipping/", {
        method: "POST",
        body: { cep, modalidade_frete },
      }),
    );
  const sendMessage = async (value) => {
    const text = value.trim();
    if (!text || typing) return;
    setMessage("");
    setError("");
    setPendingMessage(text);
    setTyping(true);
    try {
      const response = await request("/chat/", {
        method: "POST",
        body: { message: text },
      });
      await refresh();
      setPendingMessage(null);
      if (
        response.active_order?.pix &&
        response.active_order.status !== "pago"
      ) {
        setPix(response.active_order);
        setCheckout(false);
      }
    } catch (e) {
      setMessage(text);
      setError(e.message);
    } finally {
      setTyping(false);
    }
  };
  const send = (event) => {
    event.preventDefault();
    sendMessage(message);
  };
  const createOrder = async (data) => {
    const created = await transact(() =>
      request("/orders/", { method: "POST", body: data }),
    );
    const active = await request(`/orders/${created.id}/pix/`, {
      method: "POST",
    });
    await refresh();
    setCheckout(false);
    setPix(active);
    setDrawer(false);
  };
  const renew = async () =>
    setPix(
      await transact(() =>
        request(`/orders/${pix.id}/pix/`, { method: "POST" }),
      ),
    );
  const pay = async () =>
    setPix(
      await transact(() =>
        request(`/orders/${pix.id}/simulate-payment/`, { method: "POST" }),
      ),
    );
  const reopenOrder = async () => {
    const latest = session.orders?.at(-1);
    if (!latest) return;
    try {
      setPix(await request(`/orders/${latest.id}/`));
    } catch (e) {
      setError(e.message);
    }
  };
  const cart = session.cart;
  const count =
    cart?.items?.reduce((sum, item) => sum + item.quantidade, 0) || 0;
  const cardsById = Object.fromEntries(products.map((p) => [p.id, p]));
  const messages = [
    welcome,
    ...session.messages,
    ...(pendingMessage ? [{ role: "user", text: pendingMessage }] : []),
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-symbol">P</span>
          <div>
            <strong>PROHALL</strong>
            <span>CONSULTORIA DE BELEZA</span>
          </div>
        </div>
        <div className="top-actions">
          <button
            className="bag-trigger"
            onClick={() => setDrawer(true)}
            aria-label={`Abrir sacola com ${count} itens`}
          >
            <ShoppingBag size={18} />
            <span>Sacola</span>
            <b>{count}</b>
          </button>
        </div>
      </header>
      {page === "debug" ? (
        <DebugPage calls={debugCalls} error={debugError} onBack={() => { window.location.hash = ""; }} onRefresh={refreshDebug} />
      ) : (
      <div className="app-grid">
        <main className="chat">
          <div className="chat-head">
            <div className="sofia-avatar">S</div>
            <div>
              <strong>Sofia</strong>
              <span>Consultora de beleza · Prohall</span>
            </div>
            <span className="online">
              <span /> Online
            </span>
            <button type="button" className="debug-page-trigger" onClick={() => { window.location.hash = "/debug"; }} aria-label="Abrir painel de debug">
              <Bug size={16} /> <span>Debug</span>
            </button>
          </div>
          <div className="conversation" ref={conversationRef}>
            {messages.map((m, index) => (
              <div key={index}>
                <div className={`message ${m.role}`}>
                  <div className="bubble">{m.role === "assistant" ? <FormattedMessage text={m.text} /> : m.text}</div>
                </div>
                {m.cards?.length > 0 && (
                  <div className="card-row">
                    {m.cards
                      .map((id) => cardsById[id])
                      .filter(Boolean)
                      .map((item) => (
                        <ProductCard
                          key={item.id}
                          item={item}
                          onAdd={addFromCard}
                          busy={busy}
                        />
                      ))}
                  </div>
                )}
                {m.checkout_preview && (
                  <CheckoutPreview
                    preview={m.checkout_preview}
                    onSelect={(label) => sendMessage(`Quero o frete ${label}`)}
                    busy={typing || busy}
                    active={index === messages.length - 1 && session.checkout_preparado}
                  />
                )}
              </div>
            ))}
            {typing && (
              <div className="message assistant">
                <div className="bubble typing-bubble">
                  <LoaderCircle size={15} className="spin" /> Sofia está
                  digitando…
                </div>
              </div>
            )}
            {error && (
              <div className="chat-error" role="alert">
                {error}
              </div>
            )}
          </div>
          <form className="composer" onSubmit={send}>
            <input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Conte para a Sofia sobre seu cabelo…"
              aria-label="Sua mensagem para Sofia"
              maxLength="2000"
            />
            <button
              type="submit"
              disabled={typing || !message.trim()}
              aria-label="Enviar mensagem"
            >
              <Send size={18} />
            </button>
          </form>
        </main>
      </div>
      )}
      {drawer && (
        <div
          className="drawer-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setDrawer(false);
          }}
        >
          <aside className="cart-drawer">
            <div className="sidebar-heading">
              <h2>Minha sacola</h2>
              <button
                className="icon-button"
                onClick={() => setDrawer(false)}
                aria-label="Fechar sacola"
              >
                <X size={20} />
              </button>
            </div>
            {session.orders?.length > 0 && (
              <button className="order-trigger" onClick={() => { setDrawer(false); reopenOrder(); }}>
                Acompanhar pedido
              </button>
            )}
            <Cart
              cart={cart}
              onAdd={add}
              onRemove={remove}
              onCoupon={coupon}
              onShipping={shipping}
              onCheckout={() => {
                setDrawer(false);
                setCheckout(true);
              }}
              busy={busy}
              couponInput={couponInput}
              setCouponInput={setCouponInput}
              cepInput={cepInput}
              setCepInput={setCepInput}
            />
          </aside>
        </div>
      )}
      {checkout && (
        <Checkout
          cart={cart}
          initialCep={cart?.frete?.cep || cepInput}
          onClose={() => setCheckout(false)}
          onShipping={shipping}
          onCreate={createOrder}
          busy={busy}
        />
      )}
      {pix && (
        <Pix
          order={pix}
          onClose={() => setPix(null)}
          onRenew={renew}
          onPay={pay}
          busy={busy}
        />
      )}
    </div>
  );
}
