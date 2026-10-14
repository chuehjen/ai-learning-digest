# AI Learning Digest Feed

Public, machine-readable AI learning briefings for an iPhone Shortcut. This repository contains public titles, learning plans, and source links only. **Never add contact information, personal notes, private documents, or API keys.**

## Files

- `daily.json`: the newest five-item AI news index. Headlines and links come from publisher feeds; the selection is automated and is **not an AI-written article summary**.
- `weekly.json`: the current Saturday's video/podcast plan, from an eight-week AI product learning sequence.
- `archive/daily/` and `archive/weekly/`: dated copies of published briefings.
- `latest.json`: a manual test payload. Scheduled delivery must never use it.

Each payload has `kind`, `date_bjt`, `generated_at_utc`, `message`, and `items`. The iPhone Shortcut must check `kind` and `date_bjt` before sending, so a delayed or failed update cannot resend an old briefing as today's.

## Schedule (Asia/Shanghai)

GitHub Actions builds `daily.json` at 07:17 every day and `weekly.json` at 08:17 every Saturday. The iPhone delivery times are 09:00 daily and 10:00 Saturday. GitHub Actions schedules are best effort; a delayed or dropped run should result in no message after the phone's freshness check.

To run locally: `python3 scripts/build_daily.py --dry-run` and `python3 scripts/build_weekly.py --dry-run`. Both scripts use the Python standard library. Their workflows can also be run manually from the GitHub Actions tab.

The iPhone can read each public file without a token through GitHub's contents API. In **Get Contents of URL**, set header `Accept: application/vnd.github.raw+json`. Example daily endpoint: `https://api.github.com/repos/chuehjen/ai-learning-digest/contents/daily.json`.
