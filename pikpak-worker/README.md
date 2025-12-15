# PikPak Telegram Bot Worker

This project implements a Telegram Bot running on Cloudflare Workers that allows users to pay with **Telegram Stars** to download files using your PikPak account's quota.

## Features

- **Serverless**: Runs entirely on Cloudflare Workers.
- **Telegram Stars Payment**: Integrated payment flow (1 Star per task).
- **PikPak Integration**: Auto-submits magnet/HTTP links to PikPak.
- **TypeScript**: Written in strict TypeScript.

## Prerequisities

1.  **Cloudflare Account**: For deploying Workers.
2.  **Telegram Bot**: Create one via @BotFather.
3.  **Telegram Stars**: Enable payments in your bot via @BotFather (Select "Telegram Stars" as provider).
4.  **PikPak Account**: Username and Password.

## Setup

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

2.  **Configure Secrets**:
    You need to set sensitive environment variables. You can do this via the Cloudflare Dashboard (Settings -> Variables) or using `wrangler`:

    ```bash
    npx wrangler secret put TELEGRAM_BOT_TOKEN
    npx wrangler secret put PIKPAK_USERNAME
    npx wrangler secret put PIKPAK_PASSWORD
    ```

3.  **Setup KV Namespace** (Optional but recommended for state):
    ```bash
    npx wrangler kv:namespace create DB
    # Update wrangler.toml with the output ID
    ```

4.  **Deploy**:
    ```bash
    npx wrangler deploy
    ```

5.  **Set Telegram Webhook**:
    After deployment, get your worker URL (e.g., `https://pikpak-bot.your-name.workers.dev`) and set the webhook:
    ```bash
    curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://pikpak-bot.your-name.workers.dev"
    ```

## Usage

1.  User sends `/start` to the bot.
2.  User sends a magnet link or HTTP link.
3.  Bot replies with an Invoice for **1 Star**.
4.  User pays.
5.  Bot submits task to PikPak and replies with the result/download link.

## Note on Long-Running Tasks

Cloudflare Workers have a CPU time limit (usually 10ms-50ms) and wall-clock limit. Downloading large files happens on PikPak's side, but *waiting* for it to finish might take longer than a single Worker invocation allows.
This demo performs a quick poll (approx 6 seconds). For robust production usage, consider using **Cloudflare Cron Triggers** to periodically check task status in the background and notify the user via `sendMessage`.

## License

ISC
