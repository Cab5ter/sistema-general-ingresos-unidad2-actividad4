// Prueba del cliente real contra una API de práctica; guarda capturas sin tokens.
// Ejecutar solamente con el laboratorio aislado U3-A3, cuya matriz se restaura al final.
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const api = process.env.API_URL || 'http://127.0.0.1:8007/graphql';
const dashboard = process.env.DASHBOARD_URL || 'http://127.0.0.1:5500';
const output = path.join(root,'docs/unidad3-actividad3/evidencias');
const initial = {
  ADMINISTRADOR: ['company.users.read','company.users.write','accounts.read','accounts.write','concepts.read','concepts.write','transactions.read','transactions.write','roles.read','roles.write'],
  CONTADOR: ['company.users.read','accounts.read','accounts.write','concepts.read','concepts.write','transactions.read','transactions.write','roles.read'],
  CAPTURISTA: ['accounts.read','concepts.read','transactions.read','transactions.write'],
  CONSULTA: ['company.users.read','accounts.read','concepts.read','transactions.read']
};
const checks=[];
const query = `query ListaDelRol($roleId: ID!) {\n  rolePermissions(roleId: $roleId) {\n    isActive\n    permission { id code }\n  }\n}`;
const set = 'mutation($input:SetRolePermissionsInput!){setRolePermissions(input:$input){changed finalCount}}';
const assign = 'mutation($input:AssignRoleInput!){assignRole(input:$input){role{code}}}';

(async()=>{
  const credentials=JSON.parse(await fs.readFile(path.join(root,'.activity3-credentials.json'),'utf8'));
  const ids=JSON.parse(await fs.readFile(path.join(root,'docs/unidad3-actividad3/ids.json'),'utf8'));
  await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM ? {executablePath:process.env.CHROMIUM}: {})});
  const contexts=[];
  let adminToken, catalog, capturedAccount;
  const gql=async(token,document,variables={})=>{
    const response=await fetch(api,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({query:document,variables})});
    return response.json();
  };
  const token=page=>page.evaluate(()=>JSON.parse(sessionStorage.getItem('ingresos.sesion')).token);
  async function shot(page,name){await page.screenshot({path:path.join(output,name+'.png'),fullPage:true,timeout:15000});console.log(name);}
  async function open(label){
    const context=await browser.newContext({viewport:{width:1440,height:1080},colorScheme:'light'});contexts.push(context);
    const page=await context.newPage(); page.setDefaultTimeout(15000);
    page.on('pageerror',err=>{throw err;});
    page.on('request',request=>{ if(request.url()===api && request.postData()) assert(!request.postData().includes('actorCompanyUserId')); });
    console.log('Login '+label);
    await page.goto(dashboard,{waitUntil:'domcontentloaded'});
    await page.locator('#email').fill(label+'.actividad3@example.com');
    await page.locator('#password').fill(credentials[label]);
    await page.locator('#login-btn').click();
    await page.locator('#content').waitFor({state:'visible'});
    return page;
  }
  async function tab(page,name){
    await page.locator('#nav-admin').click();
    await page.locator(`[data-admin-tab="${name}"]`).click();
    if(name==='roles') await page.locator('.permissions-matrix').waitFor();
    else if(name==='users') await page.locator('#users-body tr').first().waitFor();
    else if(name==='accounts') await page.locator('#catalog-accounts-body tr').first().waitFor();
  }
  async function verifyMatrix(page, expected){
    for(const [role,codes] of Object.entries(expected)) {
      for(const code of initial.ADMINISTRADOR){
        const check=page.locator(`[data-permission="${code}"] input[data-role="${role}"]`);
        assert.equal(await check.isChecked(), codes.includes(code),`${role} / ${code}`);
      }
    }
  }
  try {
    const admin=await open('admin'); adminToken=await token(admin);
    catalog=(await gql(adminToken,'{permissions(activeOnly:true){id code}}')).data.permissions;
    // Evita restaurar una matriz ajena editada fuera de este laboratorio.
    for(const [code,expected] of Object.entries(initial)){
      const rows=(await gql(adminToken,query,{roleId:ids.roles[code]})).data.rolePermissions;
      assert.deepEqual(rows.map(r=>r.permission.code).sort(),[...expected].sort(),'El laboratorio debe iniciar con la matriz inicial');
    }
    await tab(admin,'roles'); await verifyMatrix(admin,initial);
    assert.equal(await admin.locator('input[data-role="ADMINISTRADOR"]:enabled').count(),0);
    await shot(admin,'01-matriz-inicial'); checks.push('Matriz inicial: 40 celdas cotejadas con relaciones activas del API.');

    const capt=await open('capturista');
    const capt2=await open('capturista2');
    const contador=await open('contador');
    const pedro=await open('consulta');
    const pedroToken=await token(pedro);
    await tab(capt,'accounts');
    assert.equal(await capt.locator('#roles-tab').isVisible(),false);
    assert.equal(await capt.locator('[data-admin-tab="users"]').isVisible(),false);
    assert.equal(await capt.locator('#new-account-btn').isVisible(),false);
    await shot(capt,'03-capturista-antes');
    const denied=await gql(await token(capt),'{roles{id}}');
    assert.equal(denied.errors[0].extensions.code,'FORBIDDEN');
    checks.push('Capturista sin Usuarios, sin matriz y sin Nueva cuenta; query roles rechazada por el API.');

    // GraphiQL oficial servido por la misma API. El token se agrega solo a POST del API.
    const graphiql=await contexts[0].newPage();
    await graphiql.route(api,route=>route.continue({headers:{...route.request().headers(),authorization:'Bearer '+adminToken}}));
    await graphiql.addInitScript(({query,roleId})=>{
      localStorage.setItem('graphiql:query',query);
      localStorage.setItem('graphiql:variables',JSON.stringify({roleId},null,2));
    },{query,roleId:ids.roles.CAPTURISTA});
    await graphiql.goto(api,{waitUntil:'domcontentloaded'});
    const execute=graphiql.getByRole('button',{name:/Execute query/i});
    await execute.waitFor({timeout:60000});
    const response=graphiql.waitForResponse(r=>r.url()===api && r.request().method()==='POST' && (r.request().postData()||'').includes('ListaDelRol'));
    await execute.click();
    const result=await (await response).json();
    assert.equal(result.data.rolePermissions.length,4);
    await graphiql.getByText('transactions.write',{exact:false}).last().waitFor();
    await shot(graphiql,'02-graphiql-capturista'); await graphiql.close();
    await fs.writeFile(path.join(output,'rolePermissions-inicial.json'),JSON.stringify(result,null,2)+'\n');

    await admin.locator('[data-permission="accounts.write"] input[data-role="CAPTURISTA"]').check();
    await admin.getByRole('button',{name:'Vista previa Capturista',exact:true}).click();
    await admin.locator('#role-preview').waitFor({state:'visible'});
    assert.deepEqual(await admin.locator('#preview-summary dd').allTextContents(),['accounts.write','Ninguno','4','5']);
    await shot(admin,'04-vista-previa');
    await admin.locator('#save-role-permissions').click();
    await admin.getByText('Columna guardada. changed: true',{exact:false}).waitFor();
    const after=(await gql(adminToken,query,{roleId:ids.roles.CAPTURISTA})).data.rolePermissions;
    assert(after.some(r=>r.permission.code==='accounts.write'&&r.isActive));
    checks.push('Vista previa: activa accounts.write, 0 desactivaciones, 4 sin cambio, total 5; MySQL confirma la relación.');
    await tab(capt,'accounts'); assert(await capt.locator('#new-account-btn').isVisible());
    await shot(capt,'05-capturista-despues');
    await tab(capt2,'accounts'); assert(await capt2.locator('#new-account-btn').isVisible());
    await shot(capt2,'06-segundo-capturista');
    await capt.locator('#new-account-btn').click();
    capturedAccount='Cuenta creada por María '+Date.now();
    await capt.locator('#account-form input[name="name"]').fill(capturedAccount);
    await capt.locator('#account-form button[type="submit"]').click();
    await capt.getByRole('cell',{name:capturedAccount,exact:true}).waitFor();
    checks.push('Dos capturistas ven Nueva cuenta con sus tokens anteriores; María crea una cuenta desde el cliente.');

    await tab(admin,'users');
    const row=admin.locator('#users-body tr').filter({hasText:'Pedro Consulta'});
    await row.getByRole('combobox').selectOption(ids.roles.CAPTURISTA);
    await row.getByRole('button',{name:'Guardar rol'}).click();
    await admin.getByText('Puesto guardado: Pedro Consulta',{exact:false}).waitFor();
    assert.equal(await row.locator('td').nth(3).innerText(),'No');
    await shot(admin,'07-usuarios-cambio-puesto');
    await tab(admin,'roles');
    await verifyMatrix(admin,{...initial,CAPTURISTA:[...initial.CAPTURISTA,'accounts.write']});
    await shot(admin,'08-consulta-sin-cambios');
    await pedro.locator('#nav-finance').click();
    await pedro.locator('#new-transaction-btn').waitFor({state:'visible'});
    assert.equal(await token(pedro),pedroToken);
    await pedro.locator('#new-transaction-btn').click();
    await pedro.locator('#transaction-concept option').first().waitFor({state:'attached'});
    await pedro.locator('#transaction-form input[name="amount"]').fill('25.00');
    await pedro.locator('#transaction-form button[type="submit"]').click();
    await pedro.getByText('Movimiento registrado.',{exact:true}).waitFor();
    await shot(pedro,'09-mismo-token-movimiento');
    checks.push('Pedro cambia Consulta → Capturista, isAdmin sigue No, la matriz Consulta queda igual y su mismo JWT registra un movimiento.');

    await admin.getByRole('button',{name:'Vista previa Capturista',exact:true}).click();
    await admin.locator('#role-preview').waitFor({state:'visible'});
    await admin.locator('#save-role-permissions').click();
    await admin.getByText('Sin cambios. changed: false',{exact:false}).waitFor();
    await shot(admin,'10-segundo-guardado');
    checks.push('Segundo guardado: changed false, total 5, sin duplicar relaciones.');
    await tab(contador,'roles');
    assert.equal(await contador.locator('.permissions-matrix input:enabled').count(),0);
    assert.equal(await contador.getByRole('button',{name:/Vista previa/}).count(),0);
    await shot(contador,'11-contador-solo-lectura');
    checks.push('Contador ve la matriz completa sin casillas editables ni controles de guardado.');

    // Revocar y comprobar ambas sesiones y la conservación de la cuenta creada.
    const restoreIds=catalog.filter(p=>initial.CAPTURISTA.includes(p.code)).map(p=>p.id);
    const restored=await gql(adminToken,set,{input:{roleId:ids.roles.CAPTURISTA,permissionIds:restoreIds}});
    assert(restored.data.setRolePermissions.changed);
    for(const page of [capt,capt2]){
      await tab(page,'accounts');
      assert.equal(await page.locator('#new-account-btn').isVisible(),false);
      await page.getByRole('cell',{name:capturedAccount,exact:true}).waitFor();
    }
    await shot(capt,'12-revocacion-conserva-cuenta');
    checks.push('Revocación: desaparece Nueva cuenta para ambos capturistas; la cuenta creada se conserva.');

    // Simula un rechazo para verificar que la celda conserva el rol confirmado.
    await tab(admin,'users');
    await admin.route(api, async route=>{
      if((route.request().postData()||'').includes('mutation AsignarPuesto')) {
        return route.fulfill({contentType:'application/json',body:JSON.stringify({data:{assignRole:null},errors:[{message:'Rechazo de prueba',extensions:{code:'FORBIDDEN'}}]})});
      }
      return route.continue();
    });
    const rejected=admin.locator('#users-body tr').filter({hasText:'Pedro Consulta'});
    await rejected.getByRole('combobox').selectOption(ids.roles.CONTADOR);
    await rejected.getByRole('button',{name:'Guardar rol'}).click();
    await admin.getByText('Rechazo de prueba',{exact:true}).waitFor();
    assert.equal(await rejected.getByRole('combobox').inputValue(),ids.roles.CAPTURISTA);
    assert((await rejected.locator('td').nth(2).innerText()).includes('CAPTURISTA'));
    await admin.unroute(api);
    checks.push('Prueba adicional con respuesta de rechazo simulada: el selector recupera el puesto anterior.');

    const mobile=await open('admin');
    await mobile.setViewportSize({width:390,height:844});
    await tab(mobile,'roles');
    assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true);
    await shot(mobile,'13-matriz-movil');
    checks.push('Móvil de 390 px: matriz con desplazamiento interno y sin desbordar la página.');
    await fs.writeFile(path.join(output,'navegador.json'),JSON.stringify({backend:'MySQL 8.4.7',checks,estado:'correcto',tokensIncluidos:false},null,2)+'\n');
    console.log(`${checks.length} comprobaciones de navegador correctas.`);
  } catch(err) {
    for(let i=0;i<contexts.length;i++) for(const page of contexts[i].pages()) await page.screenshot({path:path.join(output,`fallo-${i}.png`),timeout:5000}).catch(()=>{});
    throw err;
  } finally {
    if(adminToken && catalog){
      const restored=await gql(adminToken,set,{input:{roleId:ids.roles.CAPTURISTA,permissionIds:catalog.filter(p=>initial.CAPTURISTA.includes(p.code)).map(p=>p.id)}});
      assert(!restored.errors,'No se pudo restaurar Capturista');
      const assigned=await gql(adminToken,assign,{input:{companyUserId:ids.members.consulta,roleId:ids.roles.CONSULTA}});
      assert(!assigned.errors,'No se pudo restaurar Consulta');
    }
    await browser.close();
  }
})().catch(err=>{console.error(err);process.exitCode=1;});
