const fs=require('fs/promises'),path=require('path'),cp=require('child_process'),util=require('util');
const exec=util.promisify(cp.execFile);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const ROOT=path.resolve(__dirname,'..');
const PY=process.env.PYTHON || 'python3';
const D=path.join(ROOT,'docs/unidad2-actividad5'), O=path.join(D,'evidencias'), V=path.join(D,'variables'),URL=process.env.ACTIVITY5_URL || 'http://127.0.0.1:8007/graphql';
const assert=(x,m)=>{if(!x)throw Error(m)};
(async()=>{
await fs.mkdir(O,{recursive:true});await fs.mkdir(V,{recursive:true});
const ids=JSON.parse(await fs.readFile(path.join(ROOT,'docs/evidencias/unidad2-actividad4/ids.json'),'utf8'));
await fs.writeFile(path.join(D,'ids.json'),JSON.stringify(ids,null,2));
const actor=ids.actors.Ana,roleId=ids.roles.CAPTURISTA;
const s0=['accounts.read','concepts.read','transactions.read','transactions.write'].map(c=>ids.permissions[c]);
const proposal=list=>({actor,input:{roleId,permissionIds:list}}),s1=[...s0,ids.permissions['accounts.write']];
const vars={actor:{actor},s0:proposal(s0),s1:proposal(s1),vacia:proposal([]),payments:{actor,resource:'PAYMENTS'},continuidad:{actor,company:ids.companyId},movimiento:{actor,input:{accountId:ids.accountId,conceptId:ids.conceptId,transactionType:'INCOME',amount:'125.50',shortDescription:'E10 Unidad II Actividad 5'}}};
for(const [name,value] of Object.entries(vars))await fs.writeFile(path.join(V,name+'.json'),JSON.stringify(value,null,2));
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM || '/usr/bin/chromium',args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1500,height:1200}});
let records=process.env.AFTER_RESTART?JSON.parse(await fs.readFile(path.join(O,'registro.json'),'utf8')):[];
const save=async()=>fs.writeFile(path.join(O,'registro.json'),JSON.stringify(records,null,2));
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
async function state(name,action='snapshot',id){
 const {stdout}=await exec(PY,['-m','scripts.activity5_state',action,...(id?[String(id)]:[])],{cwd:ROOT,env:{...process.env,SETTINGS_FILE:'.env.docker'}});
 const result=JSON.parse(stdout);await fs.writeFile(path.join(O,name+'.json'),JSON.stringify(result,null,2));
 const body='<!doctype html><meta charset="utf-8"><style>body{font:16px system-ui;margin:30px;color:#18283e}pre{font:15px/1.5 monospace;background:#f3f6fa;padding:20px;white-space:pre-wrap}</style><h1>'+name+' · MySQL '+result.mysql+'</h1><p>Resultado real de SQLAlchemy. IDs, pares y estados de las relaciones.</p><pre>'+esc(result.sql)+'</pre><pre>'+esc(JSON.stringify(result,null,2))+'</pre>';
 await page.setContent(body);await page.screenshot({path:path.join(O,name+'.png'),fullPage:true});
 records.push({name,kind:'SQL',result,capture:name+'.png'});await save();return result;
}
const shortFields='role{code} activated{code} deactivated{code} unchanged{code} finalCount changed';
const apply=`mutation AplicarConfiguracion($actor:ID!,$input:SetRolePermissionsInput!){setRolePermissions(actorCompanyUserId:$actor,input:$input){${shortFields}}}`;
const preview='query RevisarConfiguracion($actor:ID!,$input:SetRolePermissionsInput!){previewRolePermissions(actorCompanyUserId:$actor,input:$input){role{code} current{code} toActivate{code} toDeactivate{code} unchanged{code} finalCount}}';
async function gql(name,query,variables,invalid=false){
 await page.goto(URL,{waitUntil:'networkidle',timeout:60000});
 await page.locator('.graphiql-query-editor .CodeMirror').waitFor({timeout:45000});
 await page.evaluate(({q,v})=>{
  document.querySelector('.graphiql-query-editor .CodeMirror').CodeMirror.setValue(q);
  const vm=document.querySelector('.graphiql-editor-tool .graphiql-editor:not(.hidden) .CodeMirror');
  if(vm)vm.CodeMirror.setValue(JSON.stringify(v,null,2));
  document.querySelectorAll('.CodeMirror').forEach(e=>e.CodeMirror?.setOption('lineWrapping',true));
 },{q:query,v:variables});
 await page.waitForTimeout(700);
 const vm=await page.locator('.graphiql-editor-tool .graphiql-editor:not(.hidden) .CodeMirror').count();
 if(!vm)throw Error('No se encontró editor de variables');
 const prettify=page.locator('button[title*="Prettify"],button[aria-label*="Prettify"]').first();if(await prettify.count())await prettify.click();
 await page.addStyleTag({content:'.CodeMirror{font-size:16px!important;line-height:22px!important}'});
 await page.waitForTimeout(500);
 const pending=page.waitForResponse(r=>r.url()===URL&&r.request().method()==='POST');
 await page.locator('button[title*="Execute"],button[aria-label*="Execute"],button[title*="Run"],button[aria-label*="Run"]').first().click();
 const response=await pending,result=await response.json();
 assert(invalid?result.errors:!result.errors,name+': '+JSON.stringify(result));
 await page.waitForTimeout(350);
 await page.screenshot({path:path.join(O,name+'.png'),fullPage:true});
 records.push({name,kind:'GraphiQL',query,variables,result,http:response.status(),capture:name+'.png'});await save();
 await fs.writeFile(path.join(V,name+'.json'),JSON.stringify(variables,null,2));console.log(name+' OK');return result.data;
}
try{
if(process.env.AFTER_RESTART){
 const after=await state('E08-despues-reinicio');const before=JSON.parse(await fs.readFile(path.join(O,'E08-antes-reinicio.json')));
 assert(JSON.stringify(after.rows)===JSON.stringify(before.rows),'Reinicio alteró filas');assert(after.matrix.CAPTURISTA.length===0&&after.roles===4&&after.permissions===10,'Reinicio inválido');
 await gql('E08-consulta-reiniciada',preview,vars.vacia);
 await gql('E09-restaurar',apply,vars.s0);
 const final=await state('E09-matriz-final');const initial=JSON.parse(await fs.readFile(path.join(D,'configuracion_inicial.json')));
 assert(JSON.stringify(final.matrix)===JSON.stringify(initial)&&!final.duplicates.length,'La matriz no coincide');
 await fs.writeFile(path.join(D,'configuracion_final.json'),JSON.stringify(final.matrix,null,2));
 await gql('E10-cuentas','query ConsultarCuentas($actor:ID!,$company:ID!){accounts(actorCompanyUserId:$actor,companyId:$company){id companyId name}}',vars.continuidad);
 const tx=await gql('E10-movimiento','mutation RegistrarMovimiento($actor:ID!,$input:CreateTransactionInput!){createTransaction(actorCompanyUserId:$actor,input:$input){id accountId conceptId amount capturedBy}}',vars.movimiento);
 const persisted=await state('E10-movimiento-persistido','snapshot',tx.createTransaction.id);
 assert(persisted.transaction.length===1&&persisted.transaction[0].amount==='125.50','No persistió movimiento');
 console.log('COMPLETADO E01-E10');return;
}
const initial=await state('E01-inicial');assert(initial.roles===4&&initial.permissions===10&&initial.matrix.CAPTURISTA.length===4,'Matriz inicial inválida');
await fs.writeFile(path.join(D,'configuracion_inicial.json'),JSON.stringify(initial.matrix,null,2));
await gql('E01-catalogos','query PuntoDePartida($actor:ID!){roles(actorCompanyUserId:$actor){id code} permissions(actorCompanyUserId:$actor){id code}}',vars.actor);
const filtered=await gql('E02-alias-fragmento','query ExplorarCatalogo($actor:ID!){cuentas:permissionCatalog(actorCompanyUserId:$actor,resource:ACCOUNTS){...DatosPermiso} movimientos:permissionCatalog(actorCompanyUserId:$actor,resource:TRANSACTIONS){...DatosPermiso}} fragment DatosPermiso on Permission{id code name}',vars.actor);
assert(filtered.cuentas.length===2&&filtered.movimientos.length===2,'Catálogo incorrecto');
await gql('E02-sin-filtro','query CatalogoCompleto($actor:ID!){permissionCatalog(actorCompanyUserId:$actor){code}}',vars.actor);
await gql('E02-enum-invalido','query CatalogoCompleto($actor:ID!,$resource:PermissionResource){permissionCatalog(actorCompanyUserId:$actor,resource:$resource){code}}',vars.payments,true);
const before=await state('E03-antes');const plan=await gql('E03-previsualizar',preview,vars.s1);const after=await state('E03-despues');
assert(JSON.stringify(before.rows)===JSON.stringify(after.rows),'Preview escribió');assert(plan.previewRolePermissions.finalCount===5&&plan.previewRolePermissions.toActivate[0].code==='accounts.write','Plan incorrecto');
const first=await gql('E04-primera',apply,vars.s1);const one=await state('E04-sql-primera');
const second=await gql('E04-repetida',apply,vars.s1);const two=await state('E04-sql-repetida');
assert(first.setRolePermissions.changed&&!second.setRolePermissions.changed&&JSON.stringify(one.rows)===JSON.stringify(two.rows),'No idempotente');
await gql('E05-desactivar',apply,vars.s0);const off=await state('E05-inactiva');await gql('E05-reactivar',apply,vars.s1);const on=await state('E05-reactivada');
const pair=x=>x.rows.find(r=>r.rol==='CAPTURISTA'&&r.permiso==='accounts.write');assert(pair(one).relacion_id===pair(off).relacion_id&&pair(off).relacion_id===pair(on).relacion_id&&!pair(off).relacion_activa&&pair(on).relacion_activa&&pair(off).permiso_activo,'Reactivación incorrecta');
for(const variant of ['rol-inexistente','rol-inactivo','administrador','permiso-inexistente','permiso-inactivo','duplicado']){
 const v=JSON.parse(JSON.stringify(vars.s1));
 if(variant==='rol-inexistente')v.input.roleId='999999';
 if(variant==='administrador')v.input.roleId=ids.roles.ADMINISTRADOR;
 if(variant==='permiso-inexistente')v.input.permissionIds.push('999999');
 if(variant==='duplicado')v.input.permissionIds.push(Number(v.input.permissionIds[0]));
 const action=variant==='rol-inactivo'?'role':variant==='permiso-inactivo'?'permission':null;
 if(action)await state('E06-'+variant+'-preparacion',action+'_off');
 try{
 const b=await state('E06-'+variant+'-antes');
 for(const [op,q]of [['preview',preview],['aplicar',apply]])await gql('E06-'+variant+'-'+op,q,v,true);
 const a=await state('E06-'+variant+'-despues');assert(JSON.stringify(b.rows)===JSON.stringify(a.rows),'Error modificó relaciones');
 }finally{if(action)await state('E06-'+variant+'-restauracion',action+'_on');}
}
await gql('E08-vaciar',apply,vars.vacia);const empty=await state('E08-antes-reinicio');assert(empty.matrix.CAPTURISTA.length===0,'Lista no vacía');
console.log('REINICIAR API Y EJECUTAR AFTER_RESTART=1');
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
