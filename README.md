# Hackathon Alert Webhook Bot

A Discord webhook bot that automatically monitors and notifies you about upcoming hackathons from multiple sources.

## Features

- **Multi-Source Aggregation**: Fetches from 3 different hackathon sources:
  - [Hackalist](https://www.hackalist.org/) - JSON API with structured data
  - [MLH (Major League Hacking)](https://mlh.io/) - Official high-quality events
  - [Devpost](https://devpost.com/) - Comprehensive list including online/hybrid
- **Smart Deduplication**: Avoids posting duplicate hackathons
- **Future-Only Filtering**: Only shows upcoming events
- **Rich Discord Embeds**: Beautiful notifications with dates, location, type, and links
- **Automated Checks**: Runs every 3 hours via GitHub Actions
- **Free**: No server costs, completely serverless

## Setup

### 1. Fork/Clone This Repository

```bash
git clone <your-repo-url>
cd hackathon-alert-webhook
```

### 2. Configure Webhook URL

Your Discord webhook URL is already configured in `config.json`. To change it:

1. Go to your Discord server settings
2. Navigate to Integrations > Webhooks
3. Create a new webhook or copy an existing one
4. Update the `discord_webhook_url` in `config.json`

### 3. Install Dependencies (Local Testing)

```bash
pip install -r requirements.txt
```

### 4. Test Locally

```bash
python bot.py
```

You should see output like:
```
🚀 Starting Hackathon Alert Bot...
🔍 Fetching from Hackalist...
🔍 Fetching from MLH...
🔍 Fetching from Devpost...
📊 Found 45 total hackathons
🔍 42 unique hackathons
📅 38 within date range
🆕 38 new hackathons to post
✅ Posted: Example Hackathon 2025
...
✨ Done! Posted 38 new hackathons
```

### 5. Enable GitHub Actions

1. Push your code to GitHub
2. Go to your repository's **Settings** > **Actions** > **General**
3. Enable **Read and write permissions** for workflows
4. Go to the **Actions** tab and enable workflows
5. The bot will now run automatically every 3 hours

You can also manually trigger it:
- Go to **Actions** tab
- Select "Hackathon Alert Checker"
- Click "Run workflow"

## Configuration

Edit `config.json` to customize behavior:

```json
{
  "discord_webhook_url": "YOUR_WEBHOOK_URL",
  "sources": [
    {
      "name": "Hackalist",
      "enabled": true
    },
    {
      "name": "MLH",
      "enabled": true
    },
    {
      "name": "Devpost",
      "enabled": true
    }
  ],
  "check_interval_hours": 3,
  "settings": {
    "only_future_hackathons": true,
    "min_days_ahead": 0,
    "max_days_ahead": 90
  }
}
```

### Settings Explained

- **sources**: Enable/disable individual sources
- **check_interval_hours**: How often to check (reflected in cron schedule)
- **min_days_ahead**: Minimum days from now to include (0 = today)
- **max_days_ahead**: Maximum days ahead to include (90 = 3 months)

## How It Works

1. **Fetch**: Bot scrapes/fetches hackathons from all enabled sources
2. **Deduplicate**: Removes duplicate entries based on name
3. **Filter**: Only keeps hackathons within your date range
4. **Cache Check**: Compares against `hackathon_cache.json` to avoid reposts
5. **Notify**: Sends new hackathons to Discord with rich embeds
6. **Update Cache**: Saves posted hackathons to prevent duplicates

## Customizing the Schedule

To change how often the bot runs, edit `.github/workflows/hackathon-checker.yml`:

```yaml
on:
  schedule:
    - cron: '0 */3 * * *'  # Every 3 hours
```

Examples:
- Every hour: `'0 * * * *'`
- Every 6 hours: `'0 */6 * * *'`
- Every day at 9 AM: `'0 9 * * *'`
- Twice daily (9 AM and 9 PM): `'0 9,21 * * *'`

## Troubleshooting

### No hackathons being posted

- Check that `discord_webhook_url` is correct in `config.json`
- Verify webhook permissions in Discord
- Run locally with `python bot.py` to see detailed output

### Duplicate notifications

- Make sure `hackathon_cache.json` is being committed and pushed
- Check GitHub Actions logs for any errors during cache commits

### Website scraping fails

- Some websites may change their HTML structure
- Check the bot logs for error messages
- Open an issue if a source is consistently failing

## Discord Notification Format

Hackathon notifications include:
- **Title**: Hackathon name
- **Dates**: Start and end dates
- **Location**: City/country or "Online"
- **Type**: Online/In-Person/Hybrid badge
- **Link**: Direct link to registration
- **Source**: Which website it came from

## Contributing

Want to add more hackathon sources? Edit `bot.py` and add a new fetch function:

```python
def fetch_new_source() -> List[Dict]:
    # Your scraping logic
    return hackathons
```

Then add it to the sources list in `config.json` and the main fetch loop in `bot.py`.

## License

MIT License - Feel free to use and modify!

## Support

For issues or feature requests, please open an issue on GitHub.