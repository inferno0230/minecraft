import threading
import subprocess
import telegram
import time
import psutil
import requests
from telegram.ext import CommandHandler, Updater, MessageHandler, Filters

# Define Minecraft server command
server_command = ['java', '-Xmx20G', '-Xms1G', '-jar', 'server.jar', 'nogui']

# Read Telegram bot token from file
with open('api_key.txt', 'r') as f:
    bot_token = f.read().strip()

# Read pastebin API key from file
with open('pastebin_api_key.txt', 'r') as f:
    pastebin_api_key = f.read().strip()

# Define global variable for server process
process = None

def run_bash(update, context):
    message = update.message
    # Get the input after the "/bash" command
    command = message.text.split('/bash ', 1)[1]
    try:
        # Execute the command in a new bash process
        result = subprocess.check_output(['bash', '-c', command])
        # Send the output back to the user
        if len(result) > 4000:
            # Upload the output to a pastebin and send the link back to the user
            data = {'api_dev_key': pastebin_api_key, 'api_option': 'paste', 'api_paste_code': result}
            response = requests.post('https://pastebin.com/api/api_post.php', data=data)
            message.reply_text(f'The output is too long to display. Here is a pastebin link: {response.text}')
        else:
            message.reply_text(result.decode('utf-8'))
    except Exception as e:
        # If there was an error, send it back to the user
        message.reply_text(str(e))

# Define function to start Minecraft server
def start_server(update, context):
    global process

    # Start server process and redirect output to PIPE
    process = subprocess.Popen(server_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Define function to continuously read server output and send it to the chat
    def send_output():
        accumulated_message = ""
        start_time = time.time()
        skip_messages = True
        while True:
            line = process.stdout.readline()
            if not line:
                break
            message = line.decode().strip()
            if skip_messages and time.time() - start_time < 15:
                continue
            skip_messages = False
            accumulated_message += message + "\n"
            context.bot.send_message(chat_id=update.effective_chat.id, text=accumulated_message)
            accumulated_message = ""

    # Start thread to continuously read server output and send it to the chat
    thread = threading.Thread(target=send_output)
    thread.start()


# Define function to stop Minecraft server
def stop_server():
    process.stdin.write('stop\n'.encode())
    process.stdin.flush()
    process.wait()

# Define function to check Minecraft server status
def check_server_status():
    try:
        process.stdin.write('list\n'.encode())
        process.stdin.flush()
        process.stdout.readline()
        status = process.stdout.readline().decode().strip()
        return status
    except:
        return 'Server is offline'

def start_bot(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Bot initiated, use /help for help')

def stop_bot(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Stopped bot successfully')
    updater.stop()

def turn_on(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Booting up server, this make take about 10-15 seconds, use /serverstatus to check status after 15s')
    start_server(update, context)

def turn_off(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Minecraft server turning off')
    stop_server()

def list_commands(update, context):
    commands = ['/start - Start the bot',
                '/help - Show available commands',
                '/turnon - Turn on the Minecraft server',
                '/turnoff - Turn off the Minecraft server',
                '/serverstatus - Check the status of the Minecraft server',
                '/systemstatus - Check the status of the server',
                '/status - See system resource status']
    message = '\n'.join(commands)
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def server_status(update, context):
    status = check_server_status()
    context.bot.send_message(chat_id=update.effective_chat.id, text=status)

def systemstatus(update, context):
    cpu_percent = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    message = f"CPU usage: {cpu_percent}%\nRAM usage: {mem.percent}%"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def unknown_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Sorry, I did not understand that command.')

# Set up system status checking thread
def system_status_thread():
    while True:
        cpu_percent = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        message = f"CPU usage: {cpu_percent}%\nRAM usage: {mem.percent}%"
        for chat_id in chat_ids:
            bot.send_message(chat_id=chat_id, text=message)
        time.sleep(60) # wait 60 seconds before checking again

# Set up Telegram bot
updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher

# Add Telegram command handlers
dispatcher.add_handler(CommandHandler('start', start_bot))
dispatcher.add_handler(CommandHandler('stop', stop_bot))
dispatcher.add_handler(CommandHandler('help', list_commands))
dispatcher.add_handler(CommandHandler('turnon', turn_on))
dispatcher.add_handler(CommandHandler('turnoff', turn_off))
dispatcher.add_handler(CommandHandler('serverstatus', server_status))
dispatcher.add_handler(CommandHandler('systemstatus', systemstatus))
updater.dispatcher.add_handler(CommandHandler('bash', run_bash))
dispatcher.add_handler(MessageHandler(Filters.command & ~Filters.all, unknown_command))

# Start Telegram bot
updater.start_polling()

# Start system status checking thread
bot = telegram.Bot(token=bot_token)
chat_ids = [chat_id for chat_id in updater.dispatcher.chat_data.keys()]
system_status_thread = threading.Thread(target=system_status_thread)
system_status_thread.start()
