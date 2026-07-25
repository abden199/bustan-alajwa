(function(){
    if(window.google&&window.google.script&&window.google.script.run&&window.google.script.run._ok)return;
    var _s=null,_f=null;
    function go(m,u,b){
        var sf=_s,ff=_f;_s=null;_f=null;
        var o={method:m,headers:{}};
        if(b!==undefined&&b!==null){o.headers['Content-Type']='application/json';o.body=JSON.stringify(b)}
        fetch(u,o)
            .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
            .then(function(d){if(sf)sf(d)})
            .catch(function(e){console.error('ERR:',u,e);if(ff)ff({message:e.message||'error'})})
    }
    var R={_ok:true};
    R.withSuccessHandler=function(fn){_s=fn;return R};
    R.withFailureHandler=function(fn){_f=fn;return R};
    R.srvGetData=function(){go('GET','/api/data')};
    R.srvGetReportData=function(){go('GET','/api/report-data')};
    R.srvGetRepData=function(x){go('GET','/api/rep-data/'+x)};
    R.srvAuthenticate=function(u,p){go('POST','/api/auth',[u,p])};
    R.srvAddPurchase=function(d){go('POST','/api/purchases',d)};
    R.srvUpdatePurchase=function(i,d){go('PUT','/api/purchases/'+i,d||{})};
    R.srvDeletePurchase=function(i){go('DELETE','/api/purchases/'+i)};
    R.srvAddAdvance=function(d){go('POST','/api/advances',d)};
    R.srvUpdateAdvance=function(i,d){go('PUT','/api/advances/'+i,d||{})};
    R.srvDeleteAdvance=function(i){go('DELETE','/api/advances/'+i)};
    R.srvAddAdvRequest=function(d){go('POST','/api/adv-requests',d)};
    R.srvUpdateAdvRequest=function(i,d){go('PUT','/api/adv-requests/'+i,d||{})};
    R.srvAddExpenses=function(d){go('POST','/api/expenses',d)};
    R.srvUpdateExpense=function(i,d){go('PUT','/api/expenses/'+i,d||{})};
    R.srvSaveUsers=function(d){go('POST','/api/users',d)};
    R.srvSaveSuppliers=function(d){go('POST','/api/suppliers',d)};
    R.srvSaveCompanies=function(d){go('POST','/api/companies',d)};
    R.srvSaveAll=function(d){go('POST','/api/save-all',d)};
    R.importFromUploadedFile=function(d,n){go('POST','/api/import/upload',{data:d,name:n})};
    R.importFromDriveFile=function(x){go('POST','/api/import/upload',{fileId:x})};
    R.importFromSheet=function(x){go('POST','/api/import/upload',{sheetId:x})};
    R.exportToDriveFile=function(){window.open('/api/export-file','_blank')};
    window.google={script:{run:R}};
    console.log('gas-compat ready');
})();
