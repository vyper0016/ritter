# Ritter Extensions

Integrations for uploading receipts to Ritter from external sources. Both use the `/receipts` API endpoint with `X-API-Key` header — generate a key from the user profile page.

## Discord Bot

[discord_bot/](discord_bot/) — Discord bot that auto-uploads receipt images posted in watched channels.

### Setup

1. Create bot at <https://discord.com/developers/applications>, copy token, enable **Message Content Intent**.
2. Configure env:
   ```bash
   cd discord_bot
   cp .env.example .env   # fill DISCORD_TOKEN and API_URL
   ```
3. Run:
   ```bash
   docker compose up -d
   ```
   Or locally: `pip install -r requirements.txt && python bot.py`

### Slash commands

| Command | Purpose |
|---------|---------|
| `/setapikey <key>` | Link Discord user to Ritter account via API key |
| `/registerchannel` | Watch current channel for receipt uploads |
| `/deregisterchannel` | Stop watching current channel |
| `/ping` | Latency check |

Once a user runs `/setapikey` and a channel is registered, any image/PDF posted by that user in that channel is uploaded to Ritter as a receipt.

State persists in `connections.json` and `bot_config.json` (volume `ritter-bot-data`).

## n8n Node

[n8n_node.json](n8n_node.json) — importable n8n HTTP Request node config for uploading receipts.

### Use

1. n8n → Workflow → import → paste `n8n_node.json`.
2. Edit the `X-API-Key` header — replace `YOUR_API_KEY` with your Ritter API key.
3. Update the URL if your Ritter instance is not on `http://localhost`.
4. Wire a binary input (e.g. from Email Trigger, Google Drive, Webhook) into the `data` field.

### Form fields

| Field | Description |
|-------|-------------|
| `image` | Binary file (image or PDF) |
| `payer_id` | Ritter user ID who paid |
| `participant_ids` | Comma-separated user IDs, or `-1` for all |
| `uploaded_through` | Source label (e.g. `n8n`) |
