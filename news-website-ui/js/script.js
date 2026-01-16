    const preloader = document.querySelector(".preloader");
    // Use the same protocol and hostname as the current page, or default to localhost
    const API_BASE_URL = (() => {
        // If running from file:// or need to specify, use localhost
        // In production, this should match your backend domain
        const hostname = window.location.hostname;
        const protocol = window.location.protocol;
        const port = '5000';
        
        // Check if we're on localhost or 127.0.0.1
        if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') {
            // Use 127.0.0.1 to match backend default, or localhost if backend uses it
            return `${protocol}//127.0.0.1:${port}/api`;
        }
        // Production: use same domain or configured backend
        return `${protocol}//${hostname}:${port}/api`;
    })();

    // Category mapping
    const categoryMap = {
        'sports': 'sports-category',
        'entertainment': 'entertainment-category',
        'technology': 'technology-category',
        'tech': 'technology-category',
        'business': 'sports-category', // Using sports-category style
        'news': 'sports-category',
        'default': 'sports-category'
    };

    window.addEventListener('load', async () => {
        await loadNews();
        preloader.remove();
    });

    async function loadNews() {
        try {
            // Fetch news from API with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch(`${API_BASE_URL}/news?limit=15`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            // Check if response is ok
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            if (data.success && data.articles && data.articles.length > 0) {
                // Use featured article if available, otherwise use first article
                const featuredArticle = data.featured || data.articles[0];

                // Update featured article (showcase)
                updateFeaturedArticle(featuredArticle);

                // Filter out featured article from list
                const featuredUrl = featuredArticle?.url;
                const otherArticles = data.articles.filter(a => a.url !== featuredUrl);

                // Update articles grid
                updateArticlesGrid(otherArticles);
            } else {
                console.warn('No articles found in response');
                showError('No news articles available at this time.');
            }
        } catch (error) {
            // Handle different error types
            if (error.name === 'AbortError') {
                console.error('Request timeout: Server did not respond in time');
                showError('Request timeout. Please check if the server is running.');
            } else if (error instanceof TypeError && error.message.includes('fetch')) {
                console.error('Network error: Cannot connect to server');
                console.error('Make sure the backend server is running on http://127.0.0.1:5000');
                showError('Cannot connect to news server. Please ensure the server is running.');
            } else if (error.message && error.message.includes('HTTP error')) {
                console.error(`HTTP error: ${error.message}`);
                showError(`Server error: ${error.message}`);
            } else {
                console.error('Error fetching news:', error);
                showError('An error occurred while loading news. Please try again later.');
            }
        }
    }

    function updateFeaturedArticle(article) {
        const showcase = document.querySelector('.showcase');
        if (!showcase || !article) return;

        const textContent = showcase.querySelector('.text-content');
        if (!textContent) return;

        // Update category
        const categoryEl = textContent.querySelector('.sports-category, .entertainment-category, .technology-category');
        if (categoryEl) {
            categoryEl.className = getCategoryClass(article.category || article.source || 'news');
            categoryEl.textContent = article.category || article.source || 'News';
        }

        // Update headline
        const headlineEl = textContent.querySelector('h1');
        if (headlineEl) {
            headlineEl.textContent = article.headline || 'No headline';
        }

        // Update description
        const descEl = textContent.querySelector('p:not(.sports-category):not(.entertainment-category):not(.technology-category)');
        if (descEl) {
            descEl.textContent = article.description || article.summary || 'Click to read more...';
        }

        // Update link to point to article page
        const linkEl = textContent.querySelector('a');
        if (linkEl && article.url) {
            const urlHash = btoa(article.url).replace(/[+/=]/g, '');
            linkEl.href = `./html/article.html?id=${urlHash}`;
        }

        // Update background image if available
        if (article.image_url) {
            showcase.style.backgroundImage = `url('${article.image_url}')`;
            showcase.style.backgroundSize = 'cover';
            showcase.style.backgroundPosition = 'center';
        }
    }

    function updateArticlesGrid(articles) {
        const articlesContainer = document.querySelector('.articles');
        if (!articlesContainer) return;

        // Clear existing articles (keep first few for fallback if needed)
        articlesContainer.innerHTML = '';

        // Create article cards
        articles.forEach((article, index) => {
            const card = createArticleCard(article, index);
            articlesContainer.appendChild(card);
        });
    }

    function createArticleCard(article, index) {
        const card = document.createElement('a');

        // Create URL hash for article
        const articleHash = btoa(article.url || '').replace(/[+/=]/g, '').substring(0, 16);
        // Alternative: use MD5 hash (would need crypto-js library)
        // For now, use base64 encoding
        const urlHash = btoa(article.url || '').replace(/[+/=]/g, '');

        card.href = `./html/article.html?id=${urlHash}`;
        card.className = 'card';

        const categoryClass = getCategoryClass(article.category || article.source || 'news');
        const categoryName = article.category || article.source || 'News';

        let cardHTML = '';

        // Alternate image position for visual variety
        if (article.image_url && index % 3 !== 1) {
            cardHTML += `<img src="${article.image_url}" alt="${article.headline || ''}" onerror="this.style.display='none'" />`;
        }

        cardHTML += `
            <article>
                <p class="${categoryClass}">${categoryName}</p>
                <h1>${article.headline || 'No headline'}</h1>
                <p>${truncateText(article.description || article.summary || '', 150)}</p>
            </article>
        `;

        if (article.image_url && index % 3 === 1) {
            cardHTML += `<img src="${article.image_url}" alt="${article.headline || ''}" onerror="this.style.display='none'" />`;
        }

        card.innerHTML = cardHTML;
        return card;
    }

    function getCategoryClass(category) {
        if (!category) return categoryMap.default;
        const categoryLower = category.toLowerCase();

        for (const [key, value] of Object.entries(categoryMap)) {
            if (categoryLower.includes(key)) {
                return value;
            }
        }
        return categoryMap.default;
    }

    function truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    function showError(message) {
        const articlesContainer = document.querySelector('.articles');
        if (articlesContainer) {
            articlesContainer.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #c72727;">
                    <p>${message}</p>
                </div>
            `;
        }
    }