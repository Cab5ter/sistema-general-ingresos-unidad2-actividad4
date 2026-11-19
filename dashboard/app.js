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
    viewer = null;
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
    loadViewer();
    switchSection('finance');
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
      // La empresa se obtiene de viewer, autenticado, no del endpoint bootstrap.
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
  // Unidad III: administración. Los datos y permisos vienen del API.
  // ------------------------------------------------------------------
  const VIEWER_QUERY = `query { viewer { memberId companyId companyName roleCode permissions } }`;
  const USERS_QUERY = `query($id: ID!) { companyUsers(companyId: $id) { id isAdmin isActive role user { name email } } }`;
  const ADMIN_ACCOUNTS_QUERY = `query($id: ID!) { accounts(companyId: $id) { id name accountType bankName clabe cardLastDigits isActive } }`;
  const ADMIN_CONCEPTS_QUERY = `query($id: ID!) { concepts(companyId: $id) { id name conceptType isActive } }`;
  const ASSIGNED_QUERY = `query($id: ID!) { accountConcepts(accountId: $id) { id isActive concept { id name conceptType } } }`;
  const ADD_USER_MUTATION = `mutation($i: CreateCompanyUserInput!) { createCompanyUser(input: $i) { id } }`;
  const DEACTIVATE_USER_MUTATION = `mutation($id: ID!) { deactivateCompanyUser(id: $id) { id isActive } }`;
  const ADD_ACCOUNT_MUTATION = `mutation($i: CreateAccountInput!) { createAccount(input: $i) { id } }`;
  const ADD_CONCEPT_MUTATION = `mutation($i: CreateConceptInput!) { createConcept(input: $i) { id } }`;
  const ASSIGN_CONCEPT_MUTATION = `mutation($i: AssignConceptToAccountInput!) { assignConceptToAccount(input: $i) { id } }`;
  const REMOVE_CONCEPT_MUTATION = `mutation($a: ID!, $c: ID!) { removeConceptFromAccount(accountId: $a, conceptId: $c) }`;
  const ACCOUNT_TYPES = {CASH:'Efectivo',DEBIT:'Débito',CREDIT:'Crédito',SAVINGS:'Ahorro',INVESTMENT:'Inversión',WALLET:'Monedero',OTHER:'Otro'};
  const CONCEPT_TYPES = {INCOME:'Ingreso',EXPENSE:'Egreso'};

  let viewer = null;
  let section = 'finance';
  let adminTab = 'users';
  let adminRequest = 0;
  let adminUsers = [];
  let adminAccounts = [];
  let adminConcepts = [];
  let assignedConcepts = [];

  function permitted(permission) {
    return !!viewer && viewer.permissions.includes(permission);
  }

  function adminMessage(message) {
    $('admin-message').textContent = message || '';
    $('admin-message').hidden = !message;
  }

  function adminError(err) {
    if (err.code === 'UNAUTHENTICATED') {
      logout('Sesión no válida o expirada. Inicia sesión nuevamente.');
    } else {
      adminMessage(err.message || 'No se pudo completar la operación.');
    }
  }

  async function loadViewer() {
    if (!session) return;
    const token = session.token;
    try {
      const data = await graphql(VIEWER_QUERY, {}, token);
      if (!session || session.token !== token) return;
      viewer = data.viewer;
      companyName = viewer.companyName;
      $('header-meta').replaceChildren(el('span', {text: companyName}));
      $('new-user-btn').hidden = !permitted('company.users.write');
      $('new-account-btn').hidden = !permitted('accounts.write');
      $('new-concept-btn').hidden = !permitted('concepts.write');
      $('concept-assign-controls').hidden = !permitted('concepts.write');
      if (section === 'admin') await loadAdminTab();
    } catch (err) {
      if (!session || session.token !== token) return;
      adminError(err);
    }
  }

  function switchSection(target) {
    if (!session) return showLogin();
    section = target;
    $('financial-view').hidden = target !== 'finance';
    $('administration-view').hidden = target !== 'admin';
    $('dashboard-title').textContent = target === 'finance' ? 'Dashboard financiero' : 'Dashboard administrativo';
    $('nav-finance').classList.toggle('is-current', target === 'finance');
    $('nav-admin').classList.toggle('is-current', target === 'admin');
    for (const id of ['nav-finance', 'nav-admin']) {
      if ((id === 'nav-finance') === (target === 'finance')) $(id).setAttribute('aria-current','page');
      else $(id).removeAttribute('aria-current');
    }
    if (target === 'finance') loadBalance();
    else {
      ++requestId;
      if (viewer) loadAdminTab();
      else loadViewer();
    }
  }

  function switchAdminTab(tab) {
    adminTab = tab;
    for (const name of ['users','accounts','concepts']) {
      $('module-' + name).hidden = name !== tab;
      document.querySelector(`[data-admin-tab="${name}"]`).classList.toggle('is-selected', name === tab);
    }
    adminMessage('');
    if (section === 'admin' && viewer) loadAdminTab();
  }

  async function adminQuery(query, variables = {}) {
    if (!session) throw new ApiError('UNAUTHENTICATED', 'Debes iniciar sesión.');
    return graphql(query, variables, session.token);
  }

  async function loadAdminTab() {
    if (!viewer || !session || section !== 'admin') return;
    const current = ++adminRequest;
    adminMessage('');
    try {
      if (adminTab === 'users') {
        if (!permitted('company.users.read')) return adminMessage('Tu rol no tiene permiso para ver usuarios.');
        const data = await adminQuery(USERS_QUERY, {id: viewer.companyId});
        if (current !== adminRequest || section !== 'admin' || adminTab !== 'users') return;
        adminUsers = data.companyUsers;
        renderAdminUsers();
      } else if (adminTab === 'accounts') {
        if (!permitted('accounts.read')) return adminMessage('Tu rol no tiene permiso para ver cuentas.');
        const data = await adminQuery(ADMIN_ACCOUNTS_QUERY, {id: viewer.companyId});
        if (current !== adminRequest || section !== 'admin' || adminTab !== 'accounts') return;
        adminAccounts = data.accounts;
        renderAdminAccounts();
      } else {
        if (!permitted('concepts.read')) return adminMessage('Tu rol no tiene permiso para ver conceptos.');
        const data = await adminQuery(ADMIN_CONCEPTS_QUERY, {id: viewer.companyId});
        if (current !== adminRequest || section !== 'admin' || adminTab !== 'concepts') return;
        adminConcepts = data.concepts;
        renderAdminConcepts();
        if (permitted('accounts.read')) {
          const accounts = await adminQuery(ADMIN_ACCOUNTS_QUERY, {id: viewer.companyId});
          if (current !== adminRequest || section !== 'admin' || adminTab !== 'concepts') return;
          adminAccounts = accounts.accounts;
          renderAccountSelector();
        } else {
          $('concept-account').replaceChildren(el('option', {value:'',text:'Sin permiso de lectura de cuentas'}));
        }
      }
    } catch (err) {
      if (current === adminRequest) adminError(err);
    }
  }

  function emptyRow(bodyId, columns, message) {
    $(bodyId).replaceChildren(el('tr', {}, [el('td', {colspan: String(columns), text:message})]));
  }

  function renderAdminUsers() {
    $('users-active').textContent = String(adminUsers.filter(x => x.isActive).length);
    $('users-admin').textContent = String(adminUsers.filter(x => x.isAdmin).length);
    $('users-inactive').textContent = String(adminUsers.filter(x => !x.isActive).length);
    const needle = $('user-search').value.trim().toLocaleLowerCase();
    const filter = $('user-filter').value;
    const list = adminUsers.filter(x => {
      const searchable = `${x.user.name} ${x.user.email}`.toLocaleLowerCase();
      return searchable.includes(needle) && (filter === 'all' || x.isActive === (filter === 'active'));
    });
    if (!list.length) return emptyRow('users-body', 6, 'No hay usuarios con esos filtros.');
    $('users-body').replaceChildren(...list.map(u => {
      const action = el('td');
      if (u.isActive && !u.isAdmin && permitted('company.users.write')) {
        const btn = el('button', {type:'button',class:'admin-small-action',text:'Desactivar'});
        btn.addEventListener('click', async () => {
          if (!confirm(`¿Desactivar a ${u.user.name}? Dejará de operar, pero su historial se conservará.`)) return;
          btn.disabled = true;
          try {
            await adminQuery(DEACTIVATE_USER_MUTATION, {id: u.id});
            await loadAdminTab();
          } catch (err) {adminError(err);btn.disabled=false;}
        });
        action.append(btn);
      }
      return el('tr', {}, [
        el('td',{text:u.user.name}), el('td',{text:u.user.email}),
        el('td',{text:u.role || 'Sin rol'}), el('td',{text:u.isAdmin?'Sí':'No'}),
        el('td',{},[statusElement(u.isActive)]), action
      ]);
    }));
  }

  function statusElement(active) {
    return el('span', {class:'admin-status ' + (active?'admin-status--active':'admin-status--inactive'), text:active?'Activo':'Inactivo'});
  }

  function renderAdminAccounts() {
    const kind = $('account-filter').value;
    const activeOnly = $('account-active-only').checked;
    const list = adminAccounts.filter(a => (kind === 'all' || a.accountType === kind) && (!activeOnly || a.isActive));
    if (!list.length) return emptyRow('catalog-accounts-body',5,'No hay cuentas con esos filtros.');
    $('catalog-accounts-body').replaceChildren(...list.map(a => {
      const last4 = a.cardLastDigits || (a.clabe ? a.clabe.slice(-4) : '');
      return el('tr', {}, [el('td',{text:a.name}),el('td',{text:ACCOUNT_TYPES[a.accountType] || a.accountType}),
        el('td',{text:a.bankName || '—'}),el('td',{text:last4 ? '•••• ' + last4 : '—'}),
        el('td',{},[statusElement(a.isActive)])]);
    }));
  }

  function renderAdminConcepts() {
    const kind = $('concept-filter').value;
    const activeOnly = $('concept-active-only').checked;
    const list = adminConcepts.filter(c => (kind === 'all' || kind === c.conceptType) && (!activeOnly || c.isActive));
    if (!list.length) return emptyRow('concepts-body',3,'No hay conceptos con esos filtros.');
    $('concepts-body').replaceChildren(...list.map(c => el('tr', {}, [
      el('td',{text:c.name}),el('td',{text:CONCEPT_TYPES[c.conceptType] || c.conceptType}),
      el('td',{},[statusElement(c.isActive)])])));
    renderConceptToAssign();
  }

  function renderAccountSelector() {
    const selector = $('concept-account');
    const old = selector.value;
    selector.replaceChildren(el('option',{value:'',text:'Selecciona una cuenta'}),
      ...adminAccounts.filter(a=>a.isActive).map(a => el('option',{value:a.id,text:a.name})));
    if (adminAccounts.some(a => a.isActive && a.id === old)) selector.value = old;
    if (selector.value) loadAssignedConcepts();
    else {
      assignedConcepts = [];
      $('assigned-concepts').replaceChildren(el('li',{text:'Selecciona una cuenta para ver sus conceptos.'}));
      renderConceptToAssign();
    }
  }

  async function loadAssignedConcepts() {
    const account = $('concept-account').value;
    if (!account) {
      assignedConcepts = [];
      $('assigned-concepts').replaceChildren(el('li',{text:'Selecciona una cuenta para ver sus conceptos.'}));
      renderConceptToAssign();
      return;
    }
    const token = session && session.token;
    try {
      const data = await adminQuery(ASSIGNED_QUERY, {id:account});
      if (!session || session.token !== token || account !== $('concept-account').value) return;
      assignedConcepts = data.accountConcepts;
      renderAssignedConcepts();
    } catch (err) {adminError(err);}
  }

  function renderAssignedConcepts() {
    if (!assignedConcepts.length) {
      $('assigned-concepts').replaceChildren(el('li',{text:'Esta cuenta no tiene conceptos asignados.'}));
    } else {
      $('assigned-concepts').replaceChildren(...assignedConcepts.map(link => {
        const listItem = el('li',{},[el('span',{text:`${link.concept.name} · ${CONCEPT_TYPES[link.concept.conceptType]}`})]);
        if (permitted('concepts.write')) {
          const remove = el('button',{type:'button',class:'admin-small-action',text:'Quitar'});
          remove.addEventListener('click', async () => {
            try {
              await adminQuery(REMOVE_CONCEPT_MUTATION,{a:$('concept-account').value,c:link.concept.id});
              await loadAssignedConcepts();
            } catch (err) {adminError(err);}
          });
          listItem.append(remove);
        }
        return listItem;
      }));
    }
    renderConceptToAssign();
  }

  function renderConceptToAssign() {
    // Mantener incluso los ya asignados: el API debe demostrar el error de duplicado.
    const taken = new Set(assignedConcepts.map(x => x.concept.id));
    const options = adminConcepts.filter(c=>c.isActive);
    const select = $('concept-to-assign');
    select.replaceChildren(...options.map(c => el('option',{value:c.id,text:`${c.name} (${CONCEPT_TYPES[c.conceptType]})${taken.has(c.id) ? ' · asignado' : ''}`})));
    $('assign-concept-btn').disabled = !options.length || !$('concept-account').value;
    $('concept-assign-controls').hidden = !permitted('concepts.write') || !permitted('accounts.read');
  }

  function formObject(id) {
    const obj = Object.fromEntries(new FormData($(id)).entries());
    for (const [key,value] of Object.entries(obj)) if (typeof value === 'string') obj[key] = value.trim();
    return Object.fromEntries(Object.entries(obj).filter(([,value])=>value !== ''));
  }

  async function submitAdminForm(event, kind) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    adminMessage('');
    try {
      const data = formObject(form.id);
      if (kind === 'users') {
        if (!permitted('company.users.write')) throw new ApiError('FORBIDDEN','No tienes permiso para registrar usuarios.');
        await adminQuery(ADD_USER_MUTATION, {i:{...data, companyId:viewer.companyId}});
      } else if (kind === 'accounts') {
        if (!permitted('accounts.write')) throw new ApiError('FORBIDDEN','No tienes permiso para registrar cuentas.');
        await adminQuery(ADD_ACCOUNT_MUTATION,{i:{...data, companyId:viewer.companyId}});
      } else {
        if (!permitted('concepts.write')) throw new ApiError('FORBIDDEN','No tienes permiso para registrar conceptos.');
        await adminQuery(ADD_CONCEPT_MUTATION,{i:{...data, companyId:viewer.companyId}});
      }
      form.reset();
      form.hidden = true;
      await loadAdminTab();
    } catch (err) {adminError(err);} finally {button.disabled=false;}
  }

  async function assignConcept() {
    const accountId = $('concept-account').value;
    const conceptId = $('concept-to-assign').value;
    if (!accountId || !conceptId || !permitted('concepts.write')) return;
    $('assign-concept-btn').disabled = true;
    adminMessage('');
    try {
      await adminQuery(ASSIGN_CONCEPT_MUTATION,{i:{accountId,conceptId}});
      await loadAssignedConcepts();
    } catch (err) {adminError(err);} finally {renderConceptToAssign();}
  }

  function initAdministration() {
    $('nav-finance').addEventListener('click', () => switchSection('finance'));
    $('nav-admin').addEventListener('click', () => switchSection('admin'));
    document.querySelectorAll('[data-admin-tab]').forEach(node => node.addEventListener('click', () => switchAdminTab(node.dataset.adminTab)));
    document.querySelectorAll('[data-cancel-form]').forEach(node => node.addEventListener('click', () => { $(node.dataset.cancelForm).hidden=true; adminMessage(''); }));
    for (const [button,form] of [['new-user-btn','user-form'],['new-account-btn','account-form'],['new-concept-btn','concept-form']]) {
      $(button).addEventListener('click',()=> {$(form).hidden=false;$(form).querySelector('input').focus();});
    }
    $('user-search').addEventListener('input', renderAdminUsers);
    $('user-filter').addEventListener('change',renderAdminUsers);
    $('account-filter').addEventListener('change',renderAdminAccounts);
    $('account-active-only').addEventListener('change',renderAdminAccounts);
    $('concept-filter').addEventListener('change',renderAdminConcepts);
    $('concept-active-only').addEventListener('change',renderAdminConcepts);
    $('concept-account').addEventListener('change',loadAssignedConcepts);
    $('user-form').addEventListener('submit',e=>submitAdminForm(e,'users'));
    $('account-form').addEventListener('submit',e=>submitAdminForm(e,'accounts'));
    $('concept-form').addEventListener('submit',e=>submitAdminForm(e,'concepts'));
    $('assign-concept-btn').addEventListener('click',assignConcept);
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
    initAdministration();

    session = loadSession();
    if (session) enterDashboard();
    else showLogin();
  }

  init();
})();