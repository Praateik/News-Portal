const preloader = document.querySelector(".preloader");
// Use the same protocol and hostname as the current page
const API_BASE_URL = (() => {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = '5000';
    
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') {
        return `${protocol}//127.0.0.1:${port}/api`;
    }
    return `${protocol}//${hostname}:${port}/api`;
})();

// Category mapping
const categoryMap = {
    'sports': 'sports-category',
    'entertainment': 'entertainment-category',
    'technology': 'technology-category',
    'tech': 'technology-category',
    'business': 'sports-category',
    'news': 'sports-category',
    'default': 'sports-category'
};

// Get article URL from URL parameter
function getArticleURLFromParams() {
    const params = new URLSearchParams(window.location.search);
    const hash = params.get('id');
    if (!hash) return null;
    
    // The hash is base64 encoded URL
    try {
        // Add padding if needed
        let base64 = hash.replace(/-/g, '+').replace(/_/g, '/');
        while (base64.length % 4) {
            base64 += '=';
        }
        const url = atob(base64);
        if (url.startsWith('http')) {
            return url;
        }
    } catch (e) {
        console.error('Error decoding URL:', e);
    }
    return hash; // Return hash as fallback
}

// Generate summary from article text
function generateSummary(text, maxSentences = 3) {
    if (!text) return "No summary available.";
    
    // Simple summarization: take first few sentences
    const sentences = text.match(/[^\.!\?]+[\.!\?]+/g) || [];
    return sentences.slice(0, maxSentences).join(' ').trim() || text.substring(0, 200) + '...';
}

// Progressive image loading - polls for AI-generated image
let imagePollingInterval = null;
let imagePollingAttempts = 0;
const MAX_POLLING_ATTEMPTS = 120; // 6 minutes (30 polls * 12s)
const POLLING_INTERVAL = 3000; // 3 seconds

async function pollForFinalImage(articleURL) {
    if (imagePollingAttempts >= MAX_POLLING_ATTEMPTS) {
        console.log('Image polling timeout - keeping placeholder');
        return;
    }
    
    try {
        // Re-fetch article to check if image has been generated
        const encodedURL = btoa(articleURL).replace(/[+/=]/g, (m) => {
            return {'+': '-', '/': '_', '=': ''}[m];
        });
        
        const response = await fetch(`${API_BASE_URL}/article/${encodedURL}`);
        const data = await response.json();
        
        if (data.success && data.article) {
            const newImage = data.article.image_url;
            const currentImage = document.getElementById('article-image').src;
            
            // Check if we got a real image (not placeholder)
            if (newImage && 
                !newImage.includes('placeholder') && 
                newImage !== currentImage) {
                console.log('✓ Real image received, updating...');
                document.getElementById('article-image').src = newImage;
                document.getElementById('article-image').alt = data.article.title;
                
                // Stop polling
                if (imagePollingInterval) {
                    clearInterval(imagePollingInterval);
                    imagePollingInterval = null;
                }
                return;
            }
        }
    } catch (error) {
        console.error('Error polling for image:', error);
    }
    
    imagePollingAttempts++;
}

function setupProgressiveImagePolling(articleURL) {
    // Show loader while polling
    const imageLoader = document.getElementById('image-loader');
    if (imageLoader) {
        imageLoader.style.display = 'block';
    }
    
    // Start polling for real image
    imagePollingInterval = setInterval(() => {
        pollForFinalImage(articleURL);
    }, POLLING_INTERVAL);
    
    // Also poll immediately
    pollForFinalImage(articleURL);
}

// Load and display article (optimized for <200ms TTFB)
async function loadArticle() {
    const articleURL = getArticleURLFromParams();
    
    if (!articleURL) {
        document.getElementById('article-headline').textContent = 'Article not found';
        preloader.remove();
        return;
    }
    
    try {
        const startTime = performance.now();
        
        // Fetch article from optimized API endpoint
        const response = await fetch(`${API_BASE_URL}/article?url=${encodeURIComponent(articleURL)}`);
        const data = await response.json();
        const fetchTime = performance.now() - startTime;
        
        console.log(`✓ Article fetched in ${fetchTime.toFixed(1)}ms`);
        
        if (data.success && data.article) {
            const article = data.article;
            
            // Update headline
            document.getElementById('article-headline').textContent = article.title || 'No headline';
            
            // Update meta information
            const author = Array.isArray(article.author) 
                ? article.author.join(', ') 
                : (article.author || 'Unknown');
            document.getElementById('article-author').textContent = `Written By ${author}`;
            
            if (article.date_publish) {
                const date = new Date(article.date_publish);
                document.getElementById('article-date').textContent = ` ${date.toLocaleDateString()}`;
            }
            
            // Update category
            const categoryEl = document.getElementById('article-category');
            const categoryClass = getCategoryClass(article.category || article.source || 'news');
            categoryEl.className = categoryClass;
            categoryEl.textContent = article.category || article.source || 'News';
            
            // Update source
            document.getElementById('article-source').textContent = article.source || 'Unknown';
            document.getElementById('original-link').href = article.url || '#';
            
            // Display summary (AI-generated)
            document.getElementById('summary-text').textContent = article.summary || 'Summary not available';
            
            // Display article body
            const articleBody = document.getElementById('article-body');
            if (article.content && article.content.length > 200) {
                // Split into paragraphs
                const paragraphs = article.content.split('\n\n').filter(p => p.trim());
                articleBody.innerHTML = paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
            } else {
                // Use description as fallback
                articleBody.innerHTML = `<p>${article.summary || 'Content not available.'}</p>`;
            }
            
            // Display image (placeholder + progressive loading)
            const articleImage = document.getElementById('article-image');
            if (article.image_url) {
                articleImage.src = article.image_url;
                articleImage.alt = article.title;
            } else {
                articleImage.src = '/images/placeholder-blur.jpg';
            }
            
            // Setup progressive image polling for AI-generated image updates
            setupProgressiveImagePolling(articleURL);
            
            // Update page title
            document.title = `${article.title} | Nepal Times`;
            
        } else {
            document.getElementById('article-headline').textContent = 'Article not found';
            document.getElementById('article-body').innerHTML = '<p>Sorry, we could not find this article.</p>';
        }
    } catch (error) {
        console.error('Error loading article:', error);
        document.getElementById('article-headline').textContent = 'Error loading article';
        document.getElementById('article-body').innerHTML = '<p>There was an error loading this article. Please try again later.</p>';
    } finally {
        preloader.remove();
    }
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

// Initialize when page loads
window.addEventListener('load', () => {
    loadArticle();
});

