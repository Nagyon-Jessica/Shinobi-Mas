const applicationServerPublicKey = 'BNYTz3FBz6KfOfVJSLyPsMm_lXQgsdS77kEpTy65A1vUDuimC7euCA_QEw_IJnJ-QYIwCV-YEqAtuStoWd3-3yc';

let isSubscribed = false;
let swRegistration = null;

function urlB64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register("sw.js")
  .then(function(reg) {
    console.log('登録に成功しました。', reg);
    swRegistration = reg;
    initialiseUI();
  }).catch(function(error) {
    console.log('登録に失敗しました。' + error);
  });
};

function initialiseUI() {
  if (!isSubscribed) {
    subscribeUser();
  }

  // Set the initial subscription value
  swRegistration.pushManager.getSubscription()
  .then(function(subscription) {
    isSubscribed = !(subscription === null);
    if (isSubscribed) {
      console.log('User IS subscribed.');
    } else {
      console.log('User is NOT subscribed.');
    }
  });
}

function subscribeUser() {
  const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
  swRegistration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: applicationServerKey
  })
  .then(function(subscription) {
    console.log('User is subscribed:', subscription);

    sendSubData(subscription);

    isSubscribed = true;
  })
  .catch(function(err) {
    console.log('Failed to subscribe the user: ', err);
  });
}

const sendSubData = async (subscription) => {
  const browser = navigator.userAgent.match(/(firefox|msie|chrome|safari|trident)/ig)[0].toLowerCase();
  const data = {
      status_type: 'subscribe',
      subscription: subscription.toJSON(),
      browser: browser,
  };

  const res = await fetch('/webpush/save_information', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: {
          'content-type': 'application/json'
      },
      credentials: "include"
  });

  handleResponse(res);
};

const handleResponse = (res) => {
  console.log(res.status);
};
