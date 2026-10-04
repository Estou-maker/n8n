# Daily YouTube Kids Video Generator

Automated n8n + GitHub Actions pipeline to generate daily 3-minute nursery rhyme videos for YouTube Kids using **only free services**.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  n8n (local, Cron daily 6 AM)                                   │
│    │                                                            │
│    ├─► Gemini 1.5 Flash (free) → Script + 15 scene prompts     │
│    │                                                            │
│    ├─► Pollinations.ai (free, no key) → 15 scene images        │
│    │       Character consistency via fixed prompt + seed       │
│    │                                                            │
│    ├─► Edge TTS (Microsoft, free) → Voiceover + timing JSON    │
│    │                                                            │
│    └─► GitHub Actions (workflow_dispatch) → Render + Upload    │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ GitHub Actions Runner (Ubuntu, 2000 min/mo free)        │   │
│  │   • MoviePy: Ken Burns + lyric karaoke + transitions    │   │
│  │   • FFmpeg: 1080p MP4 render (~3 min)                   │   │
│  │   • YouTube Data API → Upload (madeForKids=true)        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Required Credentials

| Service | How to Get | n8n Credential Type |
|---------|------------|---------------------|
| **Gemini API** | [Google AI Studio](https://aistudio.google.com/apikey) | "Gemini API" (Generic API Key) |
| **GitHub Token** | GitHub Settings → Developer Settings → Personal Access Tokens (classic) → `repo`, `workflow` scopes | "GitHub API" (Generic API Key) |
| **YouTube OAuth** | [Google Cloud Console](https://console.cloud.google.com/) → Enable YouTube Data API v3 → OAuth Client ID (Web App) → Redirect: `https://YOUR-NGROK.ngrok.io/rest/oauth2-credential/callback` | "YouTube OAuth2 API" |

## Setup

### 1. Clone & Configure Repo
```bash
git clone https://github.com/Estou-maker/n8n.git
cd n8n
```

### 2. Add GitHub Repository Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `YOUTUBE_CLIENT_ID` | YouTube OAuth Client ID |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth Client Secret |
| `YOUTUBE_REFRESH_TOKEN` | Get from n8n after OAuth flow (see below) |

### 3. Get YouTube Refresh Token
1. In n8n, create **YouTube OAuth2 API** credential with your Client ID/Secret
2. Set redirect URI to your ngrok/Cloudflare URL + `/rest/oauth2-credential/callback`
3. Click "Connect" → Authorize → Copy the `refresh_token` from n8n's credential storage
4. Add as `YOUTUBE_REFRESH_TOKEN` secret

### 4. Configure n8n Workflow
1. Import `n8n-workflow.json` in n8n (Workflows → Import)
2. Create credentials in n8n:
   - **Gemini API**: Generic Auth → Header Auth → `Authorization: Bearer YOUR_KEY`
   - **GitHub API**: Generic Auth → Header Auth → `Authorization: Bearer YOUR_GITHUB_TOKEN`
   - **YouTube OAuth2**: Use the credential from step 3
3. Activate workflow

### 5. Add Background Music (Optional)
Place CC0 music files in `assets/music/` (create folder):
```bash
mkdir -p assets/music
# Add cheerful_background.mp3 etc.
```

### 6. Test Run
In GitHub Actions tab → "Render YouTube Kids Video" → "Run workflow" → paste test script JSON → Run.

## Free Tier Limits

| Service | Limit | Covers |
|---------|-------|--------|
| Gemini 1.5 Flash | 1500 req/day | 1 video/day ✓ |
| Pollinations.ai | Unlimited* (rate limited) | 15 images/video ✓ |
| Edge TTS | Unlimited | Voiceover ✓ |
| GitHub Actions | 2000 min/mo | ~15 renders/mo ✓ |
| YouTube API | 10,000 units/day | 1 upload = ~1600 units ✓ |

*Pollinations has no published hard limit but may throttle heavy usage.

## Customization

- **Character**: Edit `CHARACTER_PROMPT` in "Generate Scene Images" node
- **Style**: Modify Gemini prompt in "Generate Script" node
- **Video length**: Adjust scene count/durations in Gemini prompt
- **Music**: Add CC0 tracks to `assets/music/`
- **Upload privacy**: Change `privacyStatus` in YouTube upload node (`private` → `public` after review)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Invalid redirect URI" | Use ngrok/Cloudflare tunnel for local n8n OAuth |
| GitHub Actions timeout | Reduce video quality/bitrate in `render_video.py` |
| Pollinations rate limit | Increase delay in "Generate Scene Images" node |
| YouTube upload fails | Check quota, refresh token expiry, madeForKids=true |

## Files

- `n8n-workflow.json` — Import into n8n
- `.github/workflows/render-video.yml` — GitHub Actions render job
- `render_video.py` — MoviePy video assembly (Ken Burns, karaoke lyrics, transitions)
- `requirements.txt` — Python dependencies

## License

MIT — Free to use, modify, distribute.