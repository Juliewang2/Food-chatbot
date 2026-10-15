# FoodChatBot – Pandeyji Eatery

An end-to-end food-ordering chatbot built with **Dialogflow ES**, a **FastAPI** backend and a **MySQL** database, embedded in a restaurant website.
Users can place new orders, add or remove items (including partial quantities, e.g. "remove one pizza"), complete the order and track its status through natural-language chat.

## Features

- **New order**: start an order in natural language ("new order", "I want 2 pizzas and 1 mango lassi").
- **Add items**: quantities are accumulated if the same dish is ordered again.
- **Remove items**: "remove pizza" removes the whole dish; "remove one pizza" only subtracts the given quantity.
- **Complete order**: saves the order to MySQL and returns the order id and total price.
- **Track order**: "track order 41" returns the current status from the database.
- **Web chat widget**: a custom chat window on the website, one independent session per browser tab.

## Architecture

```
Browser (frontend/home.html + chat.js)
        │  POST /chat
        ▼
FastAPI backend (backend/main.py) ──detectIntent──►  Dialogflow ES agent
        ▲                                                │
        └──────────── webhook: POST / ◄──────────────────┘
        │
        ▼
     MySQL (pandeyji_eatery)
```

- `GET /` serves the website; static files (css, js, images) are served from `frontend/`.
- `POST /chat` receives the user's message and forwards it to Dialogflow (`backend/dialogflow_client.py`).
- `POST /` is the Dialogflow webhook: it handles the order intents and reads/writes MySQL.
- ngrok exposes the local server over HTTPS so Dialogflow can reach the webhook.

## Project structure

```
FoodChatBot/
├── backend/
│   ├── main.py                 # FastAPI app: website, /chat, webhook
│   ├── dialogflow_client.py    # Calls Dialogflow detectIntent
│   ├── db_helper.py            # MySQL queries / stored procedures
│   ├── generic_helper.py       # Session id parsing, order formatting
│   ├── requirements.txt
│   └── dialogflow-key.json     # (not committed) Google service account key
├── frontend/
│   ├── home.html, styles.css, chat.js
│   └── banner.jpg, menu1-3.jpg
└── jiayi-chatbot-for-food-delivery.zip   # Dialogflow agent export
```

## Tech stack

Python · FastAPI · Uvicorn · Dialogflow ES (Google Cloud) · MySQL · HTML / CSS / JavaScript · ngrok

## Setup

### 1. Database
Import the dump `../db/pandeyji_eatery.sql` into MySQL (e.g. with MySQL Workbench).
Connection settings are read from environment variables (defaults in brackets):

| Variable      | Default            |
|---------------|--------------------|
| `DB_HOST`     | `localhost`        |
| `DB_USER`     | `root`             |
| `DB_PASSWORD` | `root`             |
| `DB_NAME`     | `pandeyji_eatery`  |

PowerShell example: `$env:DB_PASSWORD = "your_password"`

### 2. Dialogflow agent
1. In the Dialogflow ES console: ⚙ Settings → Export and Import → **Restore from zip** → `jiayi-chatbot-for-food-delivery.zip`.
2. Fulfillment → Webhook URL: your ngrok HTTPS URL (e.g. `https://<your-domain>.ngrok-free.dev`).

### 3. Google Cloud credentials
1. Google Cloud console → IAM & Admin → Service Accounts → create one with role **Dialogflow API Client**.
2. Keys → Add key → JSON, rename the file to `dialogflow-key.json` and put it in `backend/`.
3. If you use your own agent, change `PROJECT_ID` in `backend/dialogflow_client.py`.

> Never commit `dialogflow-key.json` – it is listed in `.gitignore`.

### 4. Run
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
In another terminal:
```bash
ngrok http --url=<your-domain>.ngrok-free.dev 8000
```
Open `https://<your-domain>.ngrok-free.dev`, click **Visit Site** on the ngrok notice, then click the 💬 button.

## Example conversation

```
> new order
Starting new order. Specify food items and quantities...
> 2 pizzas and 2 masala dosa
So far you have: 2 Pizza, 2 Masala Dosa. Do you need anything else?
> remove one pizza
Removed 1 Pizza from your order! Here is what is left in your order: 1 Pizza, 2 Masala Dosa
> that's it
Awesome. We have placed your order. Here is your order id #42. Your order total is ... which you can pay at the time of delivery!
```

## Notes

- In-progress orders are kept in memory, so they are lost when the server restarts.
- Make sure `pip` installs packages for the same Python that runs `uvicorn` (e.g. `py -3.13 -m pip install -r requirements.txt`).
