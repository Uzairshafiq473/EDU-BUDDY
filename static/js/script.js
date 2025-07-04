document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatContainer = document.getElementById('chat-container');
    const suggestionsContainer = document.getElementById('suggestions-container');
    const quizBtn = document.getElementById('quiz-btn');
    const progressBtn = document.getElementById('progress-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const quizModal = document.getElementById('quiz-modal');
    const progressModal = document.getElementById('progress-modal');
    const closeModals = document.querySelectorAll('.close-modal');
    const micBtn = document.getElementById('mic-btn');
    const attachBtn = document.getElementById('attach-btn');
    const fileInput = document.getElementById('file-input');

    // Avatar path from Flask (set dynamically in chat.html)
    const botAvatar = document.getElementById('bot-avatar-path')?.dataset.avatar || '/static/images/avatar.jpeg';
    const userAvatar = '/static/images/user-avatar.jpeg';

    // Initialize the chat
    initChat();

    // Event Listeners
    if (attachBtn && fileInput) {
        attachBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileUpload);
    }

    if (chatForm) chatForm.addEventListener('submit', handleFormSubmit);
    if (quizBtn) quizBtn.addEventListener('click', showQuizModal);
    if (progressBtn) progressBtn.addEventListener('click', showProgressModal);
    if (newChatBtn) newChatBtn.addEventListener('click', startNewChat);

    closeModals.forEach(btn => {
        if (btn) btn.addEventListener('click', closeAllModals);
    });

    if (micBtn) micBtn.addEventListener('click', startVoiceRecognition);

    // Handle clicks outside modal to close
    window.addEventListener('click', function (event) {
        if (event.target === quizModal) {
            quizModal.style.display = 'none';
        }
        if (event.target === progressModal) {
            progressModal.style.display = 'none';
        }
    });

    function startVoiceRecognition() {
        if (!('webkitSpeechRecognition' in window)) {
            alert('Voice recognition not supported. Use Chrome or Edge.');
            return;
        }

        const recognition = new webkitSpeechRecognition();
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        const lastMessage = chatContainer.lastElementChild?.querySelector('.message-text')?.textContent || '';
        const isUrdu = /[\u0600-\u06FF]/.test(lastMessage);
        recognition.lang = isUrdu ? 'ur-PK' : 'en-US';

        recognition.onresult = (event) => {
            let transcript = event.results[0][0].transcript;
            if (isUrdu) {
                transcript = transliterateUrduToRoman(transcript);
            }
            if (userInput) userInput.value = transcript;
        };

        recognition.onerror = (event) => {
            console.error('Voice error:', event.error);
            if (event.error === 'not-allowed') {
                alert('Microphone access blocked. Allow permissions in browser settings.');
            }
        };

        recognition.start();
    }

    function transliterateUrduToRoman(urduText) {
        const mappings = {
            'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ٹ': 'tt', 'ث': 's',
            'ج': 'j', 'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ڈ': 'dd',
            'ذ': 'z', 'ر': 'r', 'ڑ': 'rr', 'ز': 'z', 'ژ': 'zh', 'س': 's',
            'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a',
            'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ک': 'k', 'گ': 'g', 'ل': 'l',
            'م': 'm', 'ن': 'n', 'و': 'w', 'ہ': 'h', 'ھ': 'h', 'ء': "'",
            'ی': 'y', 'ے': 'e', 'ں': 'n'
        };
        return urduText.split('').map(char => mappings[char] || char).join('');
    }

    function initChat() {
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        if (userInput) userInput.focus();
    }

    async function handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const loadingId = showLoadingIndicator();
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Upload failed');

            const result = await response.json();
            addMessageToChat(`I've received your file: ${file.name}`, 'bot');
        } catch (error) {
            console.error('File upload error:', error);
            addMessageToChat("Sorry, I couldn't process your file.", 'bot');
        } finally {
            removeLoadingIndicator(loadingId);
            if (fileInput) fileInput.value = '';
        }
    }

    async function handleFormSubmit(e) {
        e.preventDefault();
        if (!userInput) return;

        const message = userInput.value.trim();
        if (!message) return;

        addMessageToChat(message, 'user');
        userInput.value = '';

        const loadingId = showLoadingIndicator();
        try {
            const response = await fetch('/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `user_input=${encodeURIComponent(message)}`
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            removeLoadingIndicator(loadingId);

            if (data.response) {
                addMessageToChat(data.response, 'bot');
                if (data.suggestions && data.suggestions.length > 0 && suggestionsContainer) {
                    showSuggestions(data.suggestions);
                }
            }
        } catch (error) {
            console.error('Error:', error);
            removeLoadingIndicator(loadingId);
            addMessageToChat("Sorry, I encountered an error. Please try again.", 'bot');
        }
    }

    // Helper function: Typing effect for bot messages
    function typeWriterEffect(text, element, speed = 18) {
        let i = 0;
        function typing() {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                setTimeout(typing, speed);
            }
        }
        typing();
    }

    // Update: addMessageToChat to use typing effect for bot
    function addMessageToChat(message, sender) {
        if (!chatContainer) return;

        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatarSrc = sender === 'bot' ? botAvatar : userAvatar;
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <img src="${avatarSrc}" alt="${sender}" onerror="this.onerror=null; this.src='/static/images/fallback-avatar.png';">
            </div>
            <div class="message-content">
                <div class="message-sender">${sender === 'bot' ? 'EDU BUDDY' : 'You'}</div>
                <div class="message-text"></div>
                <div class="message-time">${timeString}</div>
            </div>
        `;

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        const messageTextDiv = messageDiv.querySelector('.message-text');
        const formatted = formatMessage(message);

        if (sender === 'bot') {
            // If formatted message contains HTML tags, show instantly (no typing effect)
            if (/<[a-z][\s\S]*>/i.test(formatted)) {
                messageTextDiv.innerHTML = formatted;
            } else {
                typeWriterEffect(formatted, messageTextDiv, 18);
            }
        } else {
            messageTextDiv.textContent = message;
        }
    }

    function formatMessage(message) {
        if (!message) return '';

        let formatted = message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');

        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');
        return formatted;
    }

    function showLoadingIndicator() {
        if (!chatContainer) return '';

        const id = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-message';
        loadingDiv.id = id;

        loadingDiv.innerHTML = `
            <div class="message-avatar">
                <img src="${botAvatar}" alt="EDU BUDDY" onerror="this.onerror=null; this.src='/static/images/fallback-avatar.png';">
            </div>
            <div class="message-content">
                <div class="message-sender">EDU BUDDY</div>
                <div class="message-text">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;

        chatContainer.appendChild(loadingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return id;
    }

    function removeLoadingIndicator(id) {
        if (!id) return;
        const element = document.getElementById(id);
        if (element) {
            element.remove();
        }
    }

    function showSuggestions(suggestions) {
        if (!suggestionsContainer || !suggestions) return;

        suggestionsContainer.innerHTML = '';
        suggestions.forEach(suggestion => {
            if (!suggestion) return;

            const chip = document.createElement('div');
            chip.className = 'suggestion-chip';
            chip.textContent = suggestion;
            chip.addEventListener('click', () => {
                if (userInput) {
                    userInput.value = suggestion;
                    suggestionsContainer.innerHTML = '';
                    userInput.focus();
                }
            });
            suggestionsContainer.appendChild(chip);
        });
    }

    async function showQuizModal() {
        if (!quizModal) return;

        const topic = chatContainer?.lastElementChild?.querySelector('.message-text')?.textContent || 'General Knowledge';
        const quizContainer = quizModal.querySelector('#quiz-container');
        if (quizContainer) {
            quizContainer.innerHTML = '<p>Generating quiz about: ' + topic + '...</p>';
        }
        quizModal.style.display = 'flex';

        try {
            const response = await fetch('/generate_quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic: topic })
            });

            if (!response.ok) throw new Error('Failed to generate quiz');

            const quizData = await response.json();
            console.log('Quiz Data:', quizData);
            renderQuiz(quizData);
        } catch (error) {
            console.error('Error generating quiz:', error);
            if (quizContainer) {
                quizContainer.innerHTML = `
                    <p>Error generating quiz. Please try again.</p>
                    <button class="retry-quiz-btn">Retry</button>
                `;
                const retryBtn = quizContainer.querySelector('.retry-quiz-btn');
                if (retryBtn) {
                    retryBtn.addEventListener('click', showQuizModal);
                }
            }
        }
    }

    function renderQuiz(quizData) {
        const quizContainer = document.getElementById('quiz-container');
        if (!quizContainer) return;

        quizContainer.innerHTML = '';

        if (!quizData.questions || quizData.questions.length === 0) {
            quizContainer.innerHTML = '<p>Error: Could not generate quiz. Try a different topic.</p>';
            return;
        }

        const quizTitle = document.createElement('h3');
        quizTitle.textContent = `Quiz: ${quizData.topic || 'General Knowledge'}`;
        quizContainer.appendChild(quizTitle);

        const quizForm = document.createElement('form');
        quizForm.id = 'quiz-form';

        quizData.questions.forEach((question, index) => {
            const questionDiv = document.createElement('div');
            questionDiv.className = 'quiz-question';

            const questionTitle = document.createElement('h4');
            questionTitle.textContent = `${index + 1}. ${question.question || 'Question'}`;
            questionDiv.appendChild(questionTitle);

            question.options.forEach((option, optIndex) => {
                const optionDiv = document.createElement('div');
                optionDiv.className = 'quiz-option';

                const input = document.createElement('input');
                input.type = 'radio';
                input.name = `q${index}`;
                input.value = optIndex;
                input.id = `q${index}-o${optIndex}`;

                const label = document.createElement('label');
                label.htmlFor = `q${index}-o${optIndex}`;
                label.textContent = option.text || option;
                optionDiv.appendChild(input);
                optionDiv.appendChild(label);
                questionDiv.appendChild(optionDiv);
            });

            quizForm.appendChild(questionDiv);
        });

        const submitBtn = document.createElement('button');
        submitBtn.type = 'button';
        submitBtn.className = 'submit-quiz';
        submitBtn.textContent = 'Submit Quiz';
        submitBtn.addEventListener('click', submitQuiz);
        quizForm.appendChild(submitBtn);
        quizContainer.appendChild(quizForm);
    }

    async function submitQuiz() {
        const quizForm = document.getElementById('quiz-form');
        if (!quizForm) return;

        const answers = [];
        const questions = quizForm.querySelectorAll('.quiz-question');

        questions.forEach((question, index) => {
            const selectedOption = question.querySelector('input[type="radio"]:checked');
            answers.push(selectedOption ? parseInt(selectedOption.value) : null);
        });

        try {
            const response = await fetch('/submit_quiz', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ answers: answers })
            });

            if (!response.ok) throw new Error('Failed to submit quiz');

            const results = await response.json();
            renderQuizResults(results);
        } catch (error) {
            console.error('Error submitting quiz:', error);
            alert('Error submitting quiz. Please try again.');
        }
    }

    function renderQuizResults(results) {
        const quizContainer = document.getElementById('quiz-container');
        if (!quizContainer || !results) return;

        quizContainer.innerHTML = '';

        const resultTitle = document.createElement('h3');
        resultTitle.textContent = `Quiz Results: ${results.score?.toFixed(1) || 0}%`;
        quizContainer.appendChild(resultTitle);

        const resultSummary = document.createElement('p');
        resultSummary.textContent = `You answered ${results.correct_answers || 0} out of ${results.total_questions || 0} questions correctly.`;
        quizContainer.appendChild(resultSummary);

        if (results.results && results.results.length > 0) {
            const detailsList = document.createElement('ul');
            results.results.forEach((result, index) => {
                if (!result) return;

                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    <strong>${index + 1}. ${result.question}</strong><br>
                    Your Answer: ${result.user_answer_text}<br>
                    Correct Answer: ${result.correct_answer_text}<br>
                    Result: ${result.is_correct ? 'Correct' : 'Incorrect'}
                `;
                detailsList.appendChild(listItem);
            });
            quizContainer.appendChild(detailsList);
        }

        const retryBtn = document.createElement('button');
        retryBtn.className = 'submit-quiz';
        retryBtn.textContent = 'Retry Quiz';
        retryBtn.addEventListener('click', showQuizModal);
        quizContainer.appendChild(retryBtn);

        if (results.quiz_questions && results.quiz_questions.length > 0) {
            const questionsTitle = document.createElement('h4');
            questionsTitle.textContent = 'Current Quiz Questions';
            quizContainer.appendChild(questionsTitle);

            const questionsList = document.createElement('ul');
            results.quiz_questions.forEach((q, index) => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    <strong>${index + 1}. ${q.question}</strong>
                    <ul>
                        ${q.options.map(opt => `<li>${opt.text} (${opt.correct ? 'Correct' : 'Wrong'})</li>`).join('')}
                    </ul>
                `;
                questionsList.appendChild(listItem);
            });
            quizContainer.appendChild(questionsList);
        }
    }

    async function showProgressModal() {
        if (!progressModal) return;

        const progressContent = progressModal.querySelector('#progress-content');
        if (progressContent) {
            progressContent.innerHTML = '<p>Loading progress...</p>';
        } else {
            console.error('Could not find #progress-content element');
            return;
        }
        progressModal.style.display = 'flex';

        try {
            const response = await fetch('/progress');
            if (!response.ok) throw new Error('Failed to fetch progress');

            const progressData = await response.json();
            console.log('Progress Data:', progressData);
            renderProgress(progressData);
        } catch (error) {
            console.error('Error fetching progress:', error);
            if (progressContent) {
                progressContent.innerHTML = `
                    <p>Error loading progress. Please try again.</p>
                    <button class="retry-progress-btn">Retry</button>
                `;
                const retryBtn = progressContent.querySelector('.retry-progress-btn');
                if (retryBtn) {
                    retryBtn.addEventListener('click', showProgressModal);
                }
            }
        }
    }

  function renderProgress(progressData) {
    const progressContent = document.querySelector('#progress-content');
    if (!progressContent || !progressData) {
        console.error('Progress content element or data missing');
        return;
    }

    console.log('Progress Data received:', progressData);

    const totalQuizzes = progressData.total_quizzes || 0;
    const averageScore = progressData.average_score || 0;

    const weakAreas = Array.isArray(progressData.weak_areas)
        ? progressData.weak_areas
            .filter(a => a && a !== "None" && !a.includes("Thought"))
            .map(a => a.split().slice(0, 2).join(' '))  // First 1-2 words
            .slice(0, 2)
            .join(', ')
        : 'Koi nahi';

    const recentTopics = Array.isArray(progressData.recent_topics)
        ? progressData.recent_topics
            .filter(t => t && !t.includes("Thought") && t !== "Unknown")
            .map(t => t.split().slice(0, 2).join(' '))  // First 1-2 words
            .slice(0, 2)
            .join(', ')
        : 'Koi nahi';

    const newTopics = Array.isArray(progressData.new_topics)
        ? progressData.new_topics
            .filter(t => t && !t.includes("Thought") && t !== "Unknown")
            .map(t => t.split().slice(0, 2).join(' '))  // First 1-2 words
            .slice(0, 3)
            .join(', ')
        : 'Koi nahi';

    const quizHistory = Array.isArray(progressData.quiz_history) ? progressData.quiz_history.slice(0, 3) : [];

    progressContent.innerHTML = `
        <h3>Meri Seekh Raha Hai Taraqqi</h3>
        <div class="progress-card">
            <div class="progress-metric"><span>Total Quiz:</span><span>${totalQuizzes}</span></div>
            <div class="progress-metric"><span>Average Score:</span><span>${averageScore.toFixed(1)}%</span></div>
            <div class="progress-metric"><span>Past Quiz :</span><span>${weakAreas}</span></div>
            <div class="progress-metric"><span>Recent Topics:</span><span>${recentTopics}</span></div>
            <div class="progress-metric"><span>New Topics:</span><span>${newTopics}</span></div>
            <div class="progress-bar"><div class="progress-fill" style="width: ${averageScore}%"></div></div>
        </div>
        <h4>Quiz History</h4>
        <ul>
            ${quizHistory.map(q => {
                let topic = q.topic;
                if (topic === "Unknown") topic = "General";
                else if (topic.split().length > 2) topic = topic.split().slice(0, 2).join(' ');  // First 1-2 words
                const score = q.score || 0;
                const timestamp = q.timestamp || 'N/A';
                return `<li>${topic} - ${score}% (${timestamp})</li>`;
            }).join('')}
        </ul>
        <p><strong>Kuch Soch:</strong> Main seekha raha hoon, thodi practice se behtar ho jaonga! 😊</p>
    `;
}


    function startNewChat() {
        fetch('/clear', { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('Failed to clear session');
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    sessionStorage.clear();
                    if (chatContainer) chatContainer.innerHTML = '';
                    initChat();
                }
            })
            .catch(error => console.error('Error clearing session:', error));
    }

    function closeAllModals() {
        if (quizModal) quizModal.style.display = 'none';
        if (progressModal) progressModal.style.display = 'none';
    }

    function showBotLoader() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message bot-loader-message';

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <img src="${botAvatar}" alt="bot" onerror="this.onerror=null; this.src='/static/images/fallback-avatar.png';">
            </div>
            <div class="message-content">
                <div class="message-sender">EDU BUDDY</div>
                <div class="message-text">
                    <div class="vertical-dots-loader">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <div class="message-time"></div>
            </div>
        `;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return messageDiv;
    }

    // Jab API call start ho, loader show karo:
    const loaderDiv = showBotLoader();

    // Jab response mil jaye, loaderDiv ko remove karo ya replace karo bot ke actual message se:
    if (loaderDiv) loaderDiv.remove();
    addMessageToChat(botResponse, 'bot');
});