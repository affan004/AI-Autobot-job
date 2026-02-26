## Gemini Grounding Credentials (AI Studio Primary)

The search layer now uses Gemini Grounding (Google Search tool) by default.

### AI Studio setup (recommended for local runs)
1. Open [Google AI Studio](https://aistudio.google.com/).
2. Create an API key.
3. Set `GOOGLE_AI_STUDIO_API_KEY` in `.env`.
4. Keep `GEMINI_SEARCH_USE_VERTEX=False`.

Minimum env:
```env
GOOGLE_AI_STUDIO_API_KEY=your_key
GEMINI_SEARCH_MODEL=gemini-2.5-flash
```

## Vertex AI setup (scaling/fallback)

Use this when you need higher sustained volume or enterprise controls.

1. Set up a Google Cloud project with Vertex AI enabled.
2. Configure one of:
   - `VERTEX_ACCESS_TOKEN` (short-lived bearer token), or
   - Application Default Credentials (ADC) on the machine.
3. Set:
```env
GEMINI_SEARCH_USE_VERTEX=True
VERTEX_PROJECT_ID=your_project_id
VERTEX_LOCATION=us-central1
VERTEX_GEMINI_MODEL=gemini-2.5-flash
```

If Vertex call fails, the search engine falls back to AI Studio when `GOOGLE_AI_STUDIO_API_KEY` is available.

