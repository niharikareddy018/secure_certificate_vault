const api = {
  async post(path, body) {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    return r.json();
  },
  async form(path, formData, token) {
    const r = await fetch(path, { method: 'POST', headers: token ? { 'Authorization': `Bearer ${token}` } : {}, body: formData });
    return r.json();
  },
  async get(path, token) {
    const r = await fetch(path, { headers: token ? { 'Authorization': `Bearer ${token}` } : {} });
    return r.json();
  }
};

function on(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener('submit', (e) => { e.preventDefault(); handler(new FormData(el)); });
}

on('registerForm', async (fd) => {
  const email = fd.get('email');
  const password = fd.get('password');
  const role = fd.get('role');
  const res = await api.post('/api/register', { email, password, role });
  const msg = document.getElementById('registerMsg');
  msg.textContent = res.error || 'Registered';
});

on('loginForm', async (fd) => {
  const email = fd.get('email');
  const password = fd.get('password');
  const res = await api.post('/api/login', { email, password });
  const msg = document.getElementById('loginMsg');
  if (res.access_token) {
    localStorage.setItem('token', res.access_token);
    msg.textContent = 'Logged in';
  } else {
    msg.textContent = res.error || 'Login failed';
  }
});

on('issueForm', async (fd) => {
  const token = localStorage.getItem('token');
  const res = await api.form('/api/certificates', fd, token);
  const div = document.getElementById('issueResult');
  div.textContent = JSON.stringify(res, null, 2);
});

on('verifyForm', async (fd) => {
  const hash = fd.get('hash');
  const res = await api.get(`/api/verify?hash=${encodeURIComponent(hash)}`);
  const pre = document.getElementById('verifyResult');
  pre.textContent = JSON.stringify(res, null, 2);
});

const btn = document.getElementById('loadCerts');
if (btn) {
  btn.addEventListener('click', async () => {
    const token = localStorage.getItem('token');
    const res = await api.get('/api/certificates', token);
    const pre = document.getElementById('myCerts');
    pre.textContent = JSON.stringify(res, null, 2);
  });
}