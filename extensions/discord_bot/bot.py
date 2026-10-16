import os
import logging
import mimetypes
import tempfile
from logging.handlers import RotatingFileHandler
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

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = DATA_DIR / "bot.log"


def setup_logging() -> None:
	"""Log to stdout (docker logs) and to a rotating file in DATA_DIR."""
	formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
	console_handler = logging.StreamHandler()
	file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
	root = logging.getLogger()
	root.setLevel(LOG_LEVEL)
	for handler in (console_handler, file_handler):
		handler.setFormatter(formatter)
		root.addHandler(handler)
	# discord.py is very chatty on DEBUG
	logging.getLogger("discord").setLevel(logging.INFO)


setup_logging()
log = logging.getLogger("bot")

RECEIPT_MIME_PREFIXES = ("image/",)
RECEIPT_MIME_TYPES = {"application/pdf"}


def is_receipt_mime(mime: str | None) -> bool:
	return bool(mime) and (mime.startswith(RECEIPT_MIME_PREFIXES) or mime in RECEIPT_MIME_TYPES)


def receipt_content_type(attachment: discord.Attachment) -> str | None:
	"""Content type to upload with, or None if the attachment is not an image/PDF.

	Discord does not always set content_type (e.g. some mobile uploads),
	so fall back to guessing from the file extension.
	"""
	content_type = (attachment.content_type or "").split(";")[0].strip().lower()
	if is_receipt_mime(content_type):
		return content_type
	guessed, _ = mimetypes.guess_type(attachment.filename)
	if is_receipt_mime(guessed):
		log.info(
			"Attachment %s has content_type=%r, using %s guessed from filename",
			attachment.filename, attachment.content_type, guessed,
		)
		return guessed
	return None


def describe_message(message: discord.Message) -> str:
	return (
		f"message {message.id} from {message.author} [{message.author.id}] "
		f"in #{getattr(message.channel, 'name', '?')} [{message.channel.id}]"
	)


async def run_safely(coro, what: str) -> None:
	"""Await a Discord call (reply/reaction) without letting its failure abort the caller."""
	try:
		await coro
	except Exception:
		log.exception("Failed to %s", what)


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
			log.info("Synced %d slash command(s)", len(synced))
		except Exception:
			log.exception("Failed to sync slash commands")


bot = MyBot()


@bot.event
async def on_ready() -> None:
	log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
	log.info("Data dir: %s, log file: %s", DATA_DIR.resolve(), LOG_FILE.resolve())
	for channel_id in sorted(watched_channel_ids):
		channel = bot.get_channel(channel_id)
		if channel is None:
			log.warning("Watched channel %s is not visible to the bot (deleted or no access?)", channel_id)
		else:
			log.info("Watching channel #%s [%s] in %s", channel.name, channel_id, channel.guild)
	if not watched_channel_ids:
		log.warning("No watched channels - use /registerchannel in the receipt channel")
	connections = load_connections()
	log.info(
		"%d watched user(s), %d connection(s) with API key",
		len(watched_user_ids), len(connections),
	)
	for user_id in watched_user_ids:
		if str(user_id) not in connections:
			log.warning("Watched user %s has no stored API key connection", user_id)


@bot.event
async def on_disconnect() -> None:
	# messages posted while disconnected are NOT replayed and will not be processed
	log.warning("Disconnected from Discord gateway")


@bot.event
async def on_resumed() -> None:
	log.info("Resumed Discord gateway session")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
	command_name = interaction.command.name if interaction.command else "?"
	log.error(
		"Slash command /%s by %s [%s] failed", command_name, interaction.user, interaction.user.id,
		exc_info=error,
	)
	send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
	await run_safely(send(f"Command failed: {error}", ephemeral=True), "report slash command error")


@bot.tree.command(name="setapikey", description="Submit your API key")
async def setapikey(interaction: discord.Interaction, api_key: str) -> None:
	await interaction.response.defer(ephemeral=True)
	# Store the API key (consider using a secure storage method in production)
	log.info("/setapikey by %s [%s]", interaction.user, interaction.user.id)
	try:
		ritter_response = await asyncio.to_thread(ritter_api.test_api_key, api_key)
		username, user_id = ritter_response.get("username"), ritter_response.get("user_id")
		append_connection(interaction.user.id, user_id, api_key)
	except Exception as e:
		log.warning(
			"API key validation failed for %s [%s]: %s", interaction.user, interaction.user.id, e,
			exc_info=True,
		)
		await interaction.followup.send(f"API key validation failed: {str(e)}", ephemeral=True)
		return

	log.info("Connected %s [%s] to ritter user %s [%s]", interaction.user, interaction.user.id, username, user_id)
	await interaction.followup.send(
		f"API key validated successfully!\nConnected as {username}[{user_id}]", ephemeral=True)


async def handle_target_channel_message(message: discord.Message) -> None:
	attachments = message.attachments
	if not attachments:
		log.debug("No attachments in %s, ignoring", describe_message(message))
		return

	total = len(attachments)
	log.info(
		"Processing %s with %d attachment(s): %s",
		describe_message(message), total,
		", ".join(f"{a.filename} ({a.content_type}, {a.size} B)" for a in attachments),
	)

	connection = load_connections().get(str(message.author.id))
	if not connection:
		log.warning("No API key connection for %s, not uploading", describe_message(message))
		await run_safely(
			message.reply(f"{message.author.mention}, please set your API key using /setapikey before uploading receipts."),
			"ask user to set API key",
		)
		return

	uploaded = 0
	for i, attachment in enumerate(attachments):
		label = f"{i+1}/{total}"
		content_type = receipt_content_type(attachment)
		if content_type is None:
			log.warning(
				"Skipping attachment %s %s of %s: content_type=%r is not an image or PDF",
				label, attachment.filename, describe_message(message), attachment.content_type,
			)
			await run_safely(
				message.reply(f"Skipped attachment {label} ({attachment.filename}): not an image or PDF."),
				"report skipped attachment",
			)
			continue

		image_path = Path(tempfile.gettempdir()) / f"temp_{attachment.id}_{Path(attachment.filename).name}"
		try:
			await attachment.save(image_path)
			response = await asyncio.to_thread(
				ritter_api.upload_receipt,
				api_key=connection["api_key"],
				image_path=str(image_path),
				payer_id=connection["ritter_user_id"],
				content_type=content_type,
			)
		except Exception as e:
			log.exception(
				"Failed to upload attachment %s %s of %s", label, attachment.filename, describe_message(message),
			)
			await run_safely(message.add_reaction("❌"), "add ❌ reaction")
			await run_safely(
				message.reply(f"Failed to upload receipt {label}: {str(e)}"),
				"report upload failure",
			)
		else:
			uploaded += 1
			receipt_id = response.get("id")
			if receipt_id is None:
				log.warning("Upload response for %s has no receipt id: %r", attachment.filename, response)
			log.info(
				"Uploaded attachment %s %s of %s as receipt %s",
				label, attachment.filename, describe_message(message), receipt_id,
			)
			await run_safely(message.add_reaction("✅"), "add ✅ reaction")
			await run_safely(
				message.reply(f"Receipt {label} uploaded successfully! ID: {receipt_id}"),
				"confirm upload",
			)
		finally:
			image_path.unlink(missing_ok=True)

	log.info("Done with %s: %d/%d attachment(s) uploaded", describe_message(message), uploaded, total)


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
		log.info(
			"Register channel skipped (already registered): %s by %s [%s]",
			channel.id, interaction.user, interaction.user.id,
		)
	else:
		log.info("Registered channel: %s by %s [%s]", channel.id, interaction.user, interaction.user.id)
	await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="deregisterchannel", description="Remove this channel from the watched channel list")
async def deregisterchannel(interaction: discord.Interaction) -> None:
	channel = interaction.channel
	if channel.id not in watched_channel_ids:
		log.info(
			"Deregister channel skipped (not registered): %s by %s [%s]",
			channel.id, interaction.user, interaction.user.id,
		)
		await interaction.response.send_message(
			f"Channel {channel.mention} ({channel.id}) is not registered", ephemeral=True
		)
		return

	watched_channel_ids.remove(channel.id)
	bot_config["watched_channel_ids"] = sorted(watched_channel_ids)
	save_bot_config(bot_config)
	log.info("Deregistered channel: %s by %s [%s]", channel.id, interaction.user, interaction.user.id)
	await interaction.response.send_message(
		f"Stopped watching channel {channel.mention} ({channel.id})", ephemeral=True
	)


async def get_member(guild: discord.Guild, user_id: int) -> discord.Member | None:
	"""Member from cache, falling back to the API (members intent is not enabled, so the cache is sparse)."""
	member = guild.get_member(user_id)
	if member is not None:
		return member
	try:
		return await guild.fetch_member(user_id)
	except discord.NotFound:
		return None


@bot.tree.command(name="status", description="Show whether this channel is watched and which users can upload receipts here")
async def status(interaction: discord.Interaction) -> None:
	await interaction.response.defer(ephemeral=True)
	channel = interaction.channel
	log.info("/status in %s by %s [%s]", channel.id, interaction.user, interaction.user.id)

	lines = []
	if channel.id in watched_channel_ids:
		lines.append(f"✅ {channel.mention} is **watched** - receipts posted here are uploaded.")
	else:
		lines.append(f"❌ {channel.mention} is **not watched** - use /registerchannel to watch it.")
		parent_id = getattr(channel, "parent_id", None)
		if parent_id in watched_channel_ids:
			lines.append(f"(Parent channel <#{parent_id}> is watched, but threads are not.)")

	if interaction.guild is None:
		await interaction.followup.send("\n".join(lines), ephemeral=True)
		return

	connections = load_connections()
	ready_users = []
	for user_id in sorted(watched_user_ids):
		connection = connections.get(str(user_id))
		if not connection:
			continue
		try:
			member = await get_member(interaction.guild, user_id)
		except Exception:
			log.exception("Failed to look up member %s for /status", user_id)
			continue
		if member is None or not channel.permissions_for(member).read_messages:
			continue
		ready_users.append(f"- {member.mention} → ritter user {connection['ritter_user_id']}")

	if ready_users:
		lines.append(f"\n**Users with API key set up in this channel ({len(ready_users)}):**")
		lines.extend(ready_users)
	else:
		lines.append("\nNo users with an API key set up in this channel - use /setapikey.")

	await interaction.followup.send(
		"\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
	)


@bot.event
async def on_message(message: discord.Message) -> None:
	if message.author.bot:
		return

	if message.channel.id not in watched_channel_ids:
		parent_id = getattr(message.channel, "parent_id", None)
		if message.attachments and parent_id in watched_channel_ids:
			log.warning(
				"Ignoring %d attachment(s) in %s: posted in a thread of watched channel %s, threads are not watched",
				len(message.attachments), describe_message(message), parent_id,
			)
		return

	if message.author.id not in watched_user_ids:
		if message.attachments:
			log.warning(
				"Ignoring %d attachment(s) in %s: user is not a watched user (no /setapikey yet?)",
				len(message.attachments), describe_message(message),
			)
			await run_safely(
				message.reply(f"{message.author.mention}, please set your API key using /setapikey before uploading receipts."),
				"ask user to set API key",
			)
		return

	try:
		await handle_target_channel_message(message)
	except Exception as e:
		log.exception("Unexpected error while handling %s", describe_message(message))
		await run_safely(message.add_reaction("❌"), "add ❌ reaction")
		await run_safely(message.reply(f"Internal error while processing this message: {e}"), "report internal error")

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction) -> None:
	await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)}ms")


if __name__ == "__main__":

	token = os.getenv("DISCORD_TOKEN")
	if not token:
		log.critical("DISCORD_TOKEN environment variable is not set")
		raise RuntimeError("DISCORD_TOKEN environment variable is not set")
	try:
		ritter_api.test_api_health()
	except Exception:
		log.critical("ritter API health check failed (%s)", ritter_api.API_URL, exc_info=True)
		raise
	# log_handler=None: discord.py logs through the root logger configured above
	bot.run(token, log_handler=None)
