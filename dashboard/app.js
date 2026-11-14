(() => {
  'use strict';

  // ------------------------------------------------------------------
  // Configuración
  // ------------------------------------------------------------------
  const CFG = Object.assign(
    { apiUrl: 'http://127.0.0.1:8007/graphql', defaultFrom: '2026-10-26', defaultTo: '2026-10-30' },
    window.DASHBOARD_CONFIG || {}
  );
  const STORAGE_KEY = 'ingresos.sesion';

  // ------------------------------------------------------------------
  // Operaciones GraphQL (las mismas que se prueban en GraphiQL)
  // ------------------------------------------------------------------
  const LOGIN_MUTATION = `
    mutation IniciarSesion($input: LoginInput!) {
      login(input: $input) { token tokenType user { id name email } }
    }`;

  const BALANCE_QUERY = `
    query IndicadoresEmpresa($from: Date!, $to: Date!) {
      generalBalance(fromDate: $from, toDate: $to) {
        companyId currency fromDate toDate
        openingBalance totalIncome totalExpense profit closingBalance
        isInRed accountsInRed
        accounts {
          accountId accountName isActive
          openingBalance totalIncome totalExpense profit closingBalance isInRed
        }
      }
    }`;

  // Solo para mostrar el nombre de la empresa. Si falla (por permisos), se ignora.
  const COMPANY_QUERY = `query Empresa($id: ID!) { company(id: $id) { name } }`;

  // ------------------------------------------------------------------
  // Utilidades
  // ------------------------------------------------------------------
  const $ = (id) => document.getElementById(id);

  class ApiError extends Error {
    constructor(code, message) {
      super(message);
      this.code = code;
    }
  }

  async function graphql(query, variables, token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = 'Bearer ' + token;

    let response;
    try {
      response = await fetch(CFG.apiUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({ query, variables })
      });
    } catch (_) {
      throw new ApiError(
        'NETWORK',
        `No se pudo conectar con ${CFG.apiUrl}. Revisa que la API esté encendida y que CORS permita este origen.`
      );
    }

    let payload = null;
    try { payload = await response.json(); } catch (_) { /* respuesta sin JSON */ }

    if (payload && Array.isArray(payload.errors) && payload.errors.length) {
      const first = payload.errors[0];
      const code = (first.extensions && first.extensions.code) || 'GRAPHQL_ERROR';
      throw new ApiError(code, first.message || 'El servidor devolvió un error.');
    }
    if (!response.ok || !payload || !payload.data) {
      throw new ApiError('HTTP', `El servidor respondió con el estado ${response.status}.`);
    }
    return payload.data;
  }

  // Dinero: se formatea el TEXTO que manda el servidor, sin pasar por float.
  function formatMoney(value) {
    const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value).trim());
    if (!match) return String(value);
    const sign = match[1];
    const integer = match[2].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    const decimals = (match[3] || '').padEnd(2, '0');
    return `${sign}${integer}.${decimals}`;
  }

  function isNegative(value) {
    const text = String(value).trim();
    return text.startsWith('-') && /[1-9]/.test(text);
  }

  function isZero(value) {
    return !/[1-9]/.test(String(value));
  }

  const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  function formatDate(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : iso;
  }

  function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([key, val]) => {
      if (key === 'text') node.textContent = val;
      else if (key === 'class') node.className = val;
      else node.setAttribute(key, val);
    });
    [].concat(children).forEach((child) => node.append(child));
    return node;
  }

  // ------------------------------------------------------------------
  // Sesión (el token vive solo en sessionStorage y en memoria)
  // ------------------------------------------------------------------
  let session = null;
  let companyName = null;
  let requestId = 0;

  function loadSession() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      return parsed && parsed.token ? parsed : null;
    } catch (_) {
      return null;
    }
  }

  function saveSession(value) {
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value)); } catch (_) { /* solo memoria */ }
  }

  function clearSession() {
    session = null;
    companyName = null;
    try { sessionStorage.removeItem(STORAGE_KEY); } catch (_) { /* nada */ }
  }

  // ------------------------------------------------------------------
  // Vistas
  // ------------------------------------------------------------------
  function showLogin(message, kind) {
    $('dashboard-view').hidden = true;
    $('login-view').hidden = false;
    showLoginMessage(message || '', kind);
    $('email').focus();
  }

  function showLoginMessage(text, kind) {
    const box = $('login-message');
    box.hidden = !text;
    box.textContent = text || '';
    box.classList.toggle('message--notice', kind === 'notice');
  }

  function logout(message) {
    requestId += 1; // descarta cualquier respuesta pendiente
    clearSession();
    resetDashboard();
    showLogin(message, message ? 'notice' : undefined);
  }

  function resetDashboard() {
    $('content').hidden = true;
    $('content').classList.remove('is-loading');
    $('state-panel').hidden = true;
    $('accounts-body').replaceChildren();
    $('header-meta').replaceChildren(el('span', { text: 'Empresa' }));
  }

  function enterDashboard() {
    $('login-view').hidden = true;
    $('dashboard-view').hidden = false;
    $('user-label').textContent = (session.user && session.user.name) || '';
    if (!$('from-date').value) $('from-date').value = CFG.defaultFrom;
    if (!$('to-date').value) $('to-date').value = CFG.defaultTo;
    loadBalance();
  }

  // ------------------------------------------------------------------
  // Login
  // ------------------------------------------------------------------
  function loginErrorText(err) {
    if (err.code === 'NETWORK' || err.code === 'HTTP') return err.message;
    if (['UNAUTHENTICATED', 'FORBIDDEN', 'NOT_FOUND'].includes(err.code)) {
      return 'Correo o contraseña incorrectos, o el usuario está inactivo.';
    }
    return err.message;
  }

  async function onLogin(event) {
    event.preventDefault();
    const email = $('email').value.trim();
    const password = $('password').value;
    if (!email || !password) {
      showLoginMessage('Escribe tu correo y tu contraseña.');
      return;
    }
    showLoginMessage('');
    $('login-btn').disabled = true;
    $('login-btn').textContent = 'Entrando…';
    try {
      const data = await graphql(LOGIN_MUTATION, { input: { email, password } });
      session = { token: data.login.token, user: data.login.user };
      saveSession(session);
      $('password').value = '';
      enterDashboard();
    } catch (err) {
      showLoginMessage(loginErrorText(err));
    } finally {
      $('login-btn').disabled = false;
      $('login-btn').textContent = 'Entrar';
    }
  }

  // ------------------------------------------------------------------
  // Consulta del balance general
  // ------------------------------------------------------------------
  function setPeriodError(text) {
    const box = $('period-error');
    box.hidden = !text;
    box.textContent = text || '';
  }

  function showState(kind, title, text, canRetry) {
    const panel = $('state-panel');
    panel.hidden = false;
    panel.classList.toggle('state--error', kind === 'error' || kind === 'denied');
    $('state-title').textContent = title;
    $('state-text').textContent = text;
    $('state-retry').hidden = !canRetry;
  }

  function setLoading(isLoading) {
    $('refresh-btn').disabled = isLoading;
    $('refresh-btn').textContent = isLoading ? 'Consultando…' : 'Actualizar';
    if (isLoading) {
      if ($('content').hidden) showState('loading', 'Consultando balance…', 'Un momento, estamos pidiendo los datos al servidor.', false);
      else $('content').classList.add('is-loading');
    } else {
      $('content').classList.remove('is-loading');
    }
  }

  async function loadBalance() {
    if (!session) { showLogin(); return; }

    const from = $('from-date').value;
    const to = $('to-date').value;
    if (!from || !to) { setPeriodError('Elige las dos fechas para consultar.'); return; }
    if (from > to) {
      setPeriodError('La fecha inicial no puede ser posterior a la final. No se consultó el servidor.');
      return;
    }
    setPeriodError('');

    const current = ++requestId;
    setLoading(true);
    try {
      const data = await graphql(BALANCE_QUERY, { from, to }, session.token);
      if (current !== requestId) return; // llegó una respuesta vieja
      $('state-panel').hidden = true;
      render(data.generalBalance);
      fetchCompanyName(data.generalBalance);
    } catch (err) {
      if (current !== requestId) return;
      handleBalanceError(err);
    } finally {
      if (current === requestId) setLoading(false);
    }
  }

  function handleBalanceError(err) {
    $('content').hidden = true; // nunca dejar números viejos junto a un error
    if (err.code === 'UNAUTHENTICATED') {
      logout('Tu sesión expiró o el token no es válido. Inicia sesión de nuevo.');
      return;
    }
    if (err.code === 'FORBIDDEN') {
      showState('denied', 'Acceso denegado',
        'Tu rol no puede ver el balance de la empresa. Hace falta permiso de lectura de cuentas y de movimientos. Pídele a un administrador que lo active.',
        false);
      return;
    }
    if (err.code === 'NETWORK') {
      showState('error', 'Sin conexión con el API', err.message, true);
      return;
    }
    showState('error', 'No se pudo cargar el balance', err.message, true);
  }

  async function fetchCompanyName(balance) {
    const forToken = session && session.token;
    if (companyName !== null || !forToken) return;
    try {
      const data = await graphql(COMPANY_QUERY, { id: balance.companyId }, forToken);
      if (data.company && data.company.name && session && session.token === forToken) {
        companyName = data.company.name;
        renderHeader(balance);
      }
    } catch (_) { /* el nombre es opcional: se queda "Empresa N" */ }
  }

  // ------------------------------------------------------------------
  // Pintar resultados
  // ------------------------------------------------------------------
  function renderHeader(b) {
    $('header-meta').replaceChildren(
      el('span', { text: companyName || `Empresa ${b.companyId}` }),
      el('span', { text: b.currency }),
      el('span', { text: `Del ${formatDate(b.fromDate)} al ${formatDate(b.toDate)}` })
    );
  }

  function render(b) {
    renderHeader(b);
    $('period-label').textContent = `Resultados del ${formatDate(b.fromDate)} al ${formatDate(b.toDate)}, en ${b.currency}.`;
    $('currency-label').textContent = b.currency;

    // Indicadores generales: valores tal cual los calculó el servidor.
    $('kpi-opening').textContent = formatMoney(b.openingBalance);
    $('kpi-income').textContent = formatMoney(b.totalIncome);
    $('kpi-expense').textContent = formatMoney(b.totalExpense);
    $('kpi-profit').textContent = formatMoney(b.profit);
    $('kpi-closing').textContent = formatMoney(b.closingBalance);

    $('kpi-profit-card').classList.toggle('kpi--loss', isNegative(b.profit));
    $('kpi-closing-card').classList.toggle('kpi--red', b.isInRed);
    $('kpi-closing-hint').textContent = b.isInRed ? 'Saldo en rojo' : 'Saldo inicial + profit';

    // Estado de riesgo
    const general = $('risk-general');
    general.textContent = b.isInRed ? 'Sí' : 'No';
    general.className = 'badge ' + (b.isInRed ? 'badge--red' : 'badge--ok');

    const count = $('risk-count');
    count.textContent = String(b.accountsInRed);
    count.className = 'badge ' + (b.accountsInRed > 0 ? 'badge--red' : 'badge--ok');
    $('risk-names').textContent = b.accounts.filter((a) => a.isInRed).map((a) => a.accountName).join(', ');

    renderAccounts(b.accounts);
    $('content').hidden = false;
  }

  function moneyCell(value, extraClass) {
    return el('td', { class: ('num ' + (extraClass || '')).trim(), text: formatMoney(value) });
  }

  function renderAccounts(accounts) {
    const body = $('accounts-body');
    const note = $('detail-note');
    body.replaceChildren();

    if (accounts.length === 0) {
      note.hidden = false;
      note.textContent = 'Esta empresa todavía no tiene cuentas registradas.';
      return;
    }

    const allEmpty = accounts.every((a) => isZero(a.openingBalance) && isZero(a.totalIncome) && isZero(a.totalExpense));
    note.hidden = !allEmpty;
    note.textContent = allEmpty ? 'No hay movimientos ni saldo en este período. Prueba con otras fechas.' : '';

    accounts.forEach((a) => {
      const name = el('td', {}, [document.createTextNode(a.accountName)]);
      if (!a.isActive) name.append(el('span', { class: 'tag', text: 'Inactiva' }));

      const closing = el('td', { class: 'num' });
      if (a.isInRed) {
        closing.append(el('span', { class: 'pill pill--red', text: formatMoney(a.closingBalance) }));
        closing.append(el('span', { class: 'sr-only', text: ' (en rojo)' }));
      } else {
        closing.textContent = formatMoney(a.closingBalance);
      }

      const row = el('tr', { class: a.isInRed ? 'is-red' : '' }, [
        name,
        moneyCell(a.openingBalance),
        moneyCell(a.totalIncome),
        moneyCell(a.totalExpense),
        moneyCell(a.profit, isNegative(a.profit) ? 'loss' : ''),
        closing
      ]);
      body.append(row);
    });
  }

  // ------------------------------------------------------------------
  // Arranque
  // ------------------------------------------------------------------
  function init() {
    $('server-label').textContent = CFG.apiUrl;

    $('login-form').addEventListener('submit', onLogin);
    $('toggle-password').addEventListener('click', () => {
      const input = $('password');
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      $('toggle-password').textContent = show ? 'Ocultar' : 'Mostrar';
      $('toggle-password').setAttribute('aria-pressed', String(show));
    });

    $('period-form').addEventListener('submit', (e) => { e.preventDefault(); loadBalance(); });
    $('from-date').addEventListener('change', loadBalance);
    $('to-date').addEventListener('change', loadBalance);
    $('state-retry').addEventListener('click', loadBalance);
    $('logout-btn').addEventListener('click', () => logout());

    session = loadSession();
    if (session) enterDashboard();
    else showLogin();
  }

  init();
})();