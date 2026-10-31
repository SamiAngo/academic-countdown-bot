# 🎓 Academic Countdown Bot

A personal Telegram bot that posts a daily countdown of my exams, assignments and projects to a Telegram channel, so I never lose track of a deadline.

It runs entirely on **GitHub Actions**: no server, no hosting, no cost. It keeps working while my computer is off.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/Runs%20on-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![Cost](https://img.shields.io/badge/Cost-%240-brightgreen)

---

## 📸 What it posts

Every morning, the channel gets a message like this:

```
🎓 ACADEMIC COUNTDOWN
🗓 Saturday, 31 October 2026
━━━━━━━━━━━━━━━━━━

📝 Math Final
🔴 3 days left · Tue, 3 Nov
▰▰▰▰▰▰▰▱▱▱ 70% of prep time used

❓ Stats Quiz
🟠 6 days left · Fri, 6 Nov
▰▰▰▰▱▱▱▱▱▱ 40% of prep time used

💻 Database Project ⭐
🟢 31 days left · Tue, 1 Dec
▰▱▱▱▱▱▱▱▱▱ 10% of prep time used

━━━━━━━━━━━━━━━━━━
📊 3 deadlines ahead · 2 within 7 days

💬 Small progress every day adds up to big results.
```

---

## ✨ Features

- **Daily countdown** posted to a Telegram channel every morning (Ethiopian time, UTC+3)
- **Add events from Telegram** by chatting with the bot. No editing code or files
- **Admin only:** the bot ignores everyone except the owner's Telegram user ID
- **Natural dates:** `Nov 15`, `15/11/2026`, `tomorrow`, `in 10 days`, `next friday`
- **Automatic categories** guessed from the event name (exam 📝, quiz ❓, assignment 📚, project 💻, presentation 🎤)
- **Urgency colours:** 🔴 ≤ 3 days · 🟠 ≤ 7 days · 🟡 ≤ 14 days · 🟢 later
- **Progress bar** showing how much preparation time has passed
- **⭐ Important** flag for high-priority events
- **Auto-cleanup** of events whose date has passed
- **Daily motivational quote**
- **Zero dependencies:** only Python's standard library

---

## ⚙️ How it works

There's no server listening for messages. Instead, GitHub Actions runs the bot once an hour:

```
         ┌──────────────── every hour ────────────────┐
         ▼                                            │
 1. Read new private messages from the admin          │
 2. Handle commands (/add, /done, /delete …)          │
 3. Remove past events                                │
 4. Once a day after 8 AM → post countdown to channel │
 5. Commit updated data/events.json back to the repo ─┘
```

Events are stored in `data/events.json`, so the repository itself acts as the database. Telegram holds incoming messages for 24 hours, so nothing is lost between runs.

**Trade-off:** because the bot only wakes up hourly, replies to commands can take up to an hour. For a deadline tracker that's fine, and it's what makes the project completely free.

---

## 📁 Project structure

```
academic-countdown-bot/
├── bot.py                        # All bot logic
├── data/
│   └── events.json               # Event storage (updated by the bot)
├── .github/
│   └── workflows/
│       └── countdown.yml         # Hourly schedule + auto-commit
└── README.md
```

---

## 🚀 Run your own copy

<details>
<summary><b>Setup guide (about 15 minutes)</b></summary>

### 1. Create a bot
Open **@BotFather** in Telegram, send `/newbot`, and copy the **token** it gives you.

### 2. Create a channel
Create a Telegram channel and add your bot as an **administrator** with permission to **post messages**.

### 3. Get the channel ID
- Public channel: its username, e.g. `@my_countdown`
- Private channel: post something in it, then open
  `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the `"chat":{"id":-100…}` number

### 4. Get your user ID
Message **@userinfobot** to get your numeric ID. Then open your bot and press **Start**.

### 5. Fork or copy this repository
Keep it **private**, since `events.json` contains your schedule.

### 6. Add secrets
**Settings → Secrets and variables → Actions → New repository secret**

| Secret       | Value                          |
| ------------ | ------------------------------ |
| `BOT_TOKEN`  | Token from @BotFather          |
| `CHANNEL_ID` | `@channel` or `-100…`          |
| `ADMIN_ID`   | Your Telegram user ID          |

### 7. Allow the workflow to save data
**Settings → Actions → General → Workflow permissions → Read and write permissions → Save**

### 8. Start it
**Actions → Academic Countdown Bot → Run workflow.** The first countdown appears in the channel within a minute.

</details>

---

## 📱 Usage

Commands are sent to the bot in a **private chat**:

| Command | Example | What it does |
| ------- | ------- | ------------ |
| `/add` | `/add Numerical Analysis Midterm \| Nov 15` | Add an event |
| `/add` | `/add Database Project \| 2026-12-01 \| project \| important` | Add with category and ⭐ |
| `/list` | `/list` | Show all events with their numbers |
| `/done` | `/done 3` | Mark event #3 as finished |
| `/delete` | `/delete 3` | Remove event #3 |
| `/post` | `/post` | Post the countdown now |
| `/help` | `/help` | Show all commands |

---

## 🛠 Customising

Settings at the top of `bot.py`:

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `POST_HOUR` | `8` | Hour of the daily post (24-hour clock) |
| `LOCAL_TZ` | UTC+3 | Timezone |
| `MAX_EVENTS_IN_POST` | `15` | Maximum events per post |
| `QUOTES` | 14 quotes | Daily motivation lines |
| `CATEGORY_EMOJI` | 6 categories | Categories and their emoji |

---

## 💰 Cost

**$0.** The Telegram Bot API is free, and hourly runs use roughly 750 of the 2,000 free GitHub Actions minutes that private repositories get each month.



---

## 📄 License

Free to use and modify for personal projects.
