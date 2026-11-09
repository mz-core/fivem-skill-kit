// Minimal NUI without a build step. The UI is untrusted: the server re-validates everything.
const panel = document.getElementById('panel');
const statusEl = document.getElementById('status');
const pointEl = document.getElementById('point');

async function post(action, payload) {
  try {
    const res = await fetch(`https://${GetParentResourceName()}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=UTF-8' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) return { ok: false, code: `http_${res.status}` };
    return await res.json();
  } catch (e) {
    return { ok: false, code: 'network_error' };
  }
}

window.addEventListener('message', (event) => {
  const { action, payload } = event.data || {};
  if (action === 'open') {
    pointEl.value = (payload && payload.defaultPoint) || 'office';
    statusEl.textContent = '';
    panel.classList.add('show');
  } else if (action === 'close') {
    panel.classList.remove('show');
  } else if (action === 'result') {
    statusEl.textContent = payload && payload.ok ? 'Allowed' : `Denied: ${payload ? payload.code : 'unknown'}`;
  }
});

document.getElementById('send').addEventListener('click', async () => {
  const res = await post('submit', { pointId: pointEl.value });
  if (!res.ok) statusEl.textContent = `Error: ${res.code}`;
});
document.getElementById('close').addEventListener('click', () => post('close'));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') post('close'); });
