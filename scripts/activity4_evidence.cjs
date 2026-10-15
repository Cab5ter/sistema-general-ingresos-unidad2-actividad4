/* Evidencia viva: ejecuta cada operación una sola vez en GraphiQL y captura su resultado.
 * Requiere npm install playwright y un servidor MySQL/API ya iniciado.
 * SETTINGS_FILE=.env.docker PYTHON=/ruta/python ACTIVITY4_URL=http://127.0.0.1:8017/graphql node scripts/activity4_evidence.cjs
 */
const fs=require('node:fs/promises');
const path=require('node:path');
const {execFile}=require('node:child_process');
const {promisify}=require('node:util');
const exec=promisify(execFile);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const ROOT=path.resolve(__dirname,'..');
const OUT=path.join(ROOT,'docs/evidencias/unidad2-actividad4');
const ENDPOINT=process.env.ACTIVITY4_URL || 'http://127.0.0.1:8007/graphql';
const PY=process.env.PYTHON || 'python';
const records=[];
const assert=(value,message)=>{if(!value)throw Error(message)};
const MATRIX={ADMINISTRADOR:['company.users.read','company.users.write','accounts.read','accounts.write','concepts.read','concepts.write','transactions.read','transactions.write','roles.read','roles.write'],CONTADOR:['company.users.read','accounts.read','accounts.write','concepts.read','concepts.write','transactions.read','transactions.write','roles.read'],CAPTURISTA:['accounts.read','concepts.read','transactions.read','transactions.write'],CONSULTA:['company.users.read','accounts.read','concepts.read','transactions.read']};
async function main(){
 if(process.env.AFTER_RESTART==='1')records.push(...JSON.parse(await fs.readFile(path.join(OUT,'operaciones.json'),'utf8')));
 const ids=JSON.parse(await fs.readFile(path.join(OUT,'ids.json'),'utf8'));
 const A=ids.actors,R=ids.roles,P=ids.permissions;
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1360,height:1000},deviceScaleFactor:1});
 const stamp=Date.now().toString().slice(-7);
 async function gql(name,title,rule,query,expected){
  await page.setViewportSize({width:1360,height:name==='03-administrador-inicial'?1400:1000});
  const q='# '+title+'\n'+query;
  if(page.url().split('?')[0]!==ENDPOINT)await page.goto(ENDPOINT,{waitUntil:'networkidle',timeout:60000});
  await page.locator('.graphiql-query-editor .CodeMirror').waitFor({timeout:45000});
  await page.evaluate(value=>document.querySelector('.graphiql-query-editor .CodeMirror').CodeMirror.setValue(value),q);
  await page.evaluate(()=>document.querySelectorAll('.CodeMirror').forEach(e=>e.CodeMirror?.setOption('lineWrapping',true)));
  const prettify=page.locator('button[title*="Prettify"],button[aria-label*="Prettify"]').first();
  if(await prettify.count())await prettify.click();
  await page.addStyleTag({content:'.CodeMirror{font-size:16px!important;line-height:21px!important}.graphiql-container{--font-size-body:16px}'});
  const promise=page.waitForResponse(r=>r.url().split('?')[0]===ENDPOINT && r.request().method()==='POST' && r.request().postData()?.includes('"query"'),{timeout:45000});
  const runButton=page.locator('button[title*="Execute"],button[aria-label*="Execute"],button[title*="Run"],button[aria-label*="Run"]').first();
  await runButton.click();
  const response=await promise;
  const result=await response.json();
  if(expected==='FORBIDDEN')assert(result.errors?.[0]?.extensions?.code==='FORBIDDEN',name+': se esperaba FORBIDDEN');
  else if(expected==='CONFLICT')assert(result.errors?.[0]?.extensions?.code==='CONFLICT',name+': se esperaba CONFLICT');
  else assert(!result.errors,name+': '+JSON.stringify(result));
  await page.waitForTimeout(500);
  await page.screenshot({path:path.join(OUT,name+'.png'),fullPage:true});
  const rec={name,title,rule,query:q,result,expected:expected||'ACEPTADO',http:response.status(),captura:name+'.png'};
  records.push(rec);await fs.writeFile(path.join(OUT,'operaciones.json'),JSON.stringify(records,null,2));
  console.log(name+': '+rec.expected);
  return result.data;
 }
 async function sql(name,title,rule,query){
  const {stdout}=await exec(PY,['-m','scripts.activity4_sql',name,query],{cwd:ROOT,env:process.env});
  const result=JSON.parse(stdout);
  await page.goto('file://'+path.join(OUT,name+'.html'));
  await page.screenshot({path:path.join(OUT,name+'.png'),fullPage:true});
  records.push({name,title,rule,query,result,expected:'SELECT REAL',captura:name+'.png'});
  await fs.writeFile(path.join(OUT,'operaciones.json'),JSON.stringify(records,null,2));
  console.log(name+': SELECT REAL');return result;
 }
 const rp=(role)=>`query {\n  rolePermissions(actorCompanyUserId: "${A.Ana}", roleId: "${R[role]}") {\n    permission { code }\n  }\n}`;
 const account=(person,stage)=>`mutation {\n  createAccount(\n    actorCompanyUserId: "${A[person]}"\n    input: {companyId: "${ids.companyId}", accountType: CASH,\n      name: "${person} ${stage} ${stamp}"}\n  ) { id name companyId }\n}`;
 const grant=(person,role,perm)=>`mutation {\n  assignPermissionToRole(\n    actorCompanyUserId: "${A[person]}"\n    input: {roleId: "${R[role]}", permissionId: "${P[perm]}"}\n  ) { id role { code } permission { code } isActive }\n}`;
 const remove=(role,perm)=>`mutation {\n  removePermissionFromRole(\n    actorCompanyUserId: "${A.Ana}"\n    roleId: "${R[role]}"\n    permissionId: "${P[perm]}"\n  )\n}`;
 const transaction=(stage)=>`mutation {\n  createTransaction(\n    actorCompanyUserId: "${A.Pedro}"\n    input: {accountId: "${ids.accountId}", conceptId: "${ids.conceptId}",\n      transactionType: INCOME, amount: "125.50",\n      shortDescription: "Pedro ${stage} ${stamp}"}\n  ) { id amount shortDescription capturedBy }\n}`;
 const sqlMatrix='SELECT r.code AS rol, p.code AS permiso, rp.is_active FROM role_permissions rp JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id ORDER BY r.code,p.code';
 const pairSql=(role,perm)=>`SELECT rp.id,r.code AS rol,p.code AS permiso,rp.is_active FROM role_permissions rp JOIN roles r ON r.id=rp.role_id JOIN permissions p ON p.id=rp.permission_id WHERE r.code='${role}' AND p.code='${perm}'`;
 const catalogSql='SELECT (SELECT COUNT(*) FROM roles) AS roles, (SELECT COUNT(*) FROM permissions) AS permisos, (SELECT COUNT(*) FROM role_permissions WHERE is_active=1) AS relaciones_activas, (SELECT COUNT(*) FROM role_permissions WHERE is_active=0) AS relaciones_inactivas';
 try {
  if(process.env.AFTER_RESTART==='1'){
   const counts=await sql('33-catalogos-tras-reinicio','MySQL después de reiniciar el servidor','El reinicio conserva 4 roles y 10 permisos; no duplica catálogos ni reactiva permisos retirados.',catalogSql);
   assert(JSON.stringify(counts.filas[0])===JSON.stringify([4,10,26,2]),'El reinicio alteró la configuración');
   const final=await sql('34-matriz-tras-reinicio','Matriz final después del reinicio','Después de reiniciar, la matriz activa sigue coincidiendo con la del documento y las dos parejas retiradas siguen inactivas.',sqlMatrix);
   for(const role of Object.keys(MATRIX))assert(JSON.stringify(final.filas.filter(r=>r[0]===role&&r[2]===1).map(r=>r[1]).sort())===JSON.stringify([...MATRIX[role]].sort()),'Matriz incorrecta tras reiniciar: '+role);
   const summary=JSON.parse(await fs.readFile(path.join(OUT,'resumen.json'),'utf8'));
   summary.estado='COMPLETADO_Y_REINICIO_VERIFICADO';summary.reinicio=counts;
   await fs.writeFile(path.join(OUT,'resumen.json'),JSON.stringify(summary,null,2));
   return;
  }
  await gql('01-roles','Configuración inicial: cuatro roles','El catálogo contiene ADMINISTRADOR, CONTADOR, CAPTURISTA y CONSULTA.',`query { roles(actorCompanyUserId: "${A.Ana}") { id code } }`);
  await gql('02-permisos','Configuración inicial: diez permisos','Los permisos son acciones del catálogo; no pertenecen directamente a cada usuario.',`query { permissions(actorCompanyUserId: "${A.Ana}") { code } }`);
  let initial={};
  for(const [i,role] of ['ADMINISTRADOR','CONTADOR','CAPTURISTA','CONSULTA'].entries()){
   const data=await gql(`${String(i+3).padStart(2,'0')}-${role.toLowerCase()}-inicial`,role+' - lista inicial',role==='CAPTURISTA'?'El capturista tiene transactions.write y todavía no tiene accounts.write.':role==='CONSULTA'?'Consulta no tiene ningún permiso de escritura.':role==='CONTADOR'?'El contador tiene accounts.write, pero no roles.write.':'El administrador dispone de los diez permisos.',rp(role));
   initial[role]=data.rolePermissions.map(x=>x.permission.code).sort();
   assert(JSON.stringify(initial[role])===JSON.stringify([...MATRIX[role]].sort()),'Matriz inicial incorrecta: '+role);
  }
  const members=await sql('07-cinco-personas','Cinco personas, una empresa','Ana es administradora; Luis contador; María y José capturistas; Pedro consulta.',`SELECT u.name,cu.id AS membresia,cu.company_id,cu.is_admin,r.code AS rol FROM company_users cu JOIN users u ON u.id=cu.user_id JOIN company_user_roles cr ON cr.company_user_id=cu.id AND cr.is_active=1 JOIN roles r ON r.id=cr.role_id WHERE cu.company_id=${ids.companyId} ORDER BY cu.id`);
  assert(members.filas.length===5,'Se requieren cinco personas');
  await gql('08-maria-rechazada','María / CAPTURISTA: crear cuenta antes del cambio','Sin accounts.write, el servidor rechaza createAccount antes de guardar.',account('María','antes'),'FORBIDDEN');
  await gql('09-jose-rechazado','José / CAPTURISTA: crear cuenta antes del cambio','José también recibe rechazo porque usa la misma lista del rol Capturista.',account('José','antes'),'FORBIDDEN');
  let rejected=await sql('10-cuentas-no-guardadas','Comprobación de las cuentas rechazadas','Un rechazo no hace commit: las dos cuentas solicitadas no existen.',`SELECT COUNT(*) AS cuentas_rechazadas_guardadas FROM accounts WHERE name IN ('María antes ${stamp}','José antes ${stamp}')`);
  assert(rejected.filas[0][0]===0,'Se guardaron cuentas rechazadas');
  const granted=await gql('11-ana-agrega-permiso','Ana / ADMINISTRADOR: agrega accounts.write al capturista','Una modificación en role_permissions habilita la acción para todos los capturistas.',grant('Ana','CAPTURISTA','accounts.write'));
  await gql('12-pareja-duplicada','Ana: no se duplica una pareja activa','assignPermissionToRole rechaza una relación que ya está activa.',grant('Ana','CAPTURISTA','accounts.write'),'CONFLICT');
  await gql('13-maria-aceptada','María / CAPTURISTA: cuenta después del cambio','María crea una cuenta porque su rol ahora incluye accounts.write.',account('María','después'));
  await gql('14-jose-aceptado','José / CAPTURISTA: cuenta después del cambio','José también crea una cuenta sin cambiar su ficha ni su asignación de rol.',account('José','después'));
  await gql('15-ana-quita-permiso','Ana: retira accounts.write del capturista','removePermissionFromRole desactiva la pareja y conserva su historial.',remove('CAPTURISTA','accounts.write'));
  const inactive=await sql('16-pareja-inactiva','MySQL: la pareja permanece inactiva','La misma fila de CAPTURISTA + accounts.write existe con is_active=0; no fue borrada.',pairSql('CAPTURISTA','accounts.write'));
  assert(inactive.filas.length===1 && inactive.filas[0][0]===Number(granted.assignPermissionToRole.id) && inactive.filas[0][3]===0,'La pareja no conserva su historial');
  await gql('17-maria-rechazada-otra-vez','María: rechazo después de retirar el permiso','La revocación del permiso del rol alcanza a María.',account('María','retirado'),'FORBIDDEN');
  await gql('18-jose-rechazado-otra-vez','José: rechazo después de retirar el permiso','La misma revocación alcanza a José sin editar a las personas.',account('José','retirado'),'FORBIDDEN');
  await gql('19-pedro-rechazado','Pedro / CONSULTA: movimiento rechazado','Consulta permite ver movimientos, pero no registrarlos.',transaction('consulta'),'FORBIDDEN');
  const deniedTx=await sql('20-movimiento-no-guardado','MySQL: movimiento rechazado ausente','El rechazo de Pedro no agrega ninguna fila a transactions.',`SELECT COUNT(*) AS movimientos_rechazados_guardados FROM transactions WHERE short_description='Pedro consulta ${stamp}'`);
  assert(deniedTx.filas[0][0]===0,'Se guardó el movimiento rechazado');
  await gql('21-pedro-cambia-rol','Ana: cambia a Pedro de CONSULTA a CAPTURISTA','assignRole cambia el puesto de una sola persona.',`mutation {\n assignRole(actorCompanyUserId: "${A.Ana}",\n   input: {companyUserId: "${A.Pedro}", roleId: "${R.CAPTURISTA}"}) {\n   companyUser { user { name } } role { code } isActive\n }\n}`);
  const roleHistory=await sql('22-pedro-un-rol-activo','MySQL: historial y un solo rol activo de Pedro','CONSULTA queda inactivo y CAPTURISTA queda activo; Pedro conserva exactamente un rol activo.',`SELECT u.name,r.code AS rol,cr.is_active FROM company_user_roles cr JOIN company_users cu ON cu.id=cr.company_user_id JOIN users u ON u.id=cu.user_id JOIN roles r ON r.id=cr.role_id WHERE cr.company_user_id=${A.Pedro} ORDER BY cr.id`);
  assert(roleHistory.filas.filter(r=>r[2]===1).length===1,'Pedro no tiene un solo rol activo');
  await gql('23-pedro-aceptado','Pedro / CAPTURISTA: movimiento aceptado','Con transactions.write en su nuevo rol, Pedro guarda el ingreso de 125.50.',transaction('capturista'));
  const contador=await gql('24-contador-sin-cambios','CONTADOR: lista después del cambio de Pedro','La lista del contador es idéntica a la inicial; cambiar a Pedro no modifica a Luis.',rp('CONTADOR'));
  assert(JSON.stringify(contador.rolePermissions.map(x=>x.permission.code).sort())===JSON.stringify(initial.CONTADOR),'Cambió la lista del contador');
  await gql('25-luis-crea-cuenta','Luis / CONTADOR: todavía puede crear cuentas','Luis conserva accounts.write después de cambiar el rol de Pedro.',account('Luis','contador'));
  const consulta=await gql('26-consulta-sin-cambios','CONSULTA: lista después del cambio de Pedro','La lista de Consulta conserva los mismos permisos y ninguno termina en .write.',rp('CONSULTA'));
  assert(JSON.stringify(consulta.rolePermissions.map(x=>x.permission.code).sort())===JSON.stringify(initial.CONSULTA),'Cambió la lista de Consulta');
  await gql('27-jose-no-administra','José / CAPTURISTA: intenta modificar CONSULTA','José no tiene roles.write; el servidor rechaza su intento de agregar concepts.write.',grant('José','CONSULTA','concepts.write'),'FORBIDDEN');
  const deniedGrant=await sql('28-lista-no-modificada','MySQL: José no modificó la lista','El intento de José no creó ni activó la pareja CONSULTA + concepts.write.',pairSql('CONSULTA','concepts.write'));
  assert(!deniedGrant.filas.some(r=>r[3]===1),'José cambió los permisos');
  await gql('29-ana-si-administra','Ana / ADMINISTRADOR: agrega concepts.write a CONSULTA','Ana tiene roles.write y la misma operación sí se guarda.',grant('Ana','CONSULTA','concepts.write'));
  await gql('30-ana-restaura-consulta','Ana: retira concepts.write de CONSULTA','Consulta vuelve a quedar sin permisos de escritura y se conserva la fila inactiva.',remove('CONSULTA','concepts.write'));
  const final=await sql('31-select-final','SELECT final de role_permissions','Las 26 relaciones activas coinciden con la matriz inicial; las dos pruebas retiradas permanecen inactivas.',sqlMatrix);
  for(const role of Object.keys(MATRIX))assert(JSON.stringify(final.filas.filter(r=>r[0]===role&&r[2]===1).map(r=>r[1]).sort())===JSON.stringify(initial[role]),'Matriz final incorrecta: '+role);
  await sql('32-conteos-antes-reinicio','Catálogos antes de reiniciar','Se conservan cuatro roles, diez permisos y 26 relaciones activas.',catalogSql);
  await fs.writeFile(path.join(OUT,'resumen.json'),JSON.stringify({estado:'PRUEBAS_COMPLETADAS',initial,stamp,ids,catalogSql},null,2));
 } finally {await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
