# CartPilot AI

> Tell AI what you need. Let it shop. You stay in control.
> **One voice. Multiple shopping platforms. One intelligent shopping assistant.**

React (Vite + Tailwind, your Google Stitch design tokens) + FastAPI + SQLAlchemy + Gemini + Channel3 + PayPal Sandbox.

```
cartpilot/
├── backend/     FastAPI server (API, database, AI, PayPal, voice commands)
│   ├── app/routers/    one file per API area (/api/auth, /api/chat, /api/cart ...)
│   ├── app/services/   the real logic (gemini, channel3, paypal, voice parser, analytics)
│   └── tests/          pytest suite
├── frontend/    React app (10 pages ported from your Stitch screens + login/register)
└── render.yaml  one-click Render deployment
```

## 1. Run it on Windows (VS Code)

You need **Python 3.11+** and **Node.js 20+** installed. Open the `cartpilot` folder in VS Code, then open **two terminals** (Terminal > New Terminal).

**Terminal 1 - backend**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Open `backend\.env` and set at least `JWT_SECRET` (generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Then:
```powershell
uvicorn app.main:app --reload
```
API docs (Swagger): http://127.0.0.1:8000/docs - health check: http://127.0.0.1:8000/api/health

**Terminal 2 - frontend**
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173, create an account, and the **System status** box (bottom-left) shows what is still missing.

> If PowerShell blocks `activate`, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 2. Credentials you need (all go in `backend/.env`)

| Feature | Variable(s) | Where to get it |
|---|---|---|
| Login | `JWT_SECRET` | generate locally (command above) |
| AI assistant | `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| Real products | `CHANNEL3_API_KEY` | https://trychannel3.com (docs: https://docs.trychannel3.com) |
| Dev products without a key | `PRODUCT_PROVIDER=fixtures` | built in - items are labelled **DEV FIXTURE** |
| Payments | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | https://developer.paypal.com > Apps & Credentials > Sandbox |
| Webhooks (optional) | `PAYPAL_WEBHOOK_ID` | create a webhook pointing to `https://YOUR-API/api/payments/webhook` |

**PayPal sandbox test:** create a *Sandbox personal* account in the PayPal developer dashboard, add products to the cart, click *Review & buy*, tick the confirmation box, and log in to the PayPal popup with the sandbox buyer.

## 3. Things you must know (honest limits)

* **Currency.** Channel3 prices are mostly USD and PayPal restricts INR, so checkout defaults to `PAYPAL_CURRENCY=USD`. A cart in another currency is refused - CartPilot never invents exchange rates. Rupee budgets ("under Rs 60,000") are only converted if you set `INR_PER_USD` yourself; otherwise you are told the budget could not be applied.
* **Channel3 coverage.** It indexes global retailers. Indian marketplace coverage is not guaranteed - check results with your key. Channel3 gives no ratings, so ratings show as "not listed".
* **Fulfilment.** CartPilot creates and verifies a real PayPal payment and a CartPilot order, but does *not* place orders with the merchants. Treat PayPal Sandbox as a demo of the payment flow.
* **Amazon / Flipkart / Myntra / AJIO.** No public API gives customers' order history, so there is no "connect your account". You import receipts (.txt/.eml/.html/.pdf) or type orders; CartPilot never asks for passwords and never scrapes. Gmail receipt import is **not implemented** (needs Google OAuth credentials) and the UI says so.
* **Voice.** Speech-to-text and speech output use your browser (Chrome/Edge best) and need internet - **not offline**. English and Hindi are the main targets; Kannada (`kn-IN`) depends on your browser/voices. Typed commands always work. Say "buy this" and you only get the order summary - nothing is charged until you tick the confirmation and approve in PayPal.
* **Database.** Tables are created automatically at startup (`create_all`). For future schema changes add Alembic.

## 4. Voice commands that work

"Open my cart", "Open shopping assistant", "Show my orders", "Go to my profile", "Open connected platforms", "Find wireless headphones under 2,000 rupees", "Compare these two laptops", "Show cheaper alternatives", "Add the second product to my cart", "Remove the headphones from my cart", "Show my total cart value", "Track my latest order", "Show my Amazon purchases", "How much did I spend this month?", "Explain why you recommended this product", and Hindi/Kannada equivalents such as "कार्ट खोलो". Shortcut: **Ctrl/Cmd + K**.

## 5. Tests
```powershell
cd backend
pytest
```
Covers registration/login/auth, cart, voice parsing and navigation, the "buy never charges" rule, PayPal create/approve/capture/verification/idempotency/amount-mismatch (PayPal and Gemini are faked, so no keys are needed), external-order duplicates, receipt parsing, and analytics.

## 6. GitHub
```powershell
git init
git add .
git commit -m "CartPilot AI"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/cartpilot.git
git push -u origin main
```
`.env` is git-ignored - never commit secrets.

## 7. Deploy on Render
1. Push to GitHub. In Render: **New > Blueprint** and choose the repo (`render.yaml`).
2. Fill the secret variables for `cartpilot-api` (Gemini, Channel3, PayPal, `ENCRYPTION_KEY`).
3. If Render gives your services different URLs, update `CORS_ORIGINS` and the `/api/*` rewrite destination in `render.yaml`.
4. Add the PayPal webhook URL `https://<api>/api/payments/webhook` and put its id in `PAYPAL_WEBHOOK_ID`.

## API overview
`/api/auth` `/api/users` `/api/chat` `/api/voice` `/api/products` `/api/recommendations` `/api/compare` `/api/cart` `/api/payments` `/api/orders` `/api/external-orders` `/api/integrations` `/api/analytics` - full Swagger at `/docs`.
