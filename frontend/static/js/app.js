document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const newChatBtn = document.getElementById('new-chat-btn');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages-container');
    const welcomeScreen = document.getElementById('welcome-screen');
    const typingIndicator = document.getElementById('typing-indicator');
    const sourceModal = document.getElementById('source-modal');
    const closeModalBtns = document.querySelectorAll('.close-modal');
    const modalBodyContent = document.getElementById('modal-body-content');
    const modalScore = document.getElementById('modal-score');

    const openSidebarBtn = document.getElementById('open-sidebar');
    const closeSidebarBtn = document.getElementById('close-sidebar');
    const sidebar = document.getElementById('sidebar');
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');

    let conversationId = null;
    let isWaitingForResponse = false;
    let conversationHistory = JSON.parse(localStorage.getItem('conversations') || '[]');
    let uploadQueue = [];

    const API_BASE = window.location.origin.includes('3000') ? 'http://localhost:8000' : '';

    const initTheme = () => {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);
    };

    const toggleTheme = () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    };

    const updateThemeIcon = (theme) => {
        const icon = themeToggle.querySelector('i');
        icon.classList.remove(theme === 'light' ? 'fa-sun' : 'fa-moon');
        icon.classList.add(theme === 'light' ? 'fa-moon' : 'fa-sun');
    };

    themeToggle.addEventListener('click', toggleTheme);
    initTheme();

    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        sendBtn.disabled = this.value.trim() === '';
    });

    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled && !isWaitingForResponse) chatForm.dispatchEvent(new Event('submit'));
        }
    });

    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            userInput.value = btn.getAttribute('data-query');
            userInput.dispatchEvent(new Event('input'));
            chatForm.dispatchEvent(new Event('submit'));
        });
    });

    newChatBtn.addEventListener('click', () => {
        conversationId = null;
        messagesContainer.innerHTML = '';
        welcomeScreen.classList.remove('hidden');
        userInput.value = '';
        userInput.style.height = 'auto';
        userInput.focus();
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query || isWaitingForResponse) return;

        if (!welcomeScreen.classList.contains('hidden')) welcomeScreen.classList.add('hidden');

        appendMessage('user', query);
        userInput.value = '';
        userInput.style.height = 'auto';
        sendBtn.disabled = true;
        isWaitingForResponse = true;
        typingIndicator.classList.remove('hidden');
        scrollToBottom();

        try {
            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, conversation_id: conversationId, stream: false })
            });

            const data = await response.json();
            typingIndicator.classList.add('hidden');
            isWaitingForResponse = false;

            if (!response.ok) throw new Error(data.error || data.detail || 'An error occurred');

            if (!conversationId && data.conversation_id) {
                conversationId = data.conversation_id;
                saveConversation(conversationId, query, data.text);
            }

            appendMessage('ai', data.text, data.sources, data.trace_id);
        } catch (error) {
            typingIndicator.classList.add('hidden');
            isWaitingForResponse = false;
            appendMessage('error', error.message || 'Failed to connect to the server.');
        }
        userInput.focus();
    });

    function appendMessage(role, text, sources = null, traceId = null) {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${role === 'error' ? 'ai error' : role}`;
        const avatar = document.createElement('div');
        avatar.className = `avatar ${role === 'user' ? 'user-avatar' : 'ai-avatar'}`;
        avatar.innerHTML = role === 'user' ? '<i class="fa-solid fa-user"></i>' :
            role === 'error' ? '<i class="fa-solid fa-triangle-exclamation"></i>' : '<i class="fa-solid fa-brain"></i>';

        const content = document.createElement('div');
        content.className = 'message-content';
        const textElement = document.createElement('div');
        textElement.className = 'message-text';
        textElement.textContent = text;
        content.appendChild(textElement);

        if (sources && sources.length > 0) {
            const sourcesContainer = document.createElement('div');
            sourcesContainer.className = 'sources-container';
            const sourcesTitle = document.createElement('div');
            sourcesTitle.className = 'sources-title';
            sourcesTitle.innerHTML = '<i class="fa-solid fa-book-open"></i> Sources';
            sourcesContainer.appendChild(sourcesTitle);
            const sourcesList = document.createElement('div');
            sourcesList.className = 'sources-list';
            sources.forEach((source, index) => {
                const badge = document.createElement('button');
                badge.className = 'source-badge';
                badge.textContent = `[${index + 1}] ${source.id ? source.id.substring(0, 15) + '...' : 'Document'}`;
                badge.addEventListener('click', () => openSourceModal(source));
                sourcesList.appendChild(badge);
            });
            sourcesContainer.appendChild(sourcesList);
            content.appendChild(sourcesContainer);
        }

        if (role === 'ai' && traceId) {
            const feedbackActions = document.createElement('div');
            feedbackActions.className = 'feedback-actions';
            const upvoteBtn = document.createElement('button');
            upvoteBtn.className = 'feedback-btn upvote';
            upvoteBtn.innerHTML = '<i class="fa-regular fa-thumbs-up"></i>';
            const downvoteBtn = document.createElement('button');
            downvoteBtn.className = 'feedback-btn downvote';
            downvoteBtn.innerHTML = '<i class="fa-regular fa-thumbs-down"></i>';

            const submitFeedback = async (rating, btn) => {
                upvoteBtn.classList.remove('active');
                upvoteBtn.innerHTML = '<i class="fa-regular fa-thumbs-up"></i>';
                downvoteBtn.classList.remove('active');
                downvoteBtn.innerHTML = '<i class="fa-regular fa-thumbs-down"></i>';
                btn.classList.add('active');
                btn.innerHTML = btn.classList.contains('upvote') ? '<i class="fa-solid fa-thumbs-up"></i>' : '<i class="fa-solid fa-thumbs-down"></i>';
                try {
                    await fetch(`${API_BASE}/api/feedback`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ trace_id: traceId, rating })
                    });
                } catch (e) { console.error("Feedback failed", e); }
            };

            upvoteBtn.addEventListener('click', () => submitFeedback(5, upvoteBtn));
            downvoteBtn.addEventListener('click', () => submitFeedback(1, downvoteBtn));
            feedbackActions.appendChild(upvoteBtn);
            feedbackActions.appendChild(downvoteBtn);
            content.appendChild(feedbackActions);
        }

        wrapper.appendChild(avatar);
        wrapper.appendChild(content);
        messagesContainer.appendChild(wrapper);
        scrollToBottom();
    }

    function scrollToBottom() {
        const chatWindow = document.getElementById('chat-window');
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function openSourceModal(source) {
        modalBodyContent.textContent = source.content;
        modalScore.innerHTML = `<strong>Relevance Score:</strong> ${(source.score * 100).toFixed(1)}%`;
        sourceModal.classList.remove('hidden');
    }

    function closeModal() { sourceModal.classList.add('hidden'); }
    closeModalBtns.forEach(btn => btn.addEventListener('click', closeModal));
    sourceModal.addEventListener('click', (e) => { if (e.target === sourceModal) closeModal(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !sourceModal.classList.contains('hidden')) closeModal(); });

    // Sidebar Navigation
    openSidebarBtn.addEventListener('click', () => {
        sidebar.classList.add('open');
    });
    closeSidebarBtn.addEventListener('click', () => {
        sidebar.classList.remove('open');
    });

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewName = item.getAttribute('data-view');
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            views.forEach(v => v.classList.remove('active'));
            document.getElementById(`${viewName}-view`).classList.add('active');
            sidebar.classList.remove('open');

            if (viewName === 'history') loadHistory();
            if (viewName === 'metrics') loadMetrics();
        });
    });

    // Conversation History
    function saveConversation(id, firstMessage, response) {
        const conv = {
            id,
            firstMessage: firstMessage.substring(0, 100),
            response: response.substring(0, 100),
            date: new Date().toISOString(),
        };
        conversationHistory.unshift(conv);
        if (conversationHistory.length > 50) conversationHistory.pop();
        localStorage.setItem('conversations', JSON.stringify(conversationHistory));
    }

    async function loadHistory() {
        const list = document.getElementById('history-list');
        if (conversationHistory.length === 0) {
            list.innerHTML = '<p class="empty-state">No conversations yet.</p>';
            return;
        }

        list.innerHTML = conversationHistory.map(conv => `
            <div class="history-item" data-id="${conv.id}">
                <div class="history-item-header">
                    <span class="history-item-id">${conv.id}</span>
                    <span class="history-item-date">${new Date(conv.date).toLocaleDateString()}</span>
                </div>
                <div class="history-item-preview">${conv.firstMessage}</div>
            </div>
        `).join('');

        list.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', async () => {
                const id = item.getAttribute('data-id');
                try {
                    const res = await fetch(`${API_BASE}/api/conversations/${id}`);
                    if (res.ok) {
                        const data = await res.json();
                        showConversationModal(data);
                    }
                } catch (e) { console.error("Failed to load conversation", e); }
            });
        });
    }

    function showConversationModal(data) {
        const body = document.getElementById('conversation-modal-body');
        body.innerHTML = data.messages.map(m => `
            <div style="margin-bottom: 1rem; padding: 0.75rem; border-radius: 0.5rem; background: ${m.role === 'user' ? 'var(--user-msg-bg)' : 'var(--ai-msg-bg)'}; color: ${m.role === 'user' ? 'var(--user-msg-text)' : 'var(--text-color)'}">
                <strong>${m.role}:</strong> ${m.content.substring(0, 200)}${m.content.length > 200 ? '...' : ''}
            </div>
        `).join('');
        document.getElementById('conversation-modal').classList.remove('hidden');
    }

    document.querySelectorAll('#conversation-modal .close-modal').forEach(btn => {
        btn.addEventListener('click', () => document.getElementById('conversation-modal').classList.add('hidden'));
    });

    // Document Upload
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const manualContent = document.getElementById('manual-content');
    const manualId = document.getElementById('manual-id');
    const manualSource = document.getElementById('manual-source');
    const addManualBtn = document.getElementById('add-manual-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadQueueEl = document.getElementById('upload-queue');
    const uploadStatus = document.getElementById('upload-status');

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));

    async function handleFiles(files) {
        for (const file of files) {
            const text = await file.text();
            addToQueue({ id: `file_${file.name}`, content: text, source: file.name });
        }
    }

    function addToQueue(doc) {
        uploadQueue.push(doc);
        renderQueue();
    }

    function renderQueue() {
        uploadQueueEl.innerHTML = uploadQueue.map((doc, i) => `
            <div class="queue-item">
                <span>${doc.id} (${doc.content.length} chars)</span>
                <button class="remove-btn" data-index="${i}"><i class="fa-solid fa-trash"></i></button>
            </div>
        `).join('');
        uploadBtn.disabled = uploadQueue.length === 0;

        uploadQueueEl.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                uploadQueue.splice(parseInt(btn.getAttribute('data-index')), 1);
                renderQueue();
            });
        });
    }

    addManualBtn.addEventListener('click', () => {
        const content = manualContent.value.trim();
        if (!content) return;
        addToQueue({
            id: manualId.value.trim() || `manual_${Date.now()}`,
            content,
            source: manualSource.value.trim() || 'manual',
        });
        manualContent.value = '';
        manualId.value = '';
        manualSource.value = '';
    });

    uploadBtn.addEventListener('click', async () => {
        uploadStatus.textContent = 'Uploading...';
        uploadStatus.className = 'upload-status';
        try {
            const res = await fetch(`${API_BASE}/api/documents`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ documents: uploadQueue, metadata: {} })
            });
            const data = await res.json();
            if (res.ok) {
                uploadStatus.textContent = `Successfully uploaded ${data.uploaded} documents!`;
                uploadStatus.className = 'upload-status success';
                uploadQueue = [];
                renderQueue();
            } else {
                uploadStatus.textContent = data.error || 'Upload failed';
                uploadStatus.className = 'upload-status error';
            }
        } catch (e) {
            uploadStatus.textContent = 'Upload failed: ' + e.message;
            uploadStatus.className = 'upload-status error';
        }
    });

    // Metrics Dashboard
    async function loadMetrics() {
        try {
            const [costRes, feedbackRes, docsRes, monitorRes] = await Promise.all([
                fetch(`${API_BASE}/api/metrics/cost`),
                fetch(`${API_BASE}/api/metrics/feedback`),
                fetch(`${API_BASE}/api/documents/stats`),
                fetch(`${API_BASE}/api/metrics/monitoring`),
            ]);

            const cost = await costRes.json();
            const feedback = await feedbackRes.json();
            const docs = await docsRes.json();
            const monitor = await monitorRes.json();

            document.getElementById('metric-cost').textContent = `$${cost.budget.daily_cost.toFixed(4)}`;
            document.getElementById('metric-budget').textContent = `Budget: $${cost.budget.budget_limit.toFixed(2)} (${cost.budget.utilization_pct.toFixed(1)}% used)`;
            document.getElementById('metric-rating').textContent = feedback.avg_rating > 0 ? feedback.avg_rating.toFixed(1) : '-';
            document.getElementById('metric-feedback-count').textContent = `${feedback.total || 0} feedbacks`;
            document.getElementById('metric-docs').textContent = docs.count || 0;
            document.getElementById('metric-cache').textContent = monitor.metrics.cache_hit_rate > 0 ? `${(monitor.metrics.cache_hit_rate * 100).toFixed(1)}%` : '-';

            const modelList = document.getElementById('model-list');
            if (Object.keys(cost.breakdown).length > 0) {
                modelList.innerHTML = Object.entries(cost.breakdown).map(([model, stats]) => `
                    <div class="model-item">
                        <span class="model-name">${model}</span>
                        <span class="model-stats">${stats.queries} queries, $${stats.cost.toFixed(4)}</span>
                    </div>
                `).join('');
            } else {
                modelList.innerHTML = '<p class="empty-state">No model usage data yet.</p>';
            }
        } catch (e) {
            console.error("Failed to load metrics", e);
        }
    }

    document.getElementById('refresh-metrics').addEventListener('click', loadMetrics);
});
