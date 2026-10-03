# 📊 E-commerce Analytics Dashboard — Plug & Play

**Turn your Shopify or WooCommerce order export into a clear, professional dashboard in under 5 minutes.
No coding. No database. No subscription. Your data never leaves your computer.**

Most store owners sit on a goldmine of order data but only see it as a spreadsheet. This dashboard reads
the CSV you already export from your store and instantly shows what actually matters: how much money you
really keep, what each customer costs you, how much you lose to refunds and where your best markets are.

---

## ✨ Features

### Four KPIs that tell you how healthy your store is

| KPI | What it tells you | Why it matters |
|---|---|---|
| **Net Revenue** | Gross sales minus refunds, excluding cancelled orders | The money you actually keep — not the vanity number on your store's homepage. |
| **Average CAC** | Average customer acquisition cost (organic orders with CAC = 0 are ignored) | Know whether your ads are profitable before your budget runs out. |
| **Return Rate (%)** | Refunds ÷ gross sales, excluding cancelled orders | Spot product, quality or expectation problems early. |
| **Average Order Value** | Gross sales ÷ non-cancelled orders | The fastest lever for growth: bundles, upsells and free-shipping thresholds. |

Every KPI has a built-in ⓘ tooltip explaining how it is calculated.

### Three interactive charts

- **Monthly Net Revenue vs Refunds** — see your growth trend and whether refunds are eating into it.
  Hover over any month to compare both figures side by side.
- **Orders by Status** — a donut chart with fixed traffic-light colours (green = completed,
  amber = pending, red = cancelled, grey = other) and the total number of orders in the centre.
- **Net Revenue by Region** — ranked bars so your best and worst markets are obvious at a glance.

All charts work in both light and dark mode, and you can zoom, pan and download them as images.

### Built for real-world, messy files

- Works with **comma or semicolon** separated files, and with Excel/Windows encodings.
- Understands **European and US number formats** (`1.234,56`, `1,234.56`) and currency symbols (`€ $ £`).
- Understands **ISO and day/month/year dates**, with or without time and timezone.
- Recognises common **Shopify and WooCommerce column names** (`date`, `order_id`, `country`, `total`,
  `refunds`, `status`…) and statuses in English or Spanish (including WooCommerce's `wc-completed` style).
- Missing optional columns? The dashboard fills in sensible defaults and tells you what was missing.
- A broken file never crashes the app — you get a clear message and the demo data instead.

### And more

- 🔒 **100% private and local.** The dashboard runs on your own computer. Nothing is uploaded to any server.
- 🌍 **English / Spanish** interface, switchable with one click.
- 💱 **€ / $ / £** currency display.
- 🗓️ Filters by **date range, region and order status**.
- 📥 Download the **filtered data** as CSV, or a **blank template** to fill in by hand.
- 🧪 **Demo Mode** with sample data, so you can explore everything before using your own file.

---

## 🚀 Quick Start (no technical knowledge needed)

### 1. Install Python (one time only)

1. Go to <https://www.python.org/downloads/> and download **Python 3.12**.
2. Run the installer.
   - **Windows:** on the first screen, **tick the box "Add Python to PATH"** (very important), then click
     **Install Now**.
   - **Mac:** just follow the installer steps.

### 2. Open a terminal in the dashboard folder

Unzip the product folder somewhere easy, for example your Desktop. Then:

- **Windows:** open the folder in File Explorer, click on the address bar at the top, type `cmd` and press
  **Enter**. A black window (the terminal) opens already inside the folder.
- **Mac:** open **Terminal** (press `Cmd + Space`, type *Terminal*, press **Enter**), type `cd ` (with a
  space after it), drag the folder from Finder into the Terminal window and press **Enter**.

### 3. Install the dashboard (one time only)

Copy this line into the terminal and press **Enter**:

```bash
pip install -r requirements.txt
```

Wait until it finishes (it can take a couple of minutes the first time).

### 4. Start the dashboard

```bash
streamlit run app.py
```

Your web browser will open the dashboard automatically. If it does not, open
<http://localhost:8501> in your browser.

To stop it, go back to the terminal and press `Ctrl + C`. Next time, you only need step 2 and step 4.

### 5. Use your own data

Export your orders as CSV from Shopify or WooCommerce and drag the file into the **"Upload your orders
CSV"** box in the left sidebar. That's it.

---

## 📄 Data Format

The dashboard expects one row per order. Only **Fecha** and **Ventas_Brutas** are required; every other
column is optional.

| Column | Required | Description | Example | Also recognised as |
|---|---|---|---|---|
| `Fecha` | ✅ | Order date | `2026-01-15` or `15/01/2026` | `date`, `created_at`, `order_date` |
| `ID_Pedido` | — | Order ID | `ORD-1001` | `order_id`, `order_number`, `name` |
| `Region` | — | Country or region | `Spain` | `country`, `shipping_country`, `billing_country` |
| `Ventas_Brutas` | ✅ | Gross order amount | `120.50` or `120,50 €` | `total`, `order_total`, `sales`, `revenue` |
| `Devoluciones` | — | Refunded amount | `20.00` | `refunds`, `refunded`, `total_refunded` |
| `CAC` | — | Acquisition cost of the customer | `15.20` | `customer_acquisition_cost`, `cpa`, `ad_spend` |
| `Estado_Pedido` | — | Order status | `Completado` / `completed` | `status`, `order_status`, `financial_status` |

Statuses are grouped into **Completed**, **Pending**, **Cancelled** and **Other**. Refunds are always
treated as positive values and can never be larger than the order amount.

Not sure how to start? Click **"Download CSV template"** in the sidebar and fill it in with Excel or
Google Sheets.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `pip` is not recognised | Use `python -m pip install -r requirements.txt` instead (on Mac, try `python3 -m pip ...`). |
| `streamlit` is not recognised | Use `python -m streamlit run app.py` instead (on Mac, `python3 -m streamlit run app.py`). |
| `python` is not recognised (Windows) | Python was installed without "Add Python to PATH". Run the installer again, choose **Modify**, and enable that option, or reinstall it ticking the box. |
| The browser did not open | Open <http://localhost:8501> manually. |
| "Address already in use" | The dashboard is already running in another terminal. Close it, or open <http://localhost:8501>. |
| My file shows an error | Check that it has a date column and a sales/total column. The message tells you exactly what is missing. |
| Some numbers look wrong | Make sure each row is one order (not one product line) and that amounts are in a single currency. |

---

## 📦 What's Included

| File | Purpose |
|---|---|
| `app.py` | The dashboard application |
| `dummy_data.csv` | 20 sample orders used in Demo Mode |
| `requirements.txt` | The exact, tested versions of the libraries the dashboard needs |
| `README.md` | This guide |

**Requirements:** Python 3.10 – 3.13 on Windows, macOS or Linux.

---

## 📜 License

This product is licensed for use by the purchaser in their own business(es). You may modify the code for
your own use. Redistribution or resale of the product, in whole or in part, is not permitted without
written permission from the author.
