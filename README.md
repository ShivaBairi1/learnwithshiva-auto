# LearnWithShiva — free scheduled YouTube starter

This starter project runs on GitHub Actions (cloud runner) and can be configured from an Android browser. It uses:
- Gemini API free tier (when available) for original educational scripts
- espeak-ng for local synthetic narration on the runner
- Pillow + FFmpeg for original motion-card style videos and thumbnails
- YouTube Data API for upload

It creates one Short and one long-form educational video per scheduled run. It does **not** guarantee YouTube monetization, views, or uninterrupted free quotas.

## Before you start
1. Create a GitHub account and a **private** repository named `learnwithshiva-auto`. Keep it private because workflow code and settings are personal. GitHub Actions minutes are limited on private repos; public repos have free standard runner use, but code is public. Check current GitHub billing.
2. Upload the contents of this ZIP into the repository (keep the `.github/workflows/daily.yml` path).
3. In Google AI Studio, create a Gemini API key.
4. In Google Cloud Console, create a project, enable **YouTube Data API v3**, configure OAuth consent, and create OAuth client credentials.
5. Generate a YouTube OAuth refresh token for the Google account that owns/manages LearnWithShiva. Use the OAuth Playground instructions below.
6. Add GitHub repository Actions secrets (Settings → Secrets and variables → Actions → New repository secret):
   - `GEMINI_API_KEY`
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
   - `YOUTUBE_REFRESH_TOKEN`
7. In GitHub, open Actions → enable workflows. Run **Daily LearnWithShiva videos** manually once. Check the logs and YouTube Studio before enabling the daily schedule.

## Create the YouTube refresh token (one-time)
This is the part that grants upload access. Never paste the token into chat, source code, or a public repository.

1. In Google Cloud Console, enable YouTube Data API v3.
2. Configure the OAuth consent screen. Add your own Google account as a test user if the app is in Testing.
3. Create an OAuth Client ID. Choose **Web application** and add this authorized redirect URI:
   `https://developers.google.com/oauthplayground`
4. Open https://developers.google.com/oauthplayground
5. Click the gear icon → enable **Use your own OAuth credentials**. Enter the OAuth client ID and client secret.
6. In Step 1, enter this scope:
   `https://www.googleapis.com/auth/youtube.upload`
7. Authorize using the Google account that manages LearnWithShiva. In Step 2, exchange the code for tokens.
8. Copy the **refresh_token** into the GitHub secret `YOUTUBE_REFRESH_TOKEN`.

Google may require the OAuth app to be published/verified for durable use. Apps left in Testing can issue refresh tokens that expire after 7 days. If the token expires, repeat the OAuth flow. Do not try to bypass Google's consent or verification requirements.

## Schedule
The workflow runs Tuesday, Thursday, and Saturday at 12:30 UTC (18:00 India time), plus manual runs. Each run creates one Short and one long-form video. This restrained schedule is a better starting point than flooding the channel. GitHub scheduled jobs can be delayed. Edit `.github/workflows/daily.yml` to change the schedule.

## What it publishes
- One vertical Short (9:16), about 35–60 seconds
- One horizontal explainer (16:9), about 2–4 minutes
- Original generated narration, on-screen teaching cards, title/description, and thumbnail
- Category: Education; audience setting: not made for kids (change this if the content is actually directed to children)

The visual style is intentionally simple and self-created rather than scraped footage. Review facts and videos regularly. For the first test, change `PRIVACY_STATUS` in `main.py` to `private`; after verifying the output, change it to `public` if you want automatic public publishing.

## Monetization-safe publishing checklist
- Make each episode meaningfully different and fact-check it.
- Add original explanations, examples, analogies, and a clear learning outcome.
- Do not mass-produce interchangeable template videos.
- Do not use copyrighted music, movie clips, sports footage, or images without rights.
- If realistic altered/synthetic content could mislead viewers, use YouTube's altered-content disclosure where required.
- AI assistance itself does not guarantee or prevent monetization. YouTube reviews the channel's overall originality and value.

## Troubleshooting
- `GEMINI_API_KEY missing`: add the secret with the exact name.
- `invalid_grant`: refresh token expired/revoked; repeat OAuth setup.
- `quotaExceeded`: check YouTube API quota / Google Cloud project.
- Gemini 429: free-tier rate limit reached; rerun later or reduce frequency.
- FFmpeg/espeak errors: check the Actions log; workflow installs these dependencies on each run.

## Security
Never commit `.env`, OAuth tokens, API keys, downloaded credentials, or personal account data. Use GitHub Actions Secrets only. Revoke the OAuth grant in your Google Account security settings if you no longer want this workflow to upload.
