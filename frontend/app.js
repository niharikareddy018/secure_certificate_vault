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
  div.innerHTML = '';
  const pre = document.createElement('pre');
  pre.textContent = JSON.stringify(res, null, 2);
  div.appendChild(pre);
  if (res && res.download_url) {
    const link = document.createElement('a');
    link.textContent = 'Download uploaded PDF';
    link.href = res.download_url;
    link.className = 'btn';
    link.addEventListener('click', async (e) => {
      e.preventDefault();
      const tok = localStorage.getItem('token');
      const resp = await fetch(res.download_url, { headers: tok ? { 'Authorization': `Bearer ${tok}` } : {} });
      if (!resp.ok) {
        alert('Download failed');
        return;
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = res.filename || 'certificate.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
    div.appendChild(link);
  }
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
    const el = document.getElementById('myCerts');
    el.innerHTML = '';
    (res || []).forEach((r) => {
      const item = document.createElement('div');
      item.className = 'card';
      const meta = document.createElement('div');
      meta.textContent = `${r.student_name} • ${r.course_name} • ${r.issue_date}`;
      const actions = document.createElement('div');
      const reveal = document.createElement('button');
      reveal.textContent = 'Show Hash';
      reveal.addEventListener('click', () => {
        reveal.textContent = r.file_hash;
        reveal.disabled = true;
      });
      const download = document.createElement('button');
      download.textContent = 'Download PDF';
      download.disabled = !r.download_url;
      download.addEventListener('click', async () => {
        if (!r.download_url) return;
        const tok = localStorage.getItem('token');
        const resp = await fetch(r.download_url, { headers: tok ? { 'Authorization': `Bearer ${tok}` } : {} });
        if (!resp.ok) {
          alert('Download failed');
          return;
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = r.filename || 'certificate.pdf';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
      actions.appendChild(reveal);
      actions.appendChild(download);
      item.appendChild(meta);
      item.appendChild(actions);
      el.appendChild(item);
    });
  });
}
