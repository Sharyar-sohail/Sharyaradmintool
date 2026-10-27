/**
 * ApexSys Master Commander Dashboard Real-time Engine
 */

let activeClientId = null;
let fleetNodes = {};
let ws = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    initWebSocket();
    setupEventHandlers();
});

function initWebSocket() {
    const loc = window.location;
    const wsProto = loc.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${loc.host}/ws/dashboard`;

    updateWsIndicator(false, "CONNECTING...");
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        updateWsIndicator(true, "LIVE WS ONLINE");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWsMessage(data);
        } catch (e) {
            console.error("WS Parse Error:", e);
        }
    };

    ws.onclose = () => {
        updateWsIndicator(false, "DISCONNECTED - RETRYING");
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.error("WS Error:", err);
        ws.close();
    };
}

function updateWsIndicator(online, text) {
    const dot = document.getElementById("ws-dot");
    const label = document.getElementById("ws-label");
    if (dot && label) {
        if (online) {
            dot.classList.add("online");
        } else {
            dot.classList.remove("online");
        }
        label.innerText = text;
    }
}

function handleWsMessage(msg) {
    const event = msg.event;

    if (event === "FLEET_SNAPSHOT") {
        fleetNodes = {};
        msg.nodes.forEach(n => { fleetNodes[n.client_id] = n; });
        renderFleetList();
        if (!activeClientId && msg.nodes.length > 0) {
            selectNode(msg.nodes[0].client_id);
        }
    } else if (event === "NODE_CONNECTED" || event === "NODE_UPDATED") {
        fleetNodes[msg.client_id] = msg.node;
        renderFleetList();
        if (!activeClientId || activeClientId === msg.client_id) {
            selectNode(msg.client_id);
        }
    } else if (event === "NODE_DISCONNECTED") {
        if (fleetNodes[msg.client_id]) {
            fleetNodes[msg.client_id].status = "OFFLINE";
            renderFleetList();
            if (activeClientId === msg.client_id) {
                renderNodeHeader();
            }
        }
    } else if (event === "TELEMETRY_TICK") {
        if (activeClientId === msg.client_id) {
            updateTelemetryDisplay(msg.telemetry);
        }
    } else if (event === "DIAGNOSTICS_UPDATED") {
        if (fleetNodes[msg.client_id]) {
            fleetNodes[msg.client_id].health_score = msg.health_score;
            fleetNodes[msg.client_id].category_scores = msg.category_scores;
            fleetNodes[msg.client_id].issues = msg.issues;
            renderFleetList();
        }
        if (activeClientId === msg.client_id) {
            renderHealthGauge(msg.health_score);
            renderCategoryBars(msg.category_scores);
            renderIssuesList(msg.issues);
        }
    } else if (event === "TERMINAL_STREAM") {
        if (activeClientId === msg.client_id) {
            appendTerminalLine(msg.ts, msg.stream, msg.text);
        }
    } else if (event === "REMEDIATION_PROGRESS") {
        if (activeClientId === msg.client_id) {
            updateProgressBar(msg.progress, msg.action);
        }
    } else if (event === "VERIFICATION_COMPLETE") {
        if (activeClientId === msg.client_id) {
            hideProgressBar();
            renderVerificationDelta(msg.delta);
            // Refresh detailed state from server
            fetchNodeDetail(activeClientId);
        }
    } else if (event === "NODE_SELF_DESTRUCTED") {
        delete fleetNodes[msg.client_id];
        renderFleetList();
        if (activeClientId === msg.client_id) {
            const remaining = Object.keys(fleetNodes);
            if (remaining.length > 0) {
                selectNode(remaining[0]);
            } else {
                activeClientId = null;
                clearDashboardDisplay();
            }
        }
    }
}

function renderFleetList() {
    const list = document.getElementById("fleet-list");
    if (!list) return;

    list.innerHTML = "";
    const nodes = Object.values(fleetNodes);

    if (nodes.length === 0) {
        list.innerHTML = `<div style="color: #718096; font-size: 0.85rem; padding: 12px; text-align: center;">Waiting for client agents to connect...</div>`;
        return;
    }

    nodes.forEach(node => {
        const card = document.createElement("div");
        card.className = `node-card ${node.client_id === activeClientId ? "active" : ""}`;
        card.onclick = () => selectNode(node.client_id);

        const statusClass = `badge-${(node.status || "offline").toLowerCase()}`;
        const score = node.health_score !== undefined ? node.health_score : 100;
        const scoreColor = score >= 80 ? "var(--neon-green)" : score >= 50 ? "var(--neon-yellow)" : "var(--neon-red)";

        card.innerHTML = `
            <div class="node-card-top">
                <span class="node-name">${node.system_info?.hostname || node.client_id}</span>
                <span class="node-badge ${statusClass}">${node.status}</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: #a0aec0; margin-top: 4px;">
                <span>Score: <strong style="color: ${scoreColor}">${score}%</strong></span>
                <span>${node.system_info?.ip_address || "127.0.0.1"}</span>
            </div>
        `;
        list.appendChild(card);
    });
}

function selectNode(clientId) {
    activeClientId = clientId;
    renderFleetList();
    fetchNodeDetail(clientId);
}

async function fetchNodeDetail(clientId) {
    try {
        const res = await fetch(`/api/nodes/${clientId}`);
        if (!res.ok) return;
        const node = await res.json();
        fleetNodes[clientId] = node;

        renderNodeHeader(node);
        renderHealthGauge(node.health_score);
        renderCategoryBars(node.category_scores);
        renderIssuesList(node.issues || []);
        if (node.latest_telemetry) {
            updateTelemetryDisplay(node.latest_telemetry);
        }
        renderTerminalHistory(node.terminal_logs || []);
    } catch (e) {
        console.error("Failed to load node detail:", e);
    }
}

function renderNodeHeader(node) {
    if (!node) node = fleetNodes[activeClientId];
    if (!node) return;

    const sys = node.system_info || {};
    document.getElementById("node-title").innerText = sys.hostname || node.client_id;
    document.getElementById("node-os").innerText = `${sys.os_name || "Windows"} (${sys.architecture || "x64"})`;
    document.getElementById("node-cpu").innerText = sys.cpu_model || "Generic CPU";
    document.getElementById("node-ram").innerText = `${sys.total_ram_gb || 0} GB`;
    document.getElementById("node-ip").innerText = sys.ip_address || "127.0.0.1";

    const adminTag = document.getElementById("node-admin");
    if (adminTag) {
        adminTag.innerText = sys.is_admin ? "ADMINISTRATOR (ELEVATED)" : "STANDARD PRIVILEGE";
        adminTag.style.color = sys.is_admin ? "var(--neon-green)" : "var(--neon-yellow)";
        adminTag.style.borderColor = sys.is_admin ? "var(--neon-green)" : "var(--neon-yellow)";
    }
}

function renderHealthGauge(score) {
    const circle = document.getElementById("score-circle");
    const valElem = document.getElementById("score-val");
    if (!circle || !valElem) return;

    valElem.innerText = score;
    let color = "var(--neon-green)";
    if (score < 50) color = "var(--neon-red)";
    else if (score < 80) color = "var(--neon-yellow)";

    circle.style.background = `conic-gradient(${color} 0%, ${color} ${score}%, rgba(255, 255, 255, 0.05) ${score}%)`;
    circle.style.boxShadow = `0 0 30px ${color}44`;
    valElem.style.color = color;
}

function renderCategoryBars(scores) {
    if (!scores) return;
    const cats = [
        { id: "cat-hw", key: "Hardware" },
        { id: "cat-os", key: "Operating System" },
        { id: "cat-storage", key: "Storage" },
        { id: "cat-drivers", key: "Drivers" },
        { id: "cat-sec", key: "Security" },
    ];

    cats.forEach(c => {
        const val = scores[c.key] !== undefined ? scores[c.key] : 100;
        const fill = document.getElementById(`${c.id}-fill`);
        const text = document.getElementById(`${c.id}-val`);
        if (fill && text) {
            fill.style.width = `${val}%`;
            text.innerText = `${val}%`;

            let color = "var(--neon-green)";
            if (val < 50) color = "var(--neon-red)";
            else if (val < 80) color = "var(--neon-yellow)";
            fill.style.backgroundColor = color;
        }
    });
}

function renderIssuesList(issues) {
    const container = document.getElementById("issues-list");
    const countBadge = document.getElementById("issues-count-badge");
    if (!container) return;

    const unresolved = issues.filter(i => !i.resolved);
    if (countBadge) {
        countBadge.innerText = `${unresolved.length} Issues Detected`;
        countBadge.style.color = unresolved.length > 0 ? "var(--neon-yellow)" : "var(--neon-green)";
    }

    if (unresolved.length === 0) {
        container.innerHTML = `
            <div style="padding: 24px; text-align: center; color: var(--neon-green); font-weight: 600;">
                ✓ ALL SYSTEMS OPERATIONAL: No critical flaws, corrupt files, or hardware errors detected.
            </div>
        `;
        return;
    }

    container.innerHTML = "";
    unresolved.forEach(issue => {
        const item = document.createElement("div");
        item.className = `issue-item ${issue.severity}`;
        item.innerHTML = `
            <div class="issue-info">
                <h4>[${issue.category}] ${issue.title}</h4>
                <p>${issue.description}</p>
            </div>
            <div>
                <button class="btn-issue-fix" onclick="triggerFix('${issue.fix_id}')">Fix Issue</button>
            </div>
        `;
        container.appendChild(item);
    });
}

function updateTelemetryDisplay(t) {
    if (!t) return;
    const cpu = document.getElementById("tele-cpu");
    const ram = document.getElementById("tele-ram");
    const disk = document.getElementById("tele-disk");
    const latency = document.getElementById("tele-lat");

    if (cpu) cpu.innerText = `${Math.round(t.cpu_percent || 0)}%`;
    if (ram) ram.innerText = `${Math.round(t.ram_percent || 0)}%`;
    if (disk) disk.innerText = `${Math.round(t.disk_percent || 0)}%`;
    if (latency) latency.innerText = `${Math.round(t.net_latency_ms || 10)}ms`;
}

function appendTerminalLine(ts, stream, text) {
    const box = document.getElementById("terminal-box");
    if (!box) return;

    const line = document.createElement("div");
    line.className = `term-line ${stream}`;
    line.innerHTML = `<span class="term-tag">[${ts}]</span> ${escapeHtml(text)}`;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function renderTerminalHistory(logs) {
    const box = document.getElementById("terminal-box");
    if (!box) return;
    box.innerHTML = "";
    logs.forEach(l => appendTerminalLine(l.ts, l.stream, l.text));
}

function updateProgressBar(progress, action) {
    const bar = document.getElementById("remediation-progress-bar");
    const fill = document.getElementById("progress-fill");
    const label = document.getElementById("progress-action-label");
    const pctLabel = document.getElementById("progress-pct-label");

    if (bar && fill) {
        bar.style.display = "block";
        fill.style.width = `${progress}%`;
        if (label) label.innerText = action;
        if (pctLabel) pctLabel.innerText = `${progress}%`;
    }
}

function hideProgressBar() {
    const bar = document.getElementById("remediation-progress-bar");
    if (bar) bar.style.display = "none";
}

function renderVerificationDelta(delta) {
    if (!delta) return;
    const banner = document.getElementById("verification-delta-banner");
    if (!banner) return;

    banner.style.display = "block";
    banner.innerHTML = `
        <div style="background: rgba(0, 255, 136, 0.12); border: 1px solid var(--neon-green); border-radius: 8px; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="color: var(--neon-green); font-size: 1rem;">AUTONOMOUS REMEDIATION VERIFIED:</strong>
                <span style="color: #fff; margin-left: 10px;">Health score elevated from <strong>${delta.pre_score}%</strong> to <strong style="color: var(--neon-green);">${delta.post_score}%</strong> (+${delta.improvement}% recovery).</span>
            </div>
            <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; color: #a0aec0; cursor: pointer; font-size: 1.2rem;">&times;</button>
        </div>
    `;
}

function clearDashboardDisplay() {
    document.getElementById("node-title").innerText = "No PC Connected";
    document.getElementById("issues-list").innerHTML = "<div style='padding:20px; text-align:center;'>Connect an agent to view diagnostics.</div>";
    renderHealthGauge(100);
}

function setupEventHandlers() {
    document.getElementById("btn-master-scan")?.addEventListener("click", triggerMasterScan);
    document.getElementById("btn-fix-all")?.addEventListener("click", triggerFixAll);
    document.getElementById("btn-self-destruct")?.addEventListener("click", confirmSelfDestruct);
    document.getElementById("btn-clear-term")?.addEventListener("click", () => {
        const box = document.getElementById("terminal-box");
        if (box) box.innerHTML = "";
    });
}

// Action Dispatchers
async function triggerMasterScan() {
    if (!activeClientId) return alert("Please select an active PC first.");
    appendTerminalLine(new Date().toLocaleTimeString(), "stdout", "[COMMAND] Requesting Master Diagnostic Scan...");
    try {
        await fetch(`/api/nodes/${activeClientId}/scan`, { method: "POST" });
    } catch (e) {
        alert("Failed to dispatch scan: " + e);
    }
}

async function triggerFixAll() {
    if (!activeClientId) return alert("Please select an active PC first.");
    if (!confirm("Execute ONE-CLICK Autonomous Master Remediation across all flagged issues?")) return;
    updateProgressBar(5, "Engaging One-Click Autonomous Remediation...");
    try {
        await fetch(`/api/nodes/${activeClientId}/fix-all`, { method: "POST" });
    } catch (e) {
        alert("Failed to dispatch Fix All: " + e);
    }
}

async function triggerFix(fixId) {
    if (!activeClientId) return alert("Please select an active PC first.");
    updateProgressBar(10, `Executing ${fixId}...`);
    try {
        await fetch(`/api/nodes/${activeClientId}/remediate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: fixId }),
        });
    } catch (e) {
        alert("Failed to dispatch fix: " + e);
    }
}

async function confirmSelfDestruct() {
    if (!activeClientId) return alert("Please select an active PC first.");
    const confirmed = confirm(
        "WARNING: SECURE ZERO-FOOTPRINT SELF-DESTRUCT\n\n" +
        "This will execute a DoD 3-pass file wipe of all temporary diagnostic logs, scripts, and agent files from the target PC, leaving ZERO trace.\n\n" +
        "Are you sure you want to proceed?"
    );
    if (!confirmed) return;

    try {
        await fetch(`/api/nodes/${activeClientId}/self-destruct`, { method: "POST" });
    } catch (e) {
        alert("Failed to dispatch self-destruct: " + e);
    }
}

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, m => map[m]);
}
