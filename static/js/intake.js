function uiGettext(message) { return typeof gettext === "function" ? gettext(message) : message; }
function uiInterpolate(message, values) { return message.replace(/%\(([^)]+)\)s/g, (_, key) => String(values[key])); }
(() => {
  const form = document.querySelector('#intake-form');
  if (!form) return;
  const submit = document.querySelector('#intake-submit'), panel = document.querySelector('#intake-panel');
  const loading = document.querySelector('#intake-loading'), feedback = document.querySelector('#intake-feedback');
  const result = document.querySelector('#intake-result'), remove = document.querySelector('#intake-delete');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
  let timer, deleteUrl, pending = false;
  const message = text => { feedback.textContent = text; };
  async function jsonRequest(url, options = {}) {
    const response = await fetch(url, {...options, cache: 'no-store', headers: {'Accept': 'application/json', ...options.headers}, signal: AbortSignal.timeout(60000)});
    if (response.redirected) throw new Error(uiGettext('Votre session a expiré. Reconnectez-vous.'));
    const data = await response.json();
    if (!response.ok) {
      for (const [key, errors] of Object.entries(data.fields || {})) {
        const node = form.querySelector(`[data-field-error="${key}"]`);
        if (node) node.textContent = errors.map(error => error.message).join(' ');
      }
      throw new Error(data.error || uiGettext('La demande a échoué. Réessayez.'));
    }
    return data;
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (pending || !form.reportValidity()) return;
    pending = true; submit.disabled = true; remove.disabled = true; panel.setAttribute('aria-busy', 'true');
    loading.hidden = false; result.hidden = true;
    form.querySelectorAll('[data-field-error]').forEach(node => { node.textContent = ''; });
    message(uiGettext('Préparation en cours.'));
    const start = Date.now(); document.querySelector('#intake-clock').textContent = '0';
    timer = setInterval(() => { document.querySelector('#intake-clock').textContent = Math.floor((Date.now()-start)/1000); }, 1000);
    try {
      const job = await jsonRequest(form.action, {method: 'POST', body: new FormData(form), headers: {'X-CSRFToken': csrf}});
      deleteUrl = job.delete_url; remove.hidden = false;
      while (Date.now()-start < 125000) {
        const data = await jsonRequest(job.status_url);
        if (data.status === 'ready') {
          result.hidden = false;
          const translations = {'Dermatology': uiGettext('Dermatologie'), 'Cardiology': uiGettext('Cardiologie'), 'General Medicine': uiGettext('Médecine générale')};
          const specialty = data.doctors[0]?.specialty;
          document.querySelector('#intake-specialty').textContent = translations[specialty] || specialty || uiGettext('À préciser ensemble');
          document.querySelector('#intake-explanation').textContent = specialty
            ? uiGettext('D’après votre description, cette spécialité est une piste à explorer avec un professionnel.')
            : data.result.explanation;
          document.querySelector('#intake-doctor-count').textContent = uiInterpolate(uiGettext("Profils disponibles : %(count)s"), {count:data.doctors.length});
          const doctors = document.querySelector('#intake-doctors'); doctors.replaceChildren();
          if (!data.doctors.length) doctors.textContent = uiGettext('Aucun médecin correspondant dans l’annuaire. Contactez un professionnel pour préciser votre besoin.');
          for (const doctor of data.doctors) {
            const card = document.createElement('article'); card.className = 'intake-doctor';
            const identity = document.createElement('div'); identity.className = 'intake-doctor-identity';
            const avatar = document.createElement('span'); avatar.className = 'intake-avatar'; avatar.setAttribute('aria-hidden', 'true');
            avatar.textContent = doctor.name.trim().split(/\s+/).slice(0,2).map(word => word[0]).join('').toUpperCase() || '✚';
            const info = document.createElement('div');
            const name = document.createElement('h4'); name.textContent = uiInterpolate(uiGettext("Dr %(v0)s"), {v0:(doctor.name)});
            const label = document.createElement('p'); label.textContent = translations[doctor.specialty] || doctor.specialty;
            const badge = document.createElement('span'); badge.className = 'intake-approved'; badge.textContent = uiGettext('✓ Profil approuvé');
            info.append(name, label, badge); identity.append(avatar, info);
            const link = document.createElement('a'); link.className = 'care-btn intake-book';
            link.href = doctor.url; link.textContent = uiGettext('Choisir un créneau →');
            link.setAttribute('aria-label', uiInterpolate(uiGettext("Choisir un créneau avec Dr %(v0)s"), {v0:(doctor.name)}));
            card.append(identity, link); doctors.append(card);
          }
          document.querySelector('#intake-timing').textContent = uiInterpolate(uiGettext("Orientation préparée avec une IA. Temps de traitement : %(v0)s s."), {v0:((data.duration_ms/1000).toFixed(1))});
          message(uiGettext('Votre orientation est prête.')); return;
        }
        if (data.status !== 'pending') throw new Error(data.error || uiGettext('Orientation indisponible.'));
        await new Promise(resolve => setTimeout(resolve, 1500));
      }
      throw new Error(uiGettext('Le traitement prend trop de temps. Contactez un professionnel ou réessayez plus tard.'));
    } catch (error) { message(error.name === 'TimeoutError' ? uiGettext('Le serveur ne répond pas à temps. Réessayez plus tard.') : error.message); }
    finally { clearInterval(timer); pending = false; submit.disabled = false; remove.disabled = false; loading.hidden = true; panel.setAttribute('aria-busy', 'false'); }
  });
  remove.addEventListener('click', async () => {
    if (!deleteUrl || pending) return;
    remove.disabled = true;
    try { await jsonRequest(deleteUrl, {method: 'POST', headers: {'X-CSRFToken': csrf}}); form.reset(); result.hidden = true; remove.hidden = true; deleteUrl = null; message(uiGettext('Vos réponses enregistrées et cette orientation ont été supprimées.')); }
    catch (error) { message(error.message); }
    finally { remove.disabled = false; }
  });
})();
