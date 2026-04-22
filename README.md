# MaxeySMP-Bot

Der offizielle Discord Bot für MaxeySMP.

## System-Anforderungen
Packages:
- discord.py 2.7+
- dotenv 0.9.9+
- jishaku 2.6.3+
- aiosqlite 0.22+
- simpleeval 1.0.7+
- aiohttp 3.13.5+
- mysql-connector-python 9.6+

Diese Packages sind in der requirements.txt vorhanden.
- Python 3.12+

## Installation

1. Repo in den Container-Root klonen
2. Environment-Datei im Container-Root erstellen:

```DISCORD_TOKEN=MainBotToken```

```DISCORD_BETA_TOKEN=BetaBotToken```

3. Installationsbefehl:
```bash 
pip install -r requirements.txt
```

## Ausführung

```bash
python main.py
```
