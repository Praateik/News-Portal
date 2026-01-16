# Gemini API Setup Notes

## Important Note

The OAuth client ID you provided (`254747498469-dap5shs24ment28ri0d8166ad7nkgtat.apps.googleusercontent.com`) is a **Google OAuth Client ID**, not a Gemini API key.

## Gemini API Key vs OAuth Client ID

- **Gemini API Key**: Used for direct API access to Gemini models
- **OAuth Client ID**: Used for user authentication and authorization

## Options for Image Generation

### Option 1: Use Gemini API Key (Recommended)
1. Get a Gemini API key from: https://makersuite.google.com/app/apikey
2. Update `config.py` with: `GEMINI_API_KEY = "your-api-key-here"`

### Option 2: Use Google Imagen API (For Image Generation)
Gemini models are text models and don't generate images directly. For image generation, you would need:
- Google Imagen API (requires different setup)
- OpenAI DALL-E API
- Stable Diffusion API
- Other image generation services

### Option 3: Use OAuth for User Authentication (Current Setup)
If you want to use OAuth, you'll need to set up OAuth flow for user authentication.

## Current Implementation

The current code uses Gemini for:
- Generating image descriptions (text)
- Creating prompts for image generation

For actual image generation, you would need to integrate a separate image generation API.

## Quick Fix for Now

For now, the system will:
1. Use original images from news articles
2. Detect watermarks (basic detection)
3. Skip watermark removal if Gemini is not properly configured
4. Still work with duplicate detection and hourly updates

To enable full functionality, get a Gemini API key and update `config.py`.






