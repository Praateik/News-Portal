"""
Configuration file for Nepal Times News Aggregator
"""

# Google Gemini API Configuration
# NOTE: The value below is an OAuth Client ID, not an API key
# To use Gemini, get an API key from: https://makersuite.google.com/app/apikey
# For now, set to empty string to disable Gemini features
GEMINI_API_KEY = ""  # Set your Gemini API key here
GEMINI_MODEL = "gemini-1.5-pro"  # or "gemini-1.5-flash" for faster generation

# News Update Schedule (in hours)
UPDATE_INTERVAL_HOURS = 1

# News Portal Configuration
NEWS_PORTALS = {
    'ekantipur': {
        'name': 'ekantipur',
        'url': 'https://ekantipur.com/',
        'rss': 'https://ekantipur.com/rss'
    },
    'onlinekhabar': {
        'name': 'Onlinekhabar',
        'url': 'https://www.onlinekhabar.com/',
        'rss': 'https://www.onlinekhabar.com/feed'
    },
    'setopati': {
        'name': 'Setopati',
        'url': 'https://www.setopati.com/',
        'rss': 'https://www.setopati.com/rss'
    },
    'cnn': {
        'name': 'CNN',
        'url': 'https://edition.cnn.com/',
        'rss': 'http://rss.cnn.com/rss/edition.rss'
    },
    'bbcnepali': {
        'name': 'BBC Nepali',
        'url': 'https://www.bbc.com/nepali',
        'rss': 'https://feeds.bbci.co.uk/nepali/rss.xml'
    }
}

# Similarity threshold for duplicate detection (0-1)
SIMILARITY_THRESHOLD = 0.7

# Minimum number of portals a news must appear in to be featured
MIN_PORTALS_FOR_FEATURED = 2

