(function() {
    let network = null;
    let nodes = new vis.DataSet([]);
    let edges = new vis.DataSet([]);
    let selectedNodes = [];
    let selectedEdges = [];

    // Base path for API calls (set from template, e.g., "/dev" or "")
    const apiBasePath = typeof basePath !== 'undefined' ? basePath : '';
    
    // Helper for API calls
    function api(path) {
        return apiBasePath + path;
    }

    // Kasten URL from template
    const kastenUrl = window.KASTEN_URL || 'https://kasten.gstoehl.dev';

    // Expose for debugging
    window.workspaceNetwork = () => network;
    window.workspaceNodes = () => nodes;

    // Load workspace data (positions from Canvas, content from Kasten)
    async function loadWorkspace() {
        const response = await fetch(api('/api/workspace'));
        const data = await response.json();

        nodes.clear();
        edges.clear();

        // Fetch content for each note from Kasten
        for (const note of data.notes) {
            try {
                const kastenResp = await fetch(`${kastenUrl}/api/notes/${note.km_note_id}`);
                if (kastenResp.ok) {
                    const kastenNote = await kastenResp.json();
                    const content = `${kastenNote.title}\n\n${kastenNote.content}`;
                    nodes.add({
                        id: note.id,
                        km_note_id: note.km_note_id,
                        label: content.substring(0, 100) + (content.length > 100 ? '...' : ''),
                        title: content,
                        x: note.x,
                        y: note.y,
                        shape: 'box',
                        font: { face: 'monospace', size: 12, align: 'left' },
                        margin: 10,
                        widthConstraint: { minimum: 150, maximum: 300 }
                    });
                }
            } catch (e) {
                console.error(`Failed to fetch note ${note.km_note_id}:`, e);
            }
        }

        data.connections.forEach(conn => {
            edges.add({
                id: conn.id,
                from: conn.from_note_id,
                to: conn.to_note_id,
                label: conn.label,
                arrows: 'to',
                font: { face: 'monospace', size: 11 }
            });
        });
    }

    // Initialize network
    function initNetwork() {
        const container = document.getElementById('graph');
        const options = {
            physics: false,
            interaction: {
                multiselect: true,
                selectConnectedEdges: false
            },
            nodes: {
                color: {
                    background: '#fff',
                    border: '#000',
                    highlight: { background: '#f5f5f5', border: '#000' }
                },
                borderWidth: 2
            },
            edges: {
                color: '#000',
                width: 1,
                smooth: { type: 'cubicBezier' }
            }
        };

        network = new vis.Network(container, { nodes, edges }, options);

        network.on('select', function(params) {
            selectedNodes = params.nodes;
            selectedEdges = params.edges;
            updateSelectionUI();
        });

        network.on('deselectNode', function() {
            selectedNodes = network.getSelectedNodes();
            selectedEdges = network.getSelectedEdges();
            updateSelectionUI();
        });

        network.on('deselectEdge', function() {
            selectedNodes = network.getSelectedNodes();
            selectedEdges = network.getSelectedEdges();
            updateSelectionUI();
        });
    }

    function updateSelectionUI() {
        const connectBtn = document.getElementById('connect-btn');
        const deleteBtn = document.getElementById('delete-btn');
        const info = document.getElementById('selection-info');

        // Handle delete button - enabled for notes OR edges
        if (selectedEdges.length > 0 || selectedNodes.length > 0) {
            deleteBtn.disabled = false;
        } else {
            deleteBtn.disabled = true;
        }

        // Build info text
        if (selectedNodes.length === 2 && selectedEdges.length === 0) {
            connectBtn.disabled = false;
            info.textContent = '2 notes selected - ready to connect';
        } else if (selectedNodes.length === 1 && selectedEdges.length === 0) {
            connectBtn.disabled = true;
            info.textContent = '1 note selected - select another to connect';
        } else if (selectedEdges.length > 0 && selectedNodes.length > 0) {
            connectBtn.disabled = true;
            info.textContent = `${selectedNodes.length} note${selectedNodes.length > 1 ? 's' : ''}, ${selectedEdges.length} connection${selectedEdges.length > 1 ? 's' : ''} selected`;
        } else if (selectedEdges.length > 0) {
            connectBtn.disabled = true;
            info.textContent = `${selectedEdges.length} connection${selectedEdges.length > 1 ? 's' : ''} selected`;
        } else if (selectedNodes.length > 0) {
            connectBtn.disabled = true;
            info.textContent = `${selectedNodes.length} note${selectedNodes.length > 1 ? 's' : ''} selected`;
        } else {
            connectBtn.disabled = true;
            info.textContent = '';
        }
    }

    // Connection modal
    window.openConnectionModal = function() {
        document.getElementById('connection-modal').classList.add('active');
        document.getElementById('connection-label').focus();
    };

    window.closeModal = function() {
        document.getElementById('connection-modal').classList.remove('active');
        document.getElementById('connection-label').value = '';
    };

    window.createConnection = async function() {
        const label = document.getElementById('connection-label').value || 'relates to';

        const response = await fetch(api('/api/workspace/connections'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                from_note_id: selectedNodes[0],
                to_note_id: selectedNodes[1],
                label: label
            })
        });

        if (response.ok) {
            const conn = await response.json();
            edges.add({
                id: conn.id,
                from: conn.from_note_id,
                to: conn.to_note_id,
                label: conn.label,
                arrows: 'to',
                font: { face: 'monospace', size: 11 }
            });
        }

        closeModal();
        network.unselectAll();
    };

    // Delete selected notes and/or connections
    window.deleteSelected = async function() {
        // Delete notes first (API cascades to remove their connections)
        for (const nodeId of selectedNodes) {
            const response = await fetch(api(`/api/workspace/notes/${nodeId}`), {
                method: 'DELETE'
            });

            if (response.ok) {
                // Remove edges connected to this node from vis.js
                const connectedEdges = edges.get().filter(
                    e => e.from === nodeId || e.to === nodeId
                );
                connectedEdges.forEach(e => edges.remove(e.id));
                nodes.remove(nodeId);
            }
        }

        // Delete remaining selected edges
        for (const edgeId of selectedEdges) {
            const response = await fetch(api(`/api/workspace/connections/${edgeId}`), {
                method: 'DELETE'
            });

            if (response.ok) {
                edges.remove(edgeId);
            }
        }

        selectedNodes = [];
        selectedEdges = [];
        network.unselectAll();
        updateSelectionUI();
    };

    // Export
    async function exportWorkspace() {
        const response = await fetch(api('/api/workspace'));
        const data = await response.json();

        // Fetch all note content from Kasten
        const noteContents = {};
        for (const note of data.notes) {
            try {
                const resp = await fetch(`${kastenUrl}/api/notes/${note.km_note_id}`);
                if (resp.ok) {
                    const kastenNote = await resp.json();
                    noteContents[note.id] = `${kastenNote.title}\n\n${kastenNote.content}`;
                }
            } catch (e) {
                noteContents[note.id] = `[Note ${note.km_note_id} not found]`;
            }
        }

        // Simple export: list notes with their connections
        let output = '';
        data.notes.forEach(note => {
            output += (noteContents[note.id] || '') + '\n\n';

            const outgoing = data.connections.filter(c => c.from_note_id === note.id);
            outgoing.forEach(conn => {
                output += `**${conn.label.charAt(0).toUpperCase() + conn.label.slice(1)}:**\n\n`;
            });
        });

        // Download as file
        const blob = new Blob([output], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'workspace-export.md';
        a.click();
    }

    // Zoom controls
    document.getElementById('zoom-in').addEventListener('click', () => {
        network.moveTo({ scale: network.getScale() * 1.2 });
    });
    document.getElementById('zoom-out').addEventListener('click', () => {
        network.moveTo({ scale: network.getScale() / 1.2 });
    });
    document.getElementById('zoom-fit').addEventListener('click', () => {
        network.fit();
    });

    // Button handlers
    document.getElementById('connect-btn').addEventListener('click', openConnectionModal);
    document.getElementById('delete-btn').addEventListener('click', deleteSelected);
    document.getElementById('export-btn').addEventListener('click', exportWorkspace);

    // Init
    loadWorkspace().then(() => {
        initNetwork();
        // Fit after a short delay to ensure render
        setTimeout(() => {
            if (network) {
                network.fit();
            }
        }, 100);
    });
})();
