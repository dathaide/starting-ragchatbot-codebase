// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton, themeToggle;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');
    
    setupEventListeners();
    initializeTheme();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // New Chat button
    newChatButton.addEventListener('click', startNewChat);
    
    // Theme toggle button
    themeToggle.addEventListener('click', toggleTheme);
    
    // Keyboard navigation for theme toggle
    themeToggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleTheme();
        }
    });
    
    // Global keyboard shortcut for theme toggle (Ctrl/Cmd + Shift + T)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 't') {
            e.preventDefault();
            toggleTheme();
        }
    });
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Group sources by course for better organization
        const courseGroups = {};
        sources.forEach((source, index) => {
            // Extract course name and lesson info
            const match = source.text.match(/^(.+?) - Lesson (\d+)$/);
            if (match) {
                const courseName = match[1];
                const lessonNum = match[2];
                if (!courseGroups[courseName]) {
                    courseGroups[courseName] = [];
                }
                courseGroups[courseName].push({
                    lesson: lessonNum,
                    url: source.url,
                    text: source.text
                });
            } else {
                // Handle sources without lesson numbers
                if (!courseGroups['Other']) {
                    courseGroups['Other'] = [];
                }
                courseGroups['Other'].push({
                    lesson: '',
                    url: source.url,
                    text: source.text
                });
            }
        });

        // Create table HTML
        let tableHtml = '<div class="sources-table"><table>';
        tableHtml += '<thead><tr><th>Course</th><th>Lesson</th><th>Link</th></tr></thead>';
        tableHtml += '<tbody>';
        
        Object.entries(courseGroups).forEach(([courseName, lessons]) => {
            lessons.sort((a, b) => parseInt(a.lesson) - parseInt(b.lesson));
            lessons.forEach((lesson, index) => {
                tableHtml += '<tr>';
                // Only show course name in first row for this course
                if (index === 0) {
                    tableHtml += `<td rowspan="${lessons.length}" class="course-name">${escapeHtml(courseName)}</td>`;
                }
                tableHtml += `<td class="lesson-num">${lesson.lesson ? `Lesson ${lesson.lesson}` : '-'}</td>`;
                tableHtml += `<td class="lesson-link">`;
                if (lesson.url) {
                    tableHtml += `<a href="${escapeHtml(lesson.url)}" target="_blank" class="source-link">Open Video</a>`;
                } else {
                    tableHtml += '<span class="no-link">No link</span>';
                }
                tableHtml += '</td></tr>';
            });
        });
        
        tableHtml += '</tbody></table></div>';
        
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources (${sources.length})</summary>
                <div class="sources-content">${tableHtml}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

// Start new chat function for button click
async function startNewChat() {
    try {
        // Clear current session on backend if exists
        if (currentSessionId) {
            await fetch(`${API_URL}/clear-session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: currentSessionId
                })
            });
        }
    } catch (error) {
        console.warn('Failed to clear session on backend:', error);
        // Continue with frontend cleanup even if backend fails
    }
    
    // Create new session (frontend cleanup)
    await createNewSession();
}

async function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}

// Theme Management Functions
function initializeTheme() {
    // Check for system preference first, then saved preference, then default to 'dark'
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let theme;
    if (savedTheme) {
        theme = savedTheme;
    } else if (window.matchMedia) {
        theme = systemPrefersDark ? 'dark' : 'light';
    } else {
        theme = 'dark'; // fallback
    }
    
    setTheme(theme, false); // false = don't save to localStorage on initial load
    
    // Listen for system theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            // Only auto-switch if user hasn't manually set a preference
            if (!localStorage.getItem('theme')) {
                setTheme(e.matches ? 'dark' : 'light', false);
            }
        });
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Add a subtle animation class for smoother transition
    document.body.classList.add('theme-transitioning');
    
    setTheme(newTheme, true);
    
    // Remove the transition class after animation completes
    setTimeout(() => {
        document.body.classList.remove('theme-transitioning');
    }, 300);
    
    // Dispatch custom event for other parts of the app to respond to theme changes
    window.dispatchEvent(new CustomEvent('themeChanged', { 
        detail: { theme: newTheme } 
    }));
}

function setTheme(theme, shouldSave = true) {
    // Validate theme parameter
    if (theme !== 'dark' && theme !== 'light') {
        console.warn('Invalid theme:', theme, 'defaulting to dark');
        theme = 'dark';
    }
    
    document.documentElement.setAttribute('data-theme', theme);
    
    // Only save to localStorage if explicitly requested (not on initial load from system preference)
    if (shouldSave) {
        localStorage.setItem('theme', theme);
    }
    
    // Update aria-label for better accessibility
    const toggleButton = document.getElementById('themeToggle');
    if (toggleButton) {
        toggleButton.setAttribute('aria-label', 
            `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
        toggleButton.setAttribute('title', 
            `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
    }
    
    // Update meta theme-color for mobile browsers
    updateMetaThemeColor(theme);
}

function updateMetaThemeColor(theme) {
    let metaThemeColor = document.querySelector('meta[name="theme-color"]');
    
    if (!metaThemeColor) {
        metaThemeColor = document.createElement('meta');
        metaThemeColor.name = 'theme-color';
        document.head.appendChild(metaThemeColor);
    }
    
    // Set theme color based on current theme
    metaThemeColor.content = theme === 'dark' ? '#0f172a' : '#ffffff';
}

// Utility function to get current theme
function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
}