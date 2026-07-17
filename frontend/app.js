document.addEventListener('DOMContentLoaded', () => {
    // ── Core Elements ──
    const tabs = document.querySelectorAll('.tab-btn');
    const form = document.getElementById('clipper-form');
    const generateBtn = document.getElementById('generate-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const btnText = generateBtn.querySelector('.btn-text');
    const btnIcon = generateBtn.querySelector('.btn-icon');
    const loader = generateBtn.querySelector('.loader');
    const consoleOutput = document.getElementById('console-output');
    const progressBar = document.getElementById('progress-bar');
    const progressLabel = document.getElementById('progress-label');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const outputGrid = document.getElementById('output-grid');
    
    let currentMode = 'hook';
    let eventSource = null;
    let outputDir = '';

    // ── File Explorer Modal Elements ──
    const explorerModal = document.getElementById('explorer-modal');
    const explorerClose = document.getElementById('explorer-close');
    const explorerCancel = document.getElementById('explorer-cancel');
    const explorerSelect = document.getElementById('explorer-select');
    const explorerPathInput = document.getElementById('explorer-path');
    const explorerGoBtn = document.getElementById('explorer-go-btn');
    const explorerUpBtn = document.getElementById('explorer-up-btn');
    const explorerDrives = document.getElementById('explorer-drives');
    const explorerList = document.getElementById('explorer-list');
    const explorerStatus = document.getElementById('explorer-status');
    const quickAccessBtns = document.querySelectorAll('.quick-access-btn');

    let currentExplorerPath = '';
    let selectedItemPath = '';
    let selectedItemType = '';

    // ── Status Helpers ──
    function setStatus(state) {
        if (statusDot) {
            statusDot.className = 'status-dot';
            if (state === 'processing') statusDot.classList.add('processing');
            if (state === 'error') statusDot.classList.add('error');
        }
        if (statusText) {
            const labels = { ready: 'READY', processing: 'PROCESSING', error: 'ERROR', complete: 'COMPLETE' };
            statusText.textContent = labels[state] || 'READY';
        }
    }

    function setProgress(percent) {
        const p = Math.min(100, Math.max(0, percent));
        if (progressBar) progressBar.style.width = `${p}%`;
        if (progressLabel) progressLabel.textContent = `${Math.round(p)}%`;
    }

    // ── File Explorer ──
    function loadDirectory(path = '') {
        explorerList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⏳</div>Loading files...</div>';
        
        fetch(`/api/list-dir?path=${encodeURIComponent(path)}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    explorerList.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div>Failed to read folder: ${data.error}</div>`;
                    return;
                }
                
                currentExplorerPath = data.current_path;
                explorerPathInput.value = currentExplorerPath;
                selectedItemPath = ''; 
                selectedItemType = '';

                if (data.parent_path) {
                    explorerUpBtn.disabled = false;
                    explorerUpBtn.style.opacity = '1';
                } else {
                    explorerUpBtn.disabled = true;
                    explorerUpBtn.style.opacity = '0.4';
                }

                // Render drives
                explorerDrives.innerHTML = '';
                if (data.drives && data.drives.length > 0) {
                    data.drives.forEach(drive => {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'drive-btn';
                        btn.textContent = drive;
                        btn.addEventListener('click', () => loadDirectory(drive));
                        explorerDrives.appendChild(btn);
                    });
                }

                // Render list
                explorerList.innerHTML = '';
                
                let foldersCount = data.folders ? data.folders.length : 0;
                let filesCount = data.files ? data.files.length : 0;
                explorerStatus.textContent = `${foldersCount} folder(s), ${filesCount} video(s) found`;

                if (foldersCount === 0 && filesCount === 0) {
                    explorerList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📂</div>No video files or subfolders found.</div>';
                    return;
                }

                // Folders
                if (data.folders) {
                    data.folders.forEach(folder => {
                        const item = document.createElement('div');
                        item.className = 'file-item';
                        item.innerHTML = `
                            <div class="file-item-info">
                                <span class="file-item-icon">📁</span>
                                <span class="file-item-name">${folder.name}</span>
                            </div>
                            <span class="file-item-meta">Folder</span>
                        `;
                        
                        item.addEventListener('click', (e) => {
                            e.stopPropagation();
                            selectExplorerItem(folder.path, 'folder', item);
                        });
                        
                        item.addEventListener('dblclick', (e) => {
                            e.stopPropagation();
                            loadDirectory(folder.path);
                        });
                        
                        explorerList.appendChild(item);
                    });
                }

                // Files
                if (data.files) {
                    data.files.forEach(file => {
                        const item = document.createElement('div');
                        item.className = 'file-item';
                        item.innerHTML = `
                            <div class="file-item-info">
                                <span class="file-item-icon">🎬</span>
                                <span class="file-item-name">${file.name}</span>
                            </div>
                            <span class="file-item-meta">${file.size}</span>
                        `;
                        
                        item.addEventListener('click', (e) => {
                            e.stopPropagation();
                            selectExplorerItem(file.path, 'file', item);
                        });

                        item.addEventListener('dblclick', (e) => {
                            e.stopPropagation();
                            confirmSelection(file.path);
                        });
                        
                        explorerList.appendChild(item);
                    });
                }
            })
            .catch(err => {
                console.error("Failed to load directory:", err);
                explorerList.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div>Network error: ${err.message}</div>`;
            });
    }

    function selectExplorerItem(path, type, element) {
        explorerList.querySelectorAll('.file-item.selected').forEach(item => {
            item.classList.remove('selected');
        });

        element.classList.add('selected');
        selectedItemPath = path;
        selectedItemType = type;
    }

    function confirmSelection(path = '') {
        const finalPath = path || selectedItemPath;
        if (!finalPath) {
            alert('Pilih file video terlebih dahulu!');
            return;
        }

        if (selectedItemType === 'folder' && !path) {
            loadDirectory(finalPath);
            return;
        }

        document.getElementById('source').value = finalPath;
        closeExplorerModal();
    }

    function closeExplorerModal() {
        if (explorerModal) {
            explorerModal.classList.remove('visible');
        }
    }

    function openExplorerModal() {
        if (explorerModal) {
            explorerModal.classList.add('visible');
            const currentVal = document.getElementById('source').value.trim();
            let startingDir = '';
            
            if (currentVal) {
                startingDir = currentVal;
                if (/\.[a-zA-Z0-9]+$/.test(currentVal)) {
                    const separator = currentVal.includes('/') ? '/' : '\\';
                    const parts = currentVal.split(separator);
                    parts.pop();
                    startingDir = parts.join(separator);
                }
            }
            
            loadDirectory(startingDir);
        }
    }

    // Modal triggers
    if (explorerClose) explorerClose.addEventListener('click', closeExplorerModal);
    if (explorerCancel) explorerCancel.addEventListener('click', closeExplorerModal);
    if (explorerSelect) {
        explorerSelect.addEventListener('click', () => confirmSelection());
    }

    if (explorerModal) {
        explorerModal.addEventListener('click', (e) => {
            if (e.target === explorerModal) closeExplorerModal();
        });
    }

    // Go Up
    if (explorerUpBtn) {
        explorerUpBtn.addEventListener('click', () => {
            fetch(`/api/list-dir?path=${encodeURIComponent(currentExplorerPath)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.parent_path) loadDirectory(data.parent_path);
                });
        });
    }

    // Path Manual Go
    if (explorerGoBtn && explorerPathInput) {
        explorerGoBtn.addEventListener('click', () => {
            loadDirectory(explorerPathInput.value.trim());
        });
        explorerPathInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadDirectory(explorerPathInput.value.trim());
            }
        });
    }

    // Quick Access
    quickAccessBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.dir;
            fetch(`/api/list-dir`)
                .then(res => res.json())
                .then(data => {
                    const home = data.current_path;
                    let target = home;
                    const sep = home.includes('/') ? '/' : '\\';
                    
                    if (type === 'desktop') target = `${home}${sep}Desktop`;
                    else if (type === 'downloads') target = `${home}${sep}Downloads`;
                    else if (type === 'documents') target = `${home}${sep}Documents`;
                    
                    loadDirectory(target);
                });
        });
    });

    // Browse Button
    const browseBtn = document.getElementById('browse-btn');
    if (browseBtn) {
        browseBtn.addEventListener('click', () => openExplorerModal());
    }

    // ── Tab Switching ──
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentMode = tab.dataset.mode;
        });
    });

    // ── Style Card Selection ──
    const styleCards = document.querySelectorAll('.style-card');
    styleCards.forEach(card => {
        card.addEventListener('click', () => {
            styleCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
        });
    });

    // ── Console Log ──
    function appendLog(message, type = 'normal', isReplace = false) {
        if (isReplace) {
            const lastChild = consoleOutput.lastElementChild;
            if (lastChild && lastChild.dataset.progress === 'true') {
                // Extract prefix, e.g., "Progress Download" or "Progress Transkripsi"
                const getPrefix = (msg) => {
                    const match = msg.match(/^\[?\d{2}:\d{2}:\d{2}\]?\s*(Progress\s+[A-Za-z0-9_]+)/) || msg.match(/^(Progress\s+[A-Za-z0-9_]+)/);
                    return match ? match[1] : null;
                };
                const lastPrefix = getPrefix(lastChild.textContent);
                const currentPrefix = getPrefix(message);
                if (lastPrefix && currentPrefix && lastPrefix === currentPrefix) {
                    lastChild.textContent = message;
                    
                    // Update progress bar from percentage in message
                    const progressMatch = message.match(/([\d.]+)%/);
                    if (progressMatch) {
                        setProgress(parseFloat(progressMatch[1]));
                    }
                    return;
                }
            }
        }

        const div = document.createElement('div');
        div.className = 'log-line';
        
        const typeClass = {
            'error': 'log-error',
            'success': 'log-success',
            'warning': 'log-warning',
            'highlight': 'log-highlight',
            'muted': 'log-muted',
            'info': 'log-info'
        };
        
        div.classList.add(typeClass[type] || 'log-normal');
        
        if (isReplace) div.dataset.progress = 'true';
        
        div.textContent = message;
        consoleOutput.appendChild(div);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;

        // Update progress bar from percentage in message
        const progressMatch = message.match(/([\d.]+)%/);
        if (progressMatch) {
            setProgress(parseFloat(progressMatch[1]));
        }
    }

    // ── Form Submit ──
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const sourceType = 'file'; 
        const source = document.getElementById('source').value.trim();
        const numClips = document.getElementById('num_clips').value;

        if (!source) {
            alert("Please enter a LOCAL VIDEO PATH!");
            return;
        }

        if (eventSource) eventSource.close();

        // Reset UI
        consoleOutput.innerHTML = '';
        setProgress(0);
        setStatus('processing');
        
        appendLog(`[SYSTEM] Initializing ${currentMode.toUpperCase()} CLIPPER ENGINE...`, 'highlight');
        appendLog(`[SYSTEM] Source: ${source}`, 'info');
        
        generateBtn.disabled = true;
        btnText.textContent = 'Processing...';
        if (btnIcon) btnIcon.classList.add('hidden');
        loader.classList.remove('hidden');
        cancelBtn.classList.remove('hidden');

        // Reset output grid
        if (outputGrid) {
            outputGrid.innerHTML = '<span class="output-empty">Memproses video... Klip sedang dibuat.</span>';
        }
        outputDir = '';

        const subStyle = document.querySelector('input[name="sub_style"]:checked')?.value || 'tiktok_viral';
        const whisperModel = document.getElementById('whisper_model')?.value || 'small';
        const streamUrl = `/stream?mode=${encodeURIComponent(currentMode)}&source_type=${encodeURIComponent(sourceType)}&source=${encodeURIComponent(source)}&num_clips=${encodeURIComponent(numClips)}&sub_style=${encodeURIComponent(subStyle)}&whisper_model=${encodeURIComponent(whisperModel)}`;
        eventSource = new EventSource(streamUrl);

        eventSource.onmessage = (event) => {
            const data = event.data;
            
            if (data === '[PROCESS_COMPLETE]') {
                appendLog('[SYSTEM] ✅ Sequence complete! Check output directory.', 'success');
                setProgress(100);
                setStatus('complete');
                finishProcess();
                
                // Show output folder link in grid
                if (outputGrid && outputDir) {
                    outputGrid.innerHTML = `
                        <div class="output-folder-card animate-in">
                            <div class="output-folder-icon">📂</div>
                            <div class="output-folder-info">
                                <span class="output-folder-title">Folder Output Siap</span>
                                <span class="output-folder-path">${outputDir}</span>
                            </div>
                            <button type="button" id="open-folder-btn" class="btn-open-folder">
                                Buka Folder
                            </button>
                        </div>
                    `;
                    const openFolderBtn = document.getElementById('open-folder-btn');
                    if (openFolderBtn) {
                        openFolderBtn.addEventListener('click', () => {
                            fetch('/api/open-folder', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ path: outputDir })
                            })
                            .then(res => res.json())
                            .then(resData => {
                                if (resData.error) {
                                    alert("Gagal membuka folder: " + resData.error);
                                }
                            })
                            .catch(err => {
                                alert("Error: " + err);
                            });
                        });
                    }
                } else if (outputGrid) {
                    outputGrid.innerHTML = '<span class="output-empty">Proses selesai! (Folder output tidak ditemukan)</span>';
                }
            } else if (data === '[PROCESS_FAILED]') {
                appendLog('[SYSTEM] ❌ Sequence failed. Check logs.', 'error');
                setStatus('error');
                finishProcess();
                if (outputGrid) {
                    outputGrid.innerHTML = '<span class="output-empty" style="color: var(--rose-500)">Gagal memproses video. Periksa log konsol.</span>';
                }
            } else {
                if (data === '[HEARTBEAT]') return;
                
                // Parse output directory from log message
                if (data.includes('Outputs will be saved to:')) {
                    const match = data.match(/Outputs will be saved to:\s*(.*)/);
                    if (match && match[1]) {
                        outputDir = match[1].trim();
                    }
                }
                
                const isProgress = data.includes('Progress') || data.includes('%|');
                let logType = 'normal';
                if (data.includes('WARNING') || data.includes('Warning')) {
                    logType = 'warning';
                }
                appendLog(data, logType, isProgress);
            }
        };

        eventSource.onerror = (error) => {
            console.error("SSE Error:", error);
            appendLog('[SYSTEM] ⚠️ Connection lost to engine.', 'error');
            setStatus('error');
            finishProcess();
        };
    });

    function finishProcess() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        generateBtn.disabled = false;
        btnText.textContent = 'Generate Clips';
        if (btnIcon) btnIcon.classList.remove('hidden');
        loader.classList.add('hidden');
        cancelBtn.classList.add('hidden');
        
        // Reset status to ready after a delay
        setTimeout(() => setStatus('ready'), 3000);
    }

    // ── Cancel ──
    cancelBtn.addEventListener('click', () => {
        if (!eventSource) return;
        
        appendLog('[SYSTEM] Transmitting abort signal...', 'highlight');
        cancelBtn.disabled = true;
        cancelBtn.querySelector('.btn-text').textContent = '⏳';
        
        fetch('/cancel', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'cancelled') {
                    appendLog('[SYSTEM] ⛔ Sequence forcefully terminated.', 'error');
                }
                finishProcess();
                cancelBtn.disabled = false;
                cancelBtn.querySelector('.btn-text').textContent = '■';
            })
            .catch(err => {
                appendLog('[SYSTEM] Failed to abort: ' + err, 'error');
                cancelBtn.disabled = false;
                cancelBtn.querySelector('.btn-text').textContent = '■';
            });
    });

    // ── Shutdown ──
    const shutdownBtn = document.getElementById('shutdown-server');
    if (shutdownBtn) {
        shutdownBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Shut down VisionClipper Studio server?')) {
                fetch('/shutdown', { method: 'POST' })
                    .then(() => {
                        document.body.innerHTML = `
                            <div style="height:100vh;width:100vw;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#0a0e1a;color:#f87171;font-family:Inter,sans-serif;font-size:1.25rem;gap:12px;">
                                <div style="font-size:3rem;">⚡</div>
                                <div style="font-weight:700;">SERVER OFFLINE</div>
                                <div style="font-size:0.8rem;color:#475569;">Close this tab or restart the server.</div>
                            </div>
                        `;
                    })
                    .catch(() => {
                        document.body.innerHTML = `
                            <div style="height:100vh;width:100vw;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#0a0e1a;color:#f87171;font-family:Inter,sans-serif;font-size:1.25rem;gap:12px;">
                                <div style="font-size:3rem;">⚡</div>
                                <div style="font-weight:700;">SERVER OFFLINE</div>
                                <div style="font-size:0.8rem;color:#475569;">Close this tab or restart the server.</div>
                            </div>
                        `;
                    });
            }
        });
    }
});
