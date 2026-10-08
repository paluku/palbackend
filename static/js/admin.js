// ============================================================
// ADMIN PANEL — Gestion complète
// ============================================================

// ==================== VARIABLES ====================
let recettes = [];
let marchandises = [];
let users = [];
let graphique = null;

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', () => {
  // Tabs
  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => changerOnglet(t.dataset.tab));
  });

  // Charger données
  chargerDashboard();
  chargerRecettes();
  chargerMarchandises();
  chargerUsers();
});

function changerOnglet(nom) {
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('actif', t.dataset.tab === nom)
  );
  document.querySelectorAll('.tab-panel').forEach(p =>
    p.classList.toggle('actif', p.id === `tab-${nom}`)
  );

  if (nom === 'dashboard') chargerDashboard();
}

// ==================== TOAST ====================
function toast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast visible ' + type;
  setTimeout(() => t.className = 'toast', 3000);
}

// ==================== API ====================
async function apiCall(url, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(url, options);
  return await res.json();
}

// ==================== DASHBOARD ====================
async function chargerDashboard() {
  // Stats
  const d = await apiCall('/api/stats/dashboard');
  if (d.success) {
    document.getElementById('stat-caisse-cdf').textContent =
      fmt(d.total_caisse?.CDF || 0) + ' FC';
    document.getElementById('stat-marchandises').textContent =
      fmt(d.total_marchandises || 0) + ' FC';
    document.getElementById('stat-recettes').textContent =
      d.nb_recettes || 0;
  }

  // Users
  const u = await apiCall('/api/users');
  if (u.success) {
    document.getElementById('stat-users').textContent = u.total || 0;
  }

  // Graphique
  const g = await apiCall('/api/stats/caisse?devise=CDF&jours=7');
  if (g.success) dessinerGraphique(g.data);

  // Top marchandises
  const m = await apiCall('/api/stats/marchandises?devise=CDF');
  const zone = document.getElementById('top-marchandises');
  if (m.success && m.data && m.data.length > 0) {
    zone.innerHTML = m.data.map((item, i) => `
      <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #e8ecf0;">
        <span><b>#${i + 1}</b> ${escape(item.nom)}</span>
        <b style="color:#7c3aed;">${fmt(item.prix_total)} CDF</b>
      </div>
    `).join('');
  } else {
    zone.innerHTML = '<p style="color:#94a3b8;">Aucune marchandise</p>';
  }
}

function dessinerGraphique(data) {
  const ctx = document.getElementById('graph-caisse');
  if (!ctx) return;

  if (graphique) graphique.destroy();

  graphique = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.label),
      datasets: [{
        label: 'Recettes CDF',
        data: data.map(d => d.montant),
        backgroundColor: 'rgba(243, 156, 18, 0.8)',
        borderRadius: 8,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    }
  });
}

// ==================== RECETTES ====================
async function chargerRecettes() {
  const r = await apiCall('/api/recettes');
  if (r.success) {
    recettes = r.recettes;
    document.getElementById('tbody-recettes').innerHTML = r.recettes.map(rec => `
      <tr>
        <td>${rec.id}</td>
        <td><b>${escape(rec.nom)}</b></td>
        <td>${escape(rec.jour)}</td>
        <td>${rec.date}</td>
        <td>${rec.heure}</td>
        <td><b style="color:#22c55e;">${fmt(rec.montant)}</b></td>
        <td>${rec.devise}</td>
        <td>
          <button class="btn-sm btn-edit" onclick="modifierRecette(${rec.id})">✏️</button>
          <button class="btn-sm btn-delete" onclick="supprimerRecette(${rec.id})">🗑</button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8;">Aucune recette</td></tr>';
  }
}

function ouvrirAjoutRecette() {
  document.getElementById('titre-modale-recette').textContent = 'Nouvelle recette';
  document.getElementById('recette-id').value = '';
  document.getElementById('recette-nom').value = '';
  document.getElementById('recette-jour').value = 'Lundi';
  document.getElementById('recette-date').value = new Date().toISOString().slice(0, 10);
  document.getElementById('recette-heure').value = '08:00';
  document.getElementById('recette-montant').value = '';
  document.getElementById('recette-devise').value = 'CDF';
  document.getElementById('recette-description').value = '';
  document.getElementById('modale-recette').classList.add('ouverte');
}

function modifierRecette(id) {
  const r = recettes.find(x => x.id === id);
  if (!r) return;

  document.getElementById('titre-modale-recette').textContent = 'Modifier recette';
  document.getElementById('recette-id').value = r.id;
  document.getElementById('recette-nom').value = r.nom;
  document.getElementById('recette-jour').value = r.jour;
  document.getElementById('recette-date').value = r.date;
  document.getElementById('recette-heure').value = r.heure;
  document.getElementById('recette-montant').value = r.montant;
  document.getElementById('recette-devise').value = r.devise;
  document.getElementById('recette-description').value = r.description || '';
  document.getElementById('modale-recette').classList.add('ouverte');
}

async function sauvegarderRecette(e) {
  e.preventDefault();
  const id = document.getElementById('recette-id').value;
  const data = {
    nom: document.getElementById('recette-nom').value,
    jour: document.getElementById('recette-jour').value,
    date: document.getElementById('recette-date').value,
    heure: document.getElementById('recette-heure').value,
    montant: parseFloat(document.getElementById('recette-montant').value),
    devise: document.getElementById('recette-devise').value,
    description: document.getElementById('recette-description').value,
  };

  let res;
  if (id) {
    res = await apiCall(`/api/recettes/${id}`, 'PUT', data);
  } else {
    res = await apiCall('/api/recettes', 'POST', data);
  }

  if (res.success) {
    toast(id ? '✅ Modifiée' : '✅ Ajoutée', 'success');
    fermerModale('modale-recette');
    chargerRecettes();
    chargerDashboard();
  } else {
    toast('❌ ' + (res.error || 'Erreur'), 'error');
  }
}

async function supprimerRecette(id) {
  if (!confirm('Supprimer cette recette ?')) return;

  const res = await apiCall(`/api/recettes/${id}`, 'DELETE');
  if (res.success) {
    toast('🗑 Supprimée', 'success');
    chargerRecettes();
    chargerDashboard();
  } else {
    toast('❌ ' + (res.error || 'Erreur'), 'error');
  }
}

// ==================== MARCHANDISES ====================
async function chargerMarchandises() {
  const r = await apiCall('/api/marchandises');
  if (r.success) {
    marchandises = r.marchandises;
    document.getElementById('tbody-marchandises').innerHTML = r.marchandises.map(m => `
      <tr>
        <td>${m.id}</td>
        <td><b>${escape(m.nom)}</b></td>
        <td>${fmt(m.prix_unitaire)}</td>
        <td>${m.quantite}</td>
        <td>${m.reduction_pct}%</td>
        <td><b style="color:#7c3aed;">${fmt(m.prix_total_net)}</b></td>
        <td>${m.devise}</td>
        <td>
          <button class="btn-sm btn-edit" onclick="modifierMarchandise(${m.id})">✏️</button>
          <button class="btn-sm btn-delete" onclick="supprimerMarchandise(${m.id})">🗑</button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="8" style="text-align:center;padding:30px;color:#94a3b8;">Aucune marchandise</td></tr>';
  }
}

function ouvrirAjoutMarchandise() {
  document.getElementById('titre-modale-marchandise').textContent = 'Nouvelle marchandise';
  document.getElementById('marchandise-id').value = '';
  document.getElementById('marchandise-nom').value = '';
  document.getElementById('marchandise-description').value = '';
  document.getElementById('marchandise-prix').value = '';
  document.getElementById('marchandise-quantite').value = '1';
  document.getElementById('marchandise-reduction').value = '0';
  document.getElementById('marchandise-devise').value = 'CDF';
  calculerTotal();
  document.getElementById('modale-marchandise').classList.add('ouverte');
}

function modifierMarchandise(id) {
  const m = marchandises.find(x => x.id === id);
  if (!m) return;

  document.getElementById('titre-modale-marchandise').textContent = 'Modifier marchandise';
  document.getElementById('marchandise-id').value = m.id;
  document.getElementById('marchandise-nom').value = m.nom;
  document.getElementById('marchandise-description').value = m.description || '';
  document.getElementById('marchandise-prix').value = m.prix_unitaire;
  document.getElementById('marchandise-quantite').value = m.quantite;
  document.getElementById('marchandise-reduction').value = m.reduction_pct;
  document.getElementById('marchandise-devise').value = m.devise;
  calculerTotal();
  document.getElementById('modale-marchandise').classList.add('ouverte');
}

function calculerTotal() {
  const p = parseFloat(document.getElementById('marchandise-prix').value) || 0;
  const q = parseFloat(document.getElementById('marchandise-quantite').value) || 0;
  const r = parseFloat(document.getElementById('marchandise-reduction').value) || 0;

  const brut = p * q;
  const reduction = brut * (r / 100);
  const net = brut - reduction;
  const devise = document.getElementById('marchandise-devise').value;

  document.getElementById('recap-brut').textContent = fmt(brut) + ' ' + devise;
  document.getElementById('recap-reduction').textContent = '-' + fmt(reduction) + ' ' + devise;
  document.getElementById('recap-net').textContent = fmt(net) + ' ' + devise;
}

async function sauvegarderMarchandise(e) {
  e.preventDefault();
  const id = document.getElementById('marchandise-id').value;
  const data = {
    nom: document.getElementById('marchandise-nom').value,
    description: document.getElementById('marchandise-description').value,
    prix_unitaire: parseFloat(document.getElementById('marchandise-prix').value),
    quantite: parseFloat(document.getElementById('marchandise-quantite').value),
    reduction_pct: parseFloat(document.getElementById('marchandise-reduction').value) || 0,
    devise: document.getElementById('marchandise-devise').value,
  };

  let res;
  if (id) {
    res = await apiCall(`/api/marchandises/${id}`, 'PUT', data);
  } else {
    res = await apiCall('/api/marchandises', 'POST', data);
  }

  if (res.success) {
    toast(id ? '✅ Modifiée' : '✅ Ajoutée', 'success');
    fermerModale('modale-marchandise');
    chargerMarchandises();
    chargerDashboard();
  } else {
    toast('❌ ' + (res.error || 'Erreur'), 'error');
  }
}

async function supprimerMarchandise(id) {
  if (!confirm('Supprimer cette marchandise ?')) return;

  const res = await apiCall(`/api/marchandises/${id}`, 'DELETE');
  if (res.success) {
    toast('🗑 Supprimée', 'success');
    chargerMarchandises();
    chargerDashboard();
  } else {
    toast('❌ ' + (res.error || 'Erreur'), 'error');
  }
}

// ==================== UTILISATEURS ====================
async function chargerUsers() {
  const r = await apiCall('/api/users');
  if (r.success) {
    users = r.users;
    document.getElementById('tbody-users').innerHTML = r.users.map(u => `
      <tr>
        <td>${u.id}</td>
        <td><b>${escape(u.nom)}</b></td>
        <td>${escape(u.email)}</td>
        <td>
          <select onchange="changerRole(${u.id}, this.value)" style="padding:4px 8px;border-radius:6px;border:1px solid #d5dbdb;">
            <option value="user" ${u.role === 'user' ? 'selected' : ''}>Utilisateur</option>
            <option value="moderator" ${u.role === 'moderator' ? 'selected' : ''}>Modérateur</option>
            <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
          </select>
        </td>
        <td>${u.email_verified ? '✅' : '⚠️'}</td>
        <td>${u.created_at}</td>
        <td>
          <button class="btn-sm btn-delete" onclick="supprimerUser(${u.id})">🗑</button>
        </td>
      </tr>
    `).join('');
  }
}

async function changerRole(id, role) {
  const res = await apiCall(`/api/users/${id}/role`, 'PUT', { role });
  if (res.success) {
    toast('✅ Rôle modifié', 'success');
  } else {
    toast('❌ ' + (res.error || 'Erreur'), 'error');
  }
}

async function supprimerUser(id) {
  if (!confirm('Supprimer cet utilisateur ?')) return;

  const res = await apiCall(`/api/users/${id}`, 'DELETE');
  if (res.success) {
    toast('🗑 Supprimé', 'success');
    chargerUsers();
    chargerDashboard();
  } else {
    toast('❌ ' + (res.error || 'Erreur'), 'error');
  }
}

// ==================== UTILS ====================
function fermerModale(id) {
  document.getElementById(id).classList.remove('ouverte');
}

function fmt(n) {
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n || 0);
}

function escape(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// Fermer modale en cliquant à côté
document.querySelectorAll('.modale').forEach(m => {
  m.addEventListener('click', e => {
    if (e.target === m) m.classList.remove('ouverte');
  });
});