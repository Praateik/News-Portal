const preloader = document.querySelector(".preloader");

// Use the same protocol and hostname as the current page
const API_BASE_URL = (() => {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = '5000';  // Production backend port
    
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') {
        return `${protocol}//127.0.0.1:${port}/api`;
    }
    return `${protocol}//${hostname}:${port}/api`;
})();

// Performance monitoring
const metrics = {
    startTime: performance.now(),
    ttfb: null,
    renderTime: null
};

document.addEventListener("DOMContentLoaded", async () => {
    await loadNews();
    
    // Calculate render time
    metrics.renderTime = performance.now() - metrics.startTime;
    console.log(`✓ Page rendered in ${metrics.renderTime.toFixed(1)}ms`);
    
    preloader.remove();
});

async function loadNews() {
    try {
        const start = performance.now();
        const res = await fetch(`${API_BASE_URL}/news?limit=15`);
        metrics.ttfb = performance.now() - start;
        
        const data = await res.json();
        console.log(`✓ API response: ${metrics.ttfb.toFixed(1)}ms TTFB`);

        if (!data.success || !data.articles || data.articles.length === 0) {
            showError("No news available right now.");
            return;
        }

        renderFeatured(data.articles[0]);
        renderArticles(data.articles.slice(1));
    } catch (err) {
        console.error('Error loading news:', err);
        showError("Unable to connect to the news server.");
    }
}

/* ================= FEATURED ================= */

function renderFeatured(article) {
    const featured = document.getElementById("featured-article");

    featured.innerHTML = `
        <p class="sports-category">${article.category || "News"}</p>
        <h1>${article.title || "Breaking News"}</h1>
        <p>${article.summary || article.description || "Read the full article for details."}</p>
        <a href="./html/article.html?id=${encode(article.url)}">Read More</a>
    `;

    if (article.image_url) {
        document.querySelector(".showcase").style.backgroundImage =
            `url('${article.image_url}')`;
        document.querySelector(".showcase").style.backgroundSize = "cover";
        document.querySelector(".showcase").style.backgroundPosition = "center";
    }
}

/* ================= GRID ================= */

function renderArticles(articles) {
    const container = document.getElementById("articles");
    container.innerHTML = "";

    articles.forEach(article => {
        const card = document.createElement("a");
        card.className = "card";
        card.href = `./html/article.html?id=${encode(article.url)}`;

        // Use AI-generated summary if available
        const description = article.summary || article.description || "Click to read more...";
        
        card.innerHTML = `
            ${article.image_url ? `<img src="${article.image_url}" alt="${article.title}" loading="lazy" />` : ""}
            <article>
                <p class="sports-category">${article.category || "News"}</p>
                <h1>${article.title || "Article"}</h1>
                <p>${truncate(description)}</p>

        container.appendChild(card);
    });
}

/* ================= HELPERS ================= */

function truncate(text = "", max = 140) {
    return text.length > max ? text.slice(0, max) + "..." : text;
}

function encode(url) {
    return btoa(url).replace(/=/g, "");
}

function showError(msg) {
    document.getElementById("articles").innerHTML = `
        <p style="grid-column:1/-1;text-align:center;color:#c72727">
            ${msg}
        </p>
    `;
}
