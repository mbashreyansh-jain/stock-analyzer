# Start here: your plain-English guide

You don't need to know any coding to use or direct this project. This guide explains what has been built, what each piece does, and the few things you will ever need to click.

---

## 1. The big picture

Think of the finished app as a restaurant.

| Restaurant | Your app | Status |
|---|---|---|
| Suppliers delivering fresh produce | The stock exchange (NSE) publishing prices every evening | ✅ Connected |
| The pantry where food is stored | The **database**, a neat filing cabinet of prices | ✅ Built |
| Staff who check deliveries for rotten items | **Quality checks** that flag strange or missing data | ✅ Built |
| The kitchen that cooks | The **analysis engine** (indicators, scores, verdicts) | ⏳ Phase 1 |
| The dining room customers see | The **screens** (Overview, Technicals, AI Verdict...) | ⏳ Phase 1 onward |

**Phase 0 built the suppliers, the pantry and the quality checks.** You can't "see" an app yet, the same way you can't eat in a restaurant that only has a stocked pantry. But every screen we build later depends on this foundation being right.

---

## 2. What we built in Phase 0

1. **A price database on your Mac.** It holds daily prices for every stock on NSE (about 3,000 companies) going back 3 years: open, high, low, close, volume, and **delivery %** (how many shares were actually taken home rather than traded within the day, which is a useful signal in India).
2. **An automatic downloader.** It fetches the official NSE files each trading day. It knows about holidays, so a missing file on Diwali isn't treated as an error.
3. **Split and bonus correction.** When a company splits its shares (for example 1 share of ₹1,300 becomes 5 shares of ₹260), the raw price looks like an 80% crash. The system reads the exchange's official list of splits, bonuses and demergers, and corrects the price history so charts and targets aren't fooled.
4. **The stock lists.** NIFTY 50, NIFTY NEXT 50 and NIFTY 500 members, with each company's industry. NIFTY 500 is the main list the AI will study.
5. **Index data.** Daily values for NIFTY, Bank NIFTY, IT and about 165 other indices, including their P/E ratios. This will power the Sector Analysis page.
6. **Daily quality checks.** Every day the system checks for impossible prices, missing NIFTY 500 stocks, unusually short files, and moves bigger than 20% that no split explains.
7. **Automatic self-tests.** There are 31 small checks that confirm the calculations are right. They run every time the code changes, like a smoke alarm for mistakes.
8. **The design colours.** The colour scheme from the blueprint is saved, ready for the screens.

---

## 3. Your step-by-step guide

### Every evening, or whenever you like: update the data

1. Open **Finder** and go to **Desktop → stcok**.
2. Double-click **`Update Stock Data.command`**.
3. A black window (Terminal) opens and shows three steps. Wait until it says **"All done"**. This usually takes under a minute. After a long break it catches up on every missed day automatically.
4. Close the window.

> **First time only:** your Mac may say the file "can't be opened because it is from an unidentified developer". If so, **right-click** the file, choose **Open**, then click **Open** again. You only need to do this once.

**Best time:** after 7 pm IST on a trading day. NSE publishes its files around 6 pm.

### Any time: check that everything is healthy

1. In the same folder, double-click **`Check Stock Data.command`**.
2. You'll see a short report like this:

```
Trading days loaded: 760  (2023-10-03 to 2026-10-16)
Stocks: 3001   Price rows: 1,950,000
Split/bonus adjustments: 412
Quality checks for 2026-10-16: info/adjustment_applied=1
```

**How to read it:**

| Line | Meaning | What you want to see |
|---|---|---|
| Trading days loaded | How many market days are stored | The second date should be the last trading day |
| Stocks / Price rows | Size of the database | Roughly 3,000 stocks |
| Split/bonus adjustments | Corporate actions corrected | Any number is fine |
| Quality checks | Problems found on the latest day | `clean` or only `info` is perfect. `warn` is worth a look. `error` means tell Claude |
| A line starting with FAILED | A day that couldn't be downloaded | Run Update again. If it repeats, tell Claude |

### If something looks wrong

You never need to fix it yourself. Open Claude Code in this folder and paste the report with a message like:

> "Here's my Check Stock Data report. Is anything wrong?"

---

## 4. How to work with Claude on this project

You're the **product owner**: you decide *what* the app should do, and Claude handles *how*. Useful things to say:

- "Explain what you just did in simple terms."
- "Show me RELIANCE's prices for the last 2 weeks."
- "Which NIFTY 500 stocks had a split this year?"
- "Start Phase 1." (the next stage, described below)
- "I don't like this colour or layout. Make it more like ___."
- "Save my work." (Claude will **commit** it, which is like a save point you can always go back to)

Claude will always ask before anything that costs money, sends anything outside your computer, or can't easily be undone.

---

## 5. Words you'll hear

| Word | Plain meaning |
|---|---|
| **Database** | An organised digital filing cabinet. Ours stores prices. |
| **Docker** | A free app that runs the database in a sealed box on your Mac. It needs to be open (the whale icon in the top bar) for the data tools to work. The scripts open it for you. |
| **Bhavcopy** | NSE's official end-of-day price sheet, published every trading day. |
| **Corporate action** | A company event that changes its shares: split, bonus, demerger, dividend, rights issue. |
| **Adjusted price** | Old prices corrected for splits and bonuses so they compare fairly with today's. |
| **Delivery %** | Share of traded quantity actually delivered to buyers. High delivery often signals genuine buying. |
| **Backfill** | Loading past history in one go. |
| **Engine** | The behind-the-scenes calculator. No screens, just maths. |
| **API** | A doorway the screens will use to ask the engine for data. |
| **Test** | A small automatic check that the maths gives the right answer. |
| **Commit** | A saved checkpoint of the project's files. |
| **GitHub** | A website that keeps an online copy of the project and runs the tests automatically. Optional for now. |
| **Phase** | A stage of the build plan. Each phase ends with something that works. |

---

## 6. What's in the folder

You don't need to open any of these. This is just so nothing looks mysterious.

| Item | What it is |
|---|---|
| `START-HERE.md` | This guide |
| `Update Stock Data.command` | Your "fetch today's prices" button |
| `Check Stock Data.command` | Your "is everything OK?" button |
| `services/engine` | The engine's code (the calculator) |
| `db` | Instructions for building the database tables |
| `packages/ui` | The app's colours and fonts |
| `docs/decisions.md` | A log of every decision we made and why |
| `docs/data-sources.md` | Where every piece of data comes from |
| `data` | Downloaded NSE files and logs (stays on your Mac only) |
| `README.md` | Technical notes for developers |

---

## 7. Decisions you can still change

We picked these sensible defaults so work could start. Tell Claude if you want any of them different.

| Question | Current choice | Why |
|---|---|---|
| Market | **India (NSE)** ✅ you chose this | |
| Who uses it? | **You and a few friends** ✅ you chose this. Maybe public later | Each person gets their own private login. Get SEBI advice before going public |
| Can it place trades? | **No, advice only** ✅ you chose this | It suggests, you decide and place orders yourself |
| Live prices during market hours? | **Yes** ✅ you chose this | Comes from your broker's API. Which broker is still to be decided |
| Which stocks to analyse | **NIFTY 500** (all ~3,000 stored) | Covers the liquid, tradeable market |
| Company financials (profit, debt, ratios) | **Not chosen yet** | Needed for Phase 1. Claude will suggest options and costs |

---

## 8. What comes next: Phase 1 (core research)

1. **Technical engine:** moving averages, RSI, MACD, Bollinger Bands, support and resistance, calculated for all NIFTY 500 stocks.
2. **Financial data:** choose a source for company results and ratios, then load it.
3. **Scoring and trade plans:** the 0 to 100 scores and the entry, stop loss and target rules from the blueprint.
4. **The first real screens:** search a stock, see its chart with selectable indicators, and see the Overview verdict page.

At the end of Phase 1 you'll be able to open the app in your browser, type a stock name, and see a verdict with entry, stop loss and targets.

> Nothing here is investment advice. The tool is for your own research.
