import os
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
import ritter_api
import json
import asyncio

dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Determine data directory - use /app/data in Docker, current dir locally
DATA_DIR = Path("/app/data") if Path("/app/data").exists() else Path(".")
DATA_DIR.mkdir(exist_ok=True)

def load_connections() -> dict:
	connections_file = DATA_DIR / "connections.json"
	if connections_file.exists():
		with open(connections_file, "r") as f:
			return json.load(f)
	return {}

def save_connections(connections: dict) -> None:
	connections_file = DATA_DIR / "connections.json"
	with open(connections_file, "w") as f:
		json.dump(connections, f, indent=2)

def load_bot_config() -> dict:
	config_file = DATA_DIR / "bot_config.json"
	if config_file.exists():
		with open(config_file, "r") as f:
			return json.load(f)
	return {}

def save_bot_config(config: dict) -> None:
	config_file = DATA_DIR / "bot_config.json"
	with open(config_file, "w") as f:
		json.dump(config, f, indent=2)


bot_config = load_bot_config()
watched_channel_ids: set[int] = set(bot_config.get("watched_channel_ids", []))
watched_user_ids: set[int] = set(bot_config.get("watched_user_ids", []))

def append_connection(user_id: int, ritter_user_id: int, api_key: str) -> None:
	connections = load_connections()
	connections[str(user_id)] = {"ritter_user_id": ritter_user_id, "api_key": api_key}
	save_connections(connections)
	watched_user_ids.add(user_id)
	bot_config["watched_user_ids"] = sorted(watched_user_ids)
	save_bot_config(bot_config)

class MyBot(commands.Bot):
	def __init__(self) -> None:
		intents = discord.Intents.default()
		intents.message_content = True
		super().__init__(command_prefix="!", intents=intents)

	async def setup_hook(self) -> None:
		await asyncio.sleep(1)  # Wait a bit before syncing to avoid rate limits
		try:
			synced = await self.tree.sync()
			print(f"✅ Synced {len(synced)} slash command(s)")
		except Exception as e:
			print(f"❌ Failed to sync commands: {e}")


bot = MyBot()


@bot.event
async def on_ready() -> None:
	print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.tree.command(name="setapikey", description="Submit your API key")
async def setapikey(interaction: discord.Interaction, api_key: str) -> None:
	await interaction.response.defer(ephemeral=True)
	# Store the API key (consider using a secure storage method in production)
	user_id = interaction.user.id
	try:
		ritter_response = ritter_api.test_api_key(api_key)
		username, user_id = ritter_response.get("username"), ritter_response.get("user_id")
		await interaction.followup.send(
      f"API key validated successfully!\nConnected as {username}[{user_id}]", ephemeral=True)
		append_connection(interaction.user.id, user_id, api_key)

	except Exception as e:
		await interaction.followup.send(f"API key validation failed: {str(e)}", ephemeral=True)
		return


async def handle_target_channel_message(message: discord.Message) -> None:
	attachments = message.attachments
	if not attachments:
		return

	for i, attachment in enumerate(attachments):
		if attachment.content_type and (attachment.content_type.startswith("image/") or attachment.content_type == "application/pdf"):
			connections = load_connections()
			connection = connections.get(str(message.author.id))
			if not connection:
				await message.channel.send(
					f"{message.author.mention}, please set your API key using /setapikey before uploading receipts."
				)
				return

			api_key = connection["api_key"]
			image_path = f"temp_{attachment.id}_{attachment.filename}"
			await attachment.save(image_path)

			try:
				response = ritter_api.upload_receipt(
					api_key=api_key,
					image_path=image_path,
					payer_id=connection["ritter_user_id"],
				)
				if i == 0:
					await message.add_reaction("✅")
				await message.reply(f"Receipt {i+1}/{len(attachments)} uploaded successfully! ID: {response.get('id')}")
				print(f"Uploaded receipt for user {message.author.name} [{message.author.id}]: {response.get('id')}")
			except Exception as e:
				await message.add_reaction("❌")
				await message.reply(f"Failed to upload receipt {i+1}/{len(attachments)}: {str(e)}")
				print(f"Error uploading receipt for user {message.author.name} [{message.author.id}]: {str(e)}")
			finally:
				os.remove(image_path)
		else:
			print(f"Attachment {attachment.filename} is not an image or PDF, skipping.")


@bot.tree.command(name="registerchannel", description="Add this channel to the watched channel list")
async def registerchannel(interaction: discord.Interaction) -> None:
	channel = interaction.channel
	watching_before = channel.id in watched_channel_ids
	watched_channel_ids.add(channel.id)
	bot_config["watched_channel_ids"] = sorted(watched_channel_ids)
	save_bot_config(bot_config)
	message = f"Watching channel {channel.mention} ({channel.id})"
	if watching_before:
		message = f"Channel {channel.mention} ({channel.id}) is already registered"
		print(
			f"Register channel skipped (already registered): {channel.id} by {interaction.user} [{interaction.user.id}]"
		)
	else:
		print(
			f"Registered channel: {channel.id} by {interaction.user} [{interaction.user.id}]"
		)
	await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="deregisterchannel", description="Remove this channel from the watched channel list")
async def deregisterchannel(interaction: discord.Interaction) -> None:
	channel = interaction.channel
	if channel.id not in watched_channel_ids:
		print(
			f"Deregister channel skipped (not registered): {channel.id} by {interaction.user} [{interaction.user.id}]"
		)
		await interaction.response.send_message(
			f"Channel {channel.mention} ({channel.id}) is not registered", ephemeral=True
		)
		return

	watched_channel_ids.remove(channel.id)
	bot_config["watched_channel_ids"] = sorted(watched_channel_ids)
	save_bot_config(bot_config)
	print(
		f"Deregistered channel: {channel.id} by {interaction.user} [{interaction.user.id}]"
	)
	await interaction.response.send_message(
		f"Stopped watching channel {channel.mention} ({channel.id})", ephemeral=True
	)


@bot.event
async def on_message(message: discord.Message) -> None:
	if message.author.bot:
		return

	if message.channel.id in watched_channel_ids and message.author.id in watched_user_ids:
		await handle_target_channel_message(message)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction) -> None:
	await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")


if __name__ == "__main__":

	token = os.getenv("DISCORD_TOKEN")
	if not token:
		raise RuntimeError("DISCORD_TOKEN environment variable is not set")
	ritter_api.test_api_health()
	bot.run(token)
