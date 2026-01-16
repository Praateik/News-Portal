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

// Generate image using Puter.js
async function generateArticleImage(headline, description) {
    const imageContainer = document.getElementById('article-image-container');
    const imageLoader = document.getElementById('image-loader');
    const articleImage = document.getElementById('article-image');
    
    try {
        // Show loader
        articleImage.style.display = 'none';
        imageLoader.style.display = 'block';
        
        // Create prompt for image generation
        const prompt = `${headline}. ${description.substring(0, 200)}`;
        
        // Use Gemini 2.5 Flash Image Preview (Nano Banana) as requested
        const generatedImg = await puter.ai.txt2img(prompt, { 
            model: "gemini-2.5-flash-image-preview",
            quality: "high"
        });
        
        // Hide loader
        imageLoader.style.display = 'none';
        
        if (generatedImg) {
            // Puter.js returns an img element or image data
            if (generatedImg instanceof HTMLImageElement) {
                // If it's an img element, use its src
                articleImage.src = generatedImg.src;
            } else if (typeof generatedImg === 'string') {
                // If it's a URL string
                articleImage.src = generatedImg;
            } else if (generatedImg.src) {
                // If it has a src property
                articleImage.src = generatedImg.src;
            }
            articleImage.style.display = 'block';
            articleImage.alt = headline;
        } else {
            // Fallback to placeholder or original image
            articleImage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error generating image:', error);
        // Fallback: show original image or placeholder
        articleImage.style.display = 'block';
        imageLoader.style.display = 'none';
    }
}

// Load and display article
async function loadArticle() {
    const articleURL = getArticleURLFromParams();
    
    if (!articleURL) {
        document.getElementById('article-headline').textContent = 'Article not found';
        preloader.remove();
        return;
    }
    
    try {
        // Encode URL for API call (base64)
        const encodedURL = btoa(articleURL).replace(/[+/=]/g, (m) => {
            return {'+': '-', '/': '_', '=': ''}[m];
        });
        
        // Fetch article from API
        const response = await fetch(`${API_BASE_URL}/article/${encodedURL}`);
        const data = await response.json();
        
        if (data.success && data.article) {
            const article = data.article;
            
            // Update headline
            document.getElementById('article-headline').textContent = article.headline || 'No headline';
            
            // Update meta information
            const author = Array.isArray(article.author) ? article.author.join(', ') : (article.author || 'Unknown');
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
            
            // Generate and display summary
            const fullText = article.article || article.description || '';
            const summary = generateSummary(fullText, 4);
            document.getElementById('summary-text').textContent = summary;
            
            // Display article body (use description if full article not available)
            const articleBody = document.getElementById('article-body');
            if (article.article && article.article.length > 200) {
                // Split into paragraphs
                const paragraphs = article.article.split('\n\n').filter(p => p.trim());
                articleBody.innerHTML = paragraphs.map(p => `<p>${p.trim()}</p>`).join('');
            } else {
                // Use description as body
                articleBody.innerHTML = `<p>${article.description || article.summary || 'Content not available.'}</p>`;
            }
            
            // Generate image using Puter.js
            await generateArticleImage(article.headline, article.description || article.summary || '');
            
            // Update page title
            document.title = `${article.headline} | Nepal Times`;
            
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

