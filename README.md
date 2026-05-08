# 🤖 Telegram Sentinel Bot

Telegram Sentinel Bot is a Python-based Telegram bot that monitors admin activity and automatically locks a group if a daily check-in message is not acknowledged within 24 hours. The admin can unlock the group at any time using a simple command.

## 🌟 Features

- **Daily Check-in**: Sends a daily verification message to a designated admin at a configurable time (default 21:00 UTC).
- **Automated Lockdown**: If the admin fails to confirm the message within 24 hours, the bot automatically restricts sending permissions for the entire group.
- **Manual Unlock**: The admin can restore full group access at any time using the `/reopen` command.
- **State Persistence**: Bot state is saved to a local JSON file, ensuring it remembers the last check-in status even after restarts.
- **Simple Deployment**: Ready-to-use Docker configuration and environment variable setup.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A Telegram Group where the bot will act as an administrator
- Your Telegram User ID (can be obtained from [@userinfobot](https://t.me/userinfobot))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ahmadrezagh671/telegram-sentinel-bot.git
   cd telegram-sentinel-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file or export the following variables:

   | Variable       | Description                                       | Default |
   |----------------|---------------------------------------------------|---------|
   | `BOT_TOKEN`    | Your Telegram bot token                           | Required|
   | `ADMIN_ID`     | User ID of the admin who will receive daily checks| Required|
   | `GROUP_ID`     | ID of the group to lock/unlock (must be integer) | Required|
   | `CHECK_HOUR`   | Hour of the day to send the daily check (0–23)    | `21`    |
   | `CHECK_MINUTE` | Minute of the hour for the daily check (0–59)     | `0`     |

4. **Run the bot**
   ```bash
   python main.py
   ```

### Docker Deployment

The repository includes a `Dockerfile` and `docker-compose.yml` for easy containerization.

```bash
docker-compose up -d
```

## 🛠️ Commands

| Command     | Description                                                  | Access |
|-------------|--------------------------------------------------------------|--------|
| `/reopen`   | Unlocks the group, restoring members' ability to send messages | Admin only |
| `/seen`     | Acknowledges the daily check message, preventing automatic lock | Admin only |

> **Note**: The bot will automatically lock the group if the `/seen` command is not received within 24 hours after a daily check is sent. The admin can always use `/reopen` to manually unlock.

## 📁 Project Structure

```
telegram-sentinel-bot/
├── main.py              # Core bot logic and handlers
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Docker Compose configuration
├── .gitignore           # Git ignore file
├── LICENSE              # MIT License
└── README.md            # Project documentation
```

## ⚙️ How It Works

1. The bot sends a daily check message to the specified admin at `CHECK_HOUR:CHECK_MINUTE` UTC.
2. The admin must reply with `/seen` within 24 hours.
3. If the admin fails to acknowledge, the bot revokes `can_send_messages` permission for all members of the group.
4. The admin can restore sending permissions at any time using the `/reopen` command.
5. The cycle repeats daily, with the bot only locking the group if the previous day's check was missed.

## 🧪 Example Usage

```
Admin receives:
✅ Daily check.
Please read this message within 24 hours.

[If admin does not respond within 24h]
⚠️ Group locked because daily check was not seen in 24h.

Admin can unlock by sending:
/reopen
```

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Ahmadreza GH**  
GitHub: [ahmadrezagh671](https://github.com/ahmadrezagh671)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/ahmadrezagh671/telegram-sentinel-bot/issues).

## ⭐ Show Your Support

If this project helped you, please give it a ⭐ on GitHub!