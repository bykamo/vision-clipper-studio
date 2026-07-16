document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab');
    const form = document.getElementById('clipper-form');
    const generateBtn = document.getElementById('generate-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const btnText = generateBtn.querySelector('.btn-text');
    const loader = generateBtn.querySelector('.loader');
    const consoleOutput = document.getElementById('console-output');
    const progressBar = document.getElementById('progress-bar');
    const workerStatus = document.getElementById('worker-status');
    
    let currentMode = 'hook';
    let eventSource = null;

    // Local File Explorer Modal State & Elements
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
    let selectedItemType = ''; // 'file' or 'folder'

    function loadDirectory(path = '') {
        explorerList.innerHTML = '<div class="text-slate-400 py-12 text-center select-none"><span class="material-symbols-outlined animate-spin text-3xl mb-2">refresh</span><br/>Loading files...</div>';
        
        fetch(`/api/list-dir?path=${encodeURIComponent(path)}`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    explorerList.innerHTML = `<div class="text-red-400 py-12 text-center select-none"><span class="material-symbols-outlined text-3xl mb-2">error</span><br/>Failed to read folder: ${data.error}</div>`;
                    return;
                }
                
                currentExplorerPath = data.current_path;
                explorerPathInput.value = currentExplorerPath;
                selectedItemPath = ''; 
                selectedItemType = '';

                // Enable/disable up button
                if (data.parent_path) {
                    explorerUpBtn.disabled = false;
                    explorerUpBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                } else {
                    explorerUpBtn.disabled = true;
                    explorerUpBtn.classList.add('opacity-50', 'cursor-not-allowed');
                }

                // Render drives
                explorerDrives.innerHTML = '';
                if (data.drives && data.drives.length > 0) {
                    data.drives.forEach(drive => {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'px-2 py-1 rounded bg-purple-500/20 hover:bg-purple-500/40 text-purple-200 border border-purple-500/30 transition-all font-semibold';
                        btn.textContent = drive;
                        btn.addEventListener('click', () => loadDirectory(drive));
                        explorerDrives.appendChild(btn);
                    });
                }

                // Render folders and files
                explorerList.innerHTML = '';
                
                let foldersCount = data.folders ? data.folders.length : 0;
                let filesCount = data.files ? data.files.length : 0;
                explorerStatus.textContent = `${foldersCount} folder(s), ${filesCount} video(s) found`;

                if (foldersCount === 0 && filesCount === 0) {
                    explorerList.innerHTML = '<div class="text-slate-500 py-12 text-center select-none">No video files or subfolders found.</div>';
                    return;
                }

                // List folders
                if (data.folders) {
                    data.folders.forEach(folder => {
                        const item = document.createElement('div');
                        item.className = 'flex items-center justify-between p-3.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 cursor-pointer transition-all select-none group';
                        item.innerHTML = `
                            <div class="flex items-center gap-3 min-w-0">
                                <span class="text-xl flex-shrink-0">📁</span>
                                <span class="text-slate-200 font-medium truncate text-sm">${folder.name}</span>
                            </div>
                            <span class="text-xs text-slate-500 group-hover:text-slate-400 transition-colors">Folder</span>
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

                // List files
                if (data.files) {
                    data.files.forEach(file => {
                        const item = document.createElement('div');
                        item.className = 'flex items-center justify-between p-3.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 cursor-pointer transition-all select-none group';
                        item.innerHTML = `
                            <div class="flex items-center gap-3 min-w-0">
                                <span class="text-xl flex-shrink-0">🎬</span>
                                <span class="text-slate-200 font-medium truncate text-sm">${file.name}</span>
                            </div>
                            <span class="text-xs text-slate-400 font-mono flex-shrink-0">${file.size}</span>
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
                explorerList.innerHTML = `<div class="text-red-400 py-12 text-center select-none"><span class="material-symbols-outlined text-3xl mb-2">error</span><br/>Network error: ${err.message}</div>`;
            });
    }

    function selectExplorerItem(path, type, element) {
        const activeItems = explorerList.querySelectorAll('.bg-purple-500\\/20');
        activeItems.forEach(item => {
            item.classList.remove('bg-purple-500/20', 'border-purple-500/40');
            item.classList.add('bg-white/5', 'border-white/5');
        });

        element.classList.remove('bg-white/5', 'border-white/5');
        element.classList.add('bg-purple-500/20', 'border-purple-500/40');

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
            explorerModal.classList.add('hidden');
        }
    }

    function openExplorerModal() {
        if (explorerModal) {
            explorerModal.classList.remove('hidden');
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

    // Modal Close Trigger
    if (explorerClose) explorerClose.addEventListener('click', closeExplorerModal);
    if (explorerCancel) explorerCancel.addEventListener('click', closeExplorerModal);
    if (explorerSelect) {
        explorerSelect.addEventListener('click', () => {
            confirmSelection();
        });
    }

    if (explorerModal) {
        explorerModal.addEventListener('click', (e) => {
            if (e.target === explorerModal) {
                closeExplorerModal();
            }
        });
    }

    // Go Up Trigger
    if (explorerUpBtn) {
        explorerUpBtn.addEventListener('click', () => {
            fetch(`/api/list-dir?path=${encodeURIComponent(currentExplorerPath)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.parent_path) {
                        loadDirectory(data.parent_path);
                    }
                });
        });
    }

    // Path Manual Go Trigger
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

    // Quick Access Navigation
    quickAccessBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.dir;
            fetch(`/api/list-dir`)
                .then(res => res.json())
                .then(data => {
                    const home = data.current_path;
                    let target = home;
                    const sep = home.includes('/') ? '/' : '\\';
                    
                    if (type === 'desktop') {
                        target = `${home}${sep}Desktop`;
                    } else if (type === 'downloads') {
                        target = `${home}${sep}Downloads`;
                    } else if (type === 'documents') {
                        target = `${home}${sep}Documents`;
                    }
                    
                    loadDirectory(target);
                });
        });
    });

    // Browse Button Trigger
    const browseBtn = document.getElementById('browse-btn');
    if (browseBtn) {
        browseBtn.addEventListener('click', () => {
            openExplorerModal();
        });
    }

    // Tab Switching Logic
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => {
                t.classList.remove('active', 'font-semibold', 'bg-white/20', 'text-white', 'shadow-[0_2px_10px_rgba(0,0,0,0.2)]', 'border-white/20', 'backdrop-blur-lg');
                t.classList.add('font-medium', 'text-slate-300', 'hover:text-white', 'hover:bg-white/5', 'border-transparent');
                const icon = t.querySelector('.material-symbols-outlined');
                if(icon) icon.style.fontVariationSettings = "'FILL' 0";
            });
            
            tab.classList.remove('font-medium', 'text-slate-300', 'hover:text-white', 'hover:bg-white/5', 'border-transparent');
            tab.classList.add('active', 'font-semibold', 'bg-white/20', 'text-white', 'shadow-[0_2px_10px_rgba(0,0,0,0.2)]', 'border-white/20', 'backdrop-blur-lg');
            const icon = tab.querySelector('.material-symbols-outlined');
            if(icon) icon.style.fontVariationSettings = "'FILL' 1";
            
            currentMode = tab.dataset.mode;
        });
    });

    function appendLog(message, type = 'normal', isReplace = false) {
        if (isReplace) {
            const lastChild = consoleOutput.lastElementChild;
            if (lastChild && lastChild.dataset.progress === 'true') {
                lastChild.textContent = message;
                return;
            }
        }

        const div = document.createElement('div');
        div.className = `log-line`;
        if (type === 'error') div.classList.add('text-error');
        else if (type === 'success') div.classList.add('text-success');
        else if (type === 'warning') div.classList.add('text-warning');
        else if (type === 'highlight') div.classList.add('text-highlight');
        else if (type === 'muted') div.classList.add('text-muted');
        else div.classList.add('text-primary'); // Default normal log color
        
        if (isReplace) {
            div.dataset.progress = 'true';
        }
        
        div.textContent = message;
        consoleOutput.appendChild(div);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;

        // Try to update progress bar if we see percentage
        const progressMatch = message.match(/([\d.]+)%/);
        if(progressMatch && progressBar) {
            progressBar.style.width = `${progressMatch[1]}%`;
        }
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Force source_type to 'file' for now as url is disabled
        const sourceType = 'file'; 
        const source = document.getElementById('source').value.trim();
        const numClips = document.getElementById('num_clips').value;

        if (!source) {
            alert("Please enter a LOCAL VIDEO PATH!");
            return;
        }

        if (eventSource) {
            eventSource.close();
        }

        // Update UI State
        consoleOutput.innerHTML = '';
        if(progressBar) progressBar.style.width = '0%';
        if(workerStatus) workerStatus.textContent = 'WORKER_NODE_ACTIVE';
        
        appendLog(`[SYSTEM] Initializing ${currentMode.toUpperCase()} CLIPPER ENGINE...`, 'highlight');
        appendLog(`[SYSTEM] Source: ${source}`);
        generateBtn.disabled = true;
        
        // Hide standard btn text and icon, show loader
        btnText.textContent = 'Sedang memproses...';
        loader.classList.remove('hidden');
        cancelBtn.classList.remove('hidden');

        const streamUrl = `/stream?mode=${encodeURIComponent(currentMode)}&source_type=${encodeURIComponent(sourceType)}&source=${encodeURIComponent(source)}&num_clips=${encodeURIComponent(numClips)}`;
        eventSource = new EventSource(streamUrl);

        eventSource.onmessage = (event) => {
            const data = event.data;
            
            if (data === '[PROCESS_COMPLETE]') {
                appendLog('[SYSTEM] Sequence complete! Check output directory.', 'success');
                if(progressBar) progressBar.style.width = '100%';
                finishProcess();
            } else if (data === '[PROCESS_FAILED]') {
                appendLog('[SYSTEM] Sequence failed. Check logs.', 'error');
                finishProcess();
            } else {
                if (data === '[HEARTBEAT]') return;
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
            appendLog('[SYSTEM] Connection lost to V-Engine.', 'error');
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
        loader.classList.add('hidden');
        cancelBtn.classList.add('hidden');
        if(workerStatus) workerStatus.textContent = 'WORKER_NODE_IDLE';
    }

    cancelBtn.addEventListener('click', () => {
        if (!eventSource) return;
        
        appendLog('[SYSTEM] Transmitting abort signal...', 'highlight');
        cancelBtn.disabled = true;
        cancelBtn.querySelector('.btn-text').textContent = 'ABORTING...';
        
        fetch('/cancel', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if(data.status === 'cancelled') {
                    appendLog('[SYSTEM] Sequence forcefully terminated.', 'error');
                }
                finishProcess();
                cancelBtn.disabled = false;
                cancelBtn.querySelector('.btn-text').textContent = 'ABORT SEQUENCE';
            })
            .catch(err => {
                appendLog('[SYSTEM] Failed to abort: ' + err, 'error');
                cancelBtn.disabled = false;
                cancelBtn.querySelector('.btn-text').textContent = 'ABORT SEQUENCE';
            });
    });

    const shutdownBtn = document.getElementById('shutdown-server');
    if(shutdownBtn) {
        shutdownBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if(confirm('Initiate complete server shutdown?')) {
                fetch('/shutdown', {method: 'POST'})
                .then(() => {
                    document.body.innerHTML = '<div class="h-screen w-screen flex flex-col items-center justify-center bg-black text-error font-label-md text-xl"><span class="material-symbols-outlined text-6xl mb-4">power_off</span>V-ENGINE OFFLINE</div>';
                }).catch(() => {
                    document.body.innerHTML = '<div class="h-screen w-screen flex flex-col items-center justify-center bg-black text-error font-label-md text-xl"><span class="material-symbols-outlined text-6xl mb-4">power_off</span>V-ENGINE OFFLINE</div>';
                });
            }
        });
    }
});
