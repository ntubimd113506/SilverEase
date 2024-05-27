importScripts('https://static.line-scdn.net/liff/edge/2.1/sdk.js');

function initiLiff(myLiffId) {
    liff.init({
        liffId: myLiffId
    }).then(() => {
        if (!liff.isLoggedIn()) {
            alert("用戶未登入");
            liff.login();
        }
    }).catch((err) => {
        console.log('初始化失敗', err);
    });
}

$(document).ready(function () {
    initializeLiff('{{ liffid }}');  //接收傳遞的 liffid 參數
});
