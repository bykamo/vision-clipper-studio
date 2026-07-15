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

    // Browse Button Logic
    const browseBtn = document.getElementById('browse-btn');
    if (browseBtn) {
        browseBtn.addEventListener('click', () => {
            const originalIcon = browseBtn.innerHTML;
            browseBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">refresh</span>';
            
            fetch('/browse')
                .then(res => res.json())
                .then(data => {
                    if (data.path) {
                        document.getElementById('source').value = data.path;
                    }
                    browseBtn.innerHTML = originalIcon;
                })
                .catch(err => {
                    console.error(err);
                    browseBtn.innerHTML = originalIcon;
                });
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
