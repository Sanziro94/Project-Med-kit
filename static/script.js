function showMsg(msg, isError = false) {
    const el = document.getElementById("status-msg");
    if (el) {
        el.textContent = msg;
        el.style.color = isError ? "#dc3545" : "#28a745";
        el.style.display = "block";
    } else {
        alert(msg);
    }
}

function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.dataset.originalText = btn.dataset.originalText || btn.textContent;
    btn.textContent = loading ? "Loading…" : btn.dataset.originalText;
}


async function CredentialCheck() {
    const user = document.getElementById("username").value.trim();
    const pass = document.getElementById("password").value;
    const btn  = document.querySelector("button[onclick='CredentialCheck()']");

    if (!user || !pass) { showMsg("Please fill in all fields.", true); return; }

    setLoading(btn, true);
    try {
        const resp = await fetch("/login", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ username: user, password: pass })
        });
        const data = await resp.json();

        if (resp.ok) {
            window.location.href = data.redirect;
        } else {
            showMsg("Error: " + (data.error || data.message || "Unknown error"), true);
        }
    } catch (err) {
        console.error("Connection error:", err);
        showMsg("Connection error — is the server running?", true);
    } finally {
        setLoading(btn, false);
    }
}

async function CredentialSave() {
    const nuser = document.getElementById("nusername").value.trim();
    const user  = document.getElementById("user").value.trim();
    const npass = document.getElementById("npassword").value;
    const admin = document.getElementById("admin").value;
    // BUG FIX: original read id="passkey" but input had id="passk"
    const passk = document.getElementById("passk").value.trim();
    const btn   = document.querySelector("button[onclick='CredentialSave()']");

    if (!nuser || !user || !npass || !passk) {
        showMsg("Please fill in all required fields.", true); return;
    }

    setLoading(btn, true);
    try {
        // 1. Register account
        const resp = await fetch("/register", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ username: nuser, password: npass,
                                     admin: admin, user: user, passk: passk })
        });
        const data = await resp.json();

        if (!resp.ok) {
            showMsg("Registration error: " + (data.error || data.message || "Unknown error"), true);
            return;
        }
        
        try {
            const rfid = await fetch("/pending-rfid", {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ username: nuser })
            });
            const rfidData = await rfid.json();
            if (!rfid.ok) {
                showMsg("Account created but RFID queuing failed: " + (rfidData.message || ""), true);
            } else {
                showMsg("Account created! Ask the patient to scan their RFID card on the reader.");
            }
        } catch {
            showMsg("Account created but could not reach RFID service.", true);
        }
        
        setTimeout(() => { window.location.href = data.redirect; }, 1500);

    } catch (err) {
        console.error("Connection error:", err);
        showMsg("Connection error — is the server running?", true);
    } finally {
        setLoading(btn, false);
    }
}


async function Sendinfo(value) {
    const timeVal = document.getElementById("time"   + value).value.trim();
    const user    = document.getElementById("user"   + value).value.trim();
    const object  = document.getElementById("Object" + value).value.trim();
    const btn     = document.querySelector(`button[onclick="Sendinfo(${value})"]`);

    if (!user || !timeVal || !object) {
        showMsg("Please fill in all fields for drawer " + value + ".", true); return;
    }

    setLoading(btn, true);
    try {
        const resp = await fetch("/Application", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ user: user, time: timeVal,
                                     Object: object, Tiroirs: value })
        });
        const data = await resp.json();

        if (resp.ok) {
            showMsg("Drawer " + value + " saved successfully!");
        } else {
            showMsg("Error: " + (data.message || data.error || "Unknown error"), true);
        }
    } catch (err) {
        console.error("Connection error:", err);
        showMsg("Connection error — is the server running?", true);
    } finally {
        setLoading(btn, false);
    }
}

async function Eraseinfo(value) {
    const timeVal = document.getElementById("time"   + value).value.trim();
    const user    = document.getElementById("user"   + value).value.trim();
    const object  = document.getElementById("Object" + value).value.trim();
    const btn     = document.querySelector(`button[onclick="Eraseinfo(${value})"]`);

    if (!user || !timeVal || !object) {
        showMsg("Please fill in all fields for drawer " + value + ".", true); return;
    }

    setLoading(btn, true);
    try {
        const resp = await fetch("/delapp", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ user: user, time: timeVal,
                                     Object: object, Tiroirs: value })
        });
        const data = await resp.json();

        if (resp.ok) {
            showMsg("Drawer " + value + " erased successfully!");
        } else {
            showMsg("Error: " + (data.message || data.error || "Unknown error"), true);
        }
    } catch (err) {
        console.error("Connection error:", err);
        showMsg("Connection error — is the server running?", true);
    } finally {
        setLoading(btn, false);
    }
}


async function Resetpass() {
    const user    = document.getElementById("username").value.trim();
    const passk   = document.getElementById("passkey").value.trim();
    const newPass = document.getElementById("password").value;
    const btn     = document.querySelector("button[onclick='Resetpass()']");

    if (!user || !passk || !newPass) {
        showMsg("All fields are required.", true); return;
    }

    setLoading(btn, true);
    try {
        const resp = await fetch("/reset-password", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ username: user, passk: passk, password: newPass })
        });
        const data = await resp.json();
        
        if (resp.ok) {
            showMsg("Password updated! Redirecting…");
            setTimeout(() => { window.location.href = "/"; }, 1500);
        } else {
            showMsg("Error: " + (data.message || data.error || "Unknown error"), true);
        }
    } catch (err) {
        console.error("Connection error:", err);
        showMsg("Connection error — is the server running?", true);
    } finally {
        setLoading(btn, false);
    }
}

async function loadTraitement() {
    const el = document.getElementById('traitement-content');
    try {
        const resp = await fetch('/my-traitement');
        if (!resp.ok) throw new Error(resp.status);
        
        const data = await resp.json();
        const t = data.traitement;

        if (!t || t.length === 0) {
            el.innerHTML = '<div class="alert">Aucun traitement assigné pour le moment.</div>';
            return;
        }

        let html = '';
        t.forEach(med => {
            // Logique de couleur pour la péremption
            const statusClass = med.perime ? 'badge-perime' : 'badge-green';
            const statusText = med.perime ? 'PÉRIMÉ' : 'VALIDE';

            html += `
                <div style="margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0;">
                    <div class="info-row">
                        <span class="info-label">Médicament</span>
                        <span class="info-value">${med.object || '—'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Heure de prise</span>
                        <span class="info-value">${med.time || '—'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">État</span>
                        <span class="badge ${statusClass}">${statusText}</span>
                    </div>
                    ${med.perime ? '<div class="alert" style="border-left-color: #dc3545; color: #dc3545;">⚠️ Ce médicament a dépassé sa durée de conservation !</div>' : ''}
                </div>
            `;
        });
        el.innerHTML = html;

    } catch (e) {
        console.error("Erreur:", e);
        el.innerHTML = '<div class="alert">Impossible de charger le traitement.</div>';
    }
}
loadTraitement();