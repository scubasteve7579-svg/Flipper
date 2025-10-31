const axios = require('axios');

const clientId = 'StephenT-Flipper-PRD-988d256be-0928a4a9'; // Your App ID
const clientSecret = 'PRD-a13b478403d-f288-45ef-9275-c12a'; // Your Cert ID
const auth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');

const scopes = 'https://api.ebay.com/oauth/api_scope/buy.browse.readonly';

axios.post('https://api.ebay.com/identity/v1/oauth2/token', 
  `grant_type=client_credentials&scope=${encodeURIComponent(scopes)}`,
  {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': `Basic ${auth}`
    }
  }
).then(response => {
  console.log('App Token:', response.data.access_token);
  console.log('Expires In:', response.data.expires_in);
  console.log('Scopes:', response.data.scope);
}).catch(err => console.error(err.response ? err.response.data : err));