# Decisions

Each entry records what was decided, when, and why. Change a decision by adding a new entry that supersedes the old one.

## D1. Market: India (NSE, with BSE later)

- **Date:** 2026-10-18
- **Decided by:** owner
- **Detail:** v1 covers NSE-listed equities. BSE-only listings are out of scope until a later phase. Prices are in INR and the trading day is 09:15 to 15:30 IST.

## D2. Users: the owner and a few friends now, possibly public later

- **Date:** 2026-10-18
- **Decided by:** owner. Supersedes the earlier "personal tool" default.
- **Consequences:**
  - Each person gets their own login. Portfolios, theses and watchlists are private to each user from the start, so going public later is not a rebuild.
  - The app is hosted online so friends can reach it. The local Docker database stays for development.
  - Live prices: a broker's personal API is meant for the account holder's own use, so live prices should come from each user's own broker link, not the owner's feed shared to everyone. Until a friend links an account they see end-of-day prices.
  - No billing until a decision to go public.
- **Before going public or charging anyone:** take advice from a SEBI-registered professional on Research Analyst registration, and switch to a licensed market data vendor (NSE-authorised vendors exist for this) instead of NSE archive files and personal broker feeds.

## D8. Advice only, never places trades

- **Date:** 2026-10-18
- **Decided by:** owner
- **Detail:** The app suggests entries, stops and targets but never sends orders. Broker connections are used read-only (prices, and holdings if the user opts in). No order-placement code is written.

## D3. Live prices during market hours are required

- **Date:** 2026-10-18
- **Decided by:** owner ("I will need live prices everyday"). Supersedes the earlier end-of-day-only default.
- **Source:** a broker API with a WebSocket feed (Angel One SmartAPI, Upstox, Zerodha Kite Connect or Dhan). Which one depends on where the owner has an account. NSE's free archive files stay as the official end-of-day record and correct any gaps in the live feed.
- **Consequences:** the owner must enable API access on their broker account and keep the keys in the local `.env` file only. Broker logins expire daily, so a morning login step is needed (automatic where the broker supports TOTP). The machine running the feed must be on from 09:15 to 15:30 IST, so the feed will move to a small cloud server once the app is in daily use.

## D4. Universe: NIFTY 500 for analysis, all mainboard equities stored

- **Date:** 2026-10-18
- **Status:** default, confirm or override
- **Detail:** Prices are stored for every NSE equity in series EQ, BE and BZ (about 2,700 symbols a day). Scoring, picks and quality coverage checks use NIFTY 500 membership. Index membership is snapshotted by date so backtests can use the list as it was then.

## D5. Price source: NSE archive files

- **Date:** 2026-10-18
- **Detail:** See [data-sources.md](data-sources.md). Tested on 2026-10-18: bhavcopy (UDiFF from 2024-01-01, legacy format before), full bhavdata with delivery, index closes and index constituent lists all download without login.
- **Open:** A fundamentals source is still needed for Phase 1. A broker API is needed only when intraday arrives.

## D6. Split and bonus adjustment from NSE's corporate actions feed

- **Date:** 2026-10-18 (revised the same day)
- **First approach, dropped:** derive factors from the bhavcopy's previous close. Testing showed NSE does not adjust that field for splits (BUILDPRO's 10-to-2 split on 2026-10-08 showed as an 80% fall), so it cannot be used.
- **Current approach:** download NSE's corporate actions feed (`www.nseindia.com/api/corporates-corporateActions`) and parse the subject text. Splits, consolidations and bonuses give an exact factor. Demergers have no ratio in the notice, so their factor is the ex-date open over the previous close and each one is flagged as a warning for a manual look. Rights issues and dividends are not adjusted.
- **Detail:** Raw prices are stored unchanged. Factors go to `price_adjustments` and adjusted series are computed on read.
- **Risk:** the feed is an undocumented website API and could change. The parser is covered by tests, and a quality check flags any unexplained move beyond 20%.

## D7. Storage: Postgres 17 + TimescaleDB, plain SQL migrations

- **Date:** 2026-10-18
- **Detail:** Local database runs in Docker on port 5433. Migrations are numbered `.sql` files in `db/migrations`, applied by `stockai migrate`. The same files can be applied to Neon, Supabase or Timescale Cloud later.

## D9. Look and feel: style C "Friendly & bold"

- **Date:** 2026-10-18
- **Decided by:** owner, after comparing three styles (`design/fundamentals-styles.html`)
- **Detail:** Light background with a violet accent, rounded cards, Bricolage Grotesque headings, DM Sans text, DM Mono numbers. Every section opens with a plain-language question and a short "what this means" note.

## D10. Simple / Pro switch for the whole app

- **Date:** 2026-10-18
- **Decided by:** owner
- **Detail:** One switch in the top bar sets the detail level for every tab and is remembered per user. Simple mode uses plain questions as section titles, shows the most important numbers as tiles with a Good/Watch label and a sector comparison, and explains each section. Pro mode shows full tables with 5-year history, sector medians, trend sparklines and formulas. In both modes, an "i" button next to every number explains what it means, how it is calculated and what is good.

## D11. Downloads on research pages

- **Date:** 2026-10-18
- **Decided by:** owner
- **Detail:** Each research tab offers a PDF report, an Excel workbook (one sheet per table) and a CSV of key ratios. Prototype: `design/fundamentals-tab.html`.

## D12. Fundamental signals for short, medium and long term (Strong buy to Strong sell)

- **Date:** 2026-10-18
- **Decided by:** owner asked for a buy/sell signal at the top of the Fundamentals tab
- **Rule:** a 3 × 3 grid of business quality against price.
  - Quality: the fundamental score. High is 70 to 100, Medium 50 to 69, Low below 50.
  - Price vs fair value: Cheap is 15% or more below, Fair is within 15%, Expensive is 15% or more above.
  - Fair value is the average of the DCF value (default inputs) and the peer P/E value (sector P/E × next-year expected EPS).
  - High: Strong buy / Buy / Neutral. Medium: Buy / Neutral / Sell. Low: Neutral / Sell / Strong sell (Cheap / Fair / Expensive).
- **Scope:** fundamentals only, for a 1 to 3 year view. The Overview tab combines it with technicals for timing. The thresholds are starting values to be checked by backtests (blueprint feedback loop).
- **Revised 2026-10-18:** the owner asked for a signal per horizon. Each horizon uses different inputs:
  - **Short term (2 to 6 weeks), catalyst score 0 to 100:** last results vs estimates, 30-day forecast changes, news tone. Results due within 15 days cap the signal at Neutral.
  - **Medium term (1 to 6 months), momentum score 0 to 100:** expected profit growth for the next 4 quarters, 90-day forecast changes, order book cover, change in FII + MF holding.
  - **Long term (1 to 3 years):** the quality × price grid above.
  - Score bands for short and medium: 85+ Strong buy, 70 to 84 Buy, 40 to 69 Neutral, 25 to 39 Sell, below 25 Strong sell.
  - Open data question: analyst forecasts (estimates and revisions) need a data source. If none is affordable, medium term falls back to reported quarterly growth trends.

## D13. Simple mode stays as the plain-English version

- **Date:** 2026-10-18
- **Decided by:** owner
- **Detail:** A stricter "for every age" Simple mode was tried (no finance terms at all, traffic-light answers, report card, rank strips, everyday comparisons). The owner preferred the earlier version: plain-question titles, metric tiles with plain names, Good/Watch labels and sector comparisons, plus "what this means" notes. The earlier version is the live prototype (`design/fundamentals-tab.html`). The tried version is kept at `design/fundamentals-tab-simple-for-everyone.html` in case parts of it are useful later.

## D14. News tab contents

- **Date:** 2026-10-18
- **Prototype:** `design/news-tab.html`
- **Sections:** news mood (good/neutral/bad counts and a meter, 7 or 30 days), AI summary of what is moving the stock, upcoming events, a filterable news feed (type, good/bad, 7/30/90 days), hot topics, and insider/bulk/block trades. Pro adds a sentiment score, impact and price reaction per story, a news-vs-price chart and the exchange announcements table.
- **Mood score:** each story is tagged positive (+1), neutral (0) or negative (−1) and weighted by impact (High 3, Medium 2, Low 1). Score = weighted average, from −1 to +1. 0.2 and above reads "Mostly good", 0.5 and above "Very good", mirrored for bad.
- **Data needed:** exchange announcements (NSE corporate filings, already reachable), bulk/block deal files and insider disclosures (NSE), and a licensed news source. AI tags tone, impact and theme and writes the "what it means" line, with numbers checked against the source.
- **Downloads:** news digest PDF and news list CSV.
- **Added 2026-10-18, news effect on buy/sell:** a section after the mood shows each horizon's signal before and after the news, with the reason, plus upgrade and downgrade triggers. News weight in each signal: short-term catalyst score 40%, medium-term momentum score 15%, long term only screened for red flags (fraud, governance, promoter selling, rating downgrade). Every story carries an effect tag for short, medium and long term (helps ▲, hurts ▼, wait, no effect –).

## D15. Sector tab contents

- **Date:** 2026-10-18
- **Prototype:** `design/sector-tab.html`
- **Sections:** compact sector signal tiles (short, medium, long, tap for reason), ACME vs its sector vs NIFTY 50 (1M, 3M, 1Y), sector heatmap (box size = market cap, colour = return, 1D to 1Y), relative rotation chart with 5-week tails, leaders and laggards within the sector, sector valuation band, macro drivers (tailwinds and headwinds), sector news.
- **Sector signal rules (starting values):** short term follows rotation quadrant and breadth (Leading with more than 60% of stocks above the 50-day average = Buy); medium term follows sector earnings momentum (order books, profit growth, forecast changes); long term weighs growth against valuation (sector P/E above the 75th percentile of its 5-year range caps the signal at Neutral).
- **Real data plan:** sector returns and P/E come from NSE index closes already collected daily (`index_daily`); industry groups for stocks come from the NIFTY 500 constituent file (`instruments.industry`); rotation (RS-Ratio and RS-Momentum) is computed weekly against NIFTY 50.
- **Simple vs Pro:** Simple uses "hot and getting hotter / hot but cooling / cold / warming up" for the rotation quadrants and plain driver descriptions. Pro shows Leading/Weakening/Lagging/Improving, RS figures, sub-industries and full tables.
- **Revised 2026-10-18 after owner feedback ("confusing"):** Simple mode opens with a 30-second summary (three plain facts), replaces the rotation chart with four plain groups (strong and getting stronger, strong but slowing down, weak but picking up, weak and getting weaker), and uses a seven-step heatmap colour scale with a worded legend. The rotation chart is Pro-only, with a visible "How to read this chart" guide.
- **All tabs:** a one-line note under the tabs says which mode is on and what the other mode adds.

## D16. Technicals tab: default indicators in Simple, your own indicators in Pro

- **Date:** 2026-10-18
- **Decided by:** owner ("in simple some default indicators are used; in pro the user can choose indicators, play with candlesticks, mark lines, time frames, so the verdict will be different")
- **Prototype:** `design/technicals-tab.html`, built on TradingView Lightweight Charts 4.2 (free, Apache 2.0; its logo stays on the chart as attribution).
- **Simple:** daily area chart with the 50-day and 200-day averages, volume, RSI and MACD panes, the trade plan drawn as dashed lines and a breakout marker. The verdict always uses the default set: SMA 50, SMA 200, golden/death cross, support/resistance breakout, volume, RSI, MACD.
- **Pro:** candles, bars, Heikin-Ashi, line or area; daily, weekly or monthly candles; 1M to 3Y range; 15 indicators (SMA 20/50/200, EMA 9/21, golden cross, Bollinger, Supertrend, support/resistance, volume, RSI, MACD, Stochastic, ADX, OBV, ATR) and four presets; horizontal and trend line drawing saved per viewer. The verdict is recalculated from the chosen indicators on the chosen time frame and shown next to the Simple verdict.
- **Verdict rule:** each indicator votes +1, 0 or −1 and counts towards the horizons it suits (short, medium, long). Horizon score = average vote: 0.7 and above Strong buy, 0.25 Buy, above −0.25 Neutral, above −0.7 Sell, else Strong sell. Indicators without enough history on the chosen time frame are shown as "Not counted" and left out; a horizon with no votes shows "No data".
- **Trade plan:** entry zone, stop loss, two targets, a price ladder and (Pro) a position size calculator based on capital and risk per trade.
- **Revised 2026-10-18 to 2026-10-19, Pro becomes a chart workstation** (owner: "not all timeframes are there… I can't play in the charts… change the values… multiple support and resistance… save presets for other stocks"):
  - **Time frames:** 1, 2, 3, 5, 10, 15 and 30 minutes, 1, 2 and 4 hours, daily, weekly, monthly. Intraday candles need the live broker feed (D3). The prototype uses sample minute bars for the last 10 trading days. The horizon tiles relabel with the time frame (on minute charts: next few hours, 1 to 3 days, 1 to 2 weeks).
  - **Indicators:** a library of 60 in six groups (moving averages, bands and levels, momentum, volume, trend strength, volatility). Any indicator can be added more than once, every setting can be changed with ⚙ (out-of-range values are clamped to the allowed range), and each can be hidden or removed from the on-chart legend. Size-only indicators (ATR, volatility, choppiness) are shown but don't vote. The legend folds away and starts folded on phones.
  - **Drawing tools on the chart:** trend line, ray, horizontal and vertical line, zone, Fibonacci retracement, measure, text note, eraser, undo (on the chart you're viewing), clear, magnet snap and six colours. Drawings are kept per stock and per time frame; horizontal lines show on every time frame.
  - **Support and resistance:** found from swing highs and lows, merged within a sensitivity %, ranked by touches, with 1 to 6 levels each side and adjustable lookback and swing strength. When the price is at a new high (or low) there is no past level on that side, so the missing levels are projected from Fibonacci extensions (1.272, 1.618, 2.0) of the last swing. Projected levels are labelled, drawn dashed, and don't vote. Simple lists them in its levels card but keeps them off its chart, which already shows the trade-plan targets. The price scale stretches to keep the nearest floor and ceiling in view when they are within 8% of the price.
  - **Presets:** six built in (Default, Swing trading, Trend following, Momentum, Intraday, Ichimoku) plus up to 5 of your own, each saving indicators with their settings, chart type and time frame. One can be starred to load on every stock. When all 5 slots are full, a new preset replaces the oldest one except the starred one, and says which it replaced. The prototype keeps presets in the browser; the app will save them to the user's account.
  - **Sample stocks** ACME, Orbit and Nova (all made up) show presets and drawings carrying across stocks.
  - **Browser-tested 2026-10-19:** 3 stocks × 13 time frames × 6 chart types × 6 built-in presets, all 60 indicators at once, every drawing tool, presets, phone width. No script errors.
- **Revised 2026-10-23, indicators explain themselves and cross-check each other** (owner: "indicators must show how they support or resist each other… tell me why and what other indicators support this decision… hover in MACD should show all other values… a separate area with the last 5, 10 or 15 candles and the pattern"):
  - **Why:** every vote carries a plain reason with its numbers (for example "Bearish for the short term: RSI (72.1) is above 70, the overbought line"). It shows in the signal tiles, the readings table and a popover opened from the ▲/▼ chip next to each indicator on the chart legend and pane headers.
  - **Backed by / against:** for each voting indicator, the other indicators that vote the same way and the ones that vote the other way. Neutral votes neither back nor oppose.
  - **Indicator agreement section:** agreement % = confirming pairs ÷ (confirming + conflicting pairs), counting only pairs from different families (trend, momentum, price range, volume, trend strength, price levels), because two moving averages agreeing adds little. Up to 8 pair notes (4 in Simple), one per family pair, using the most telling indicator of each (RSI, MACD, BB, Stochastic, S/R, volume, ADX first). Each note is a confirm, conflict or context reading with a rule of thumb, for example "BB says stretched, MACD says still rising: in strong trends price can ride the upper band". "Overheated" wording is used only when an indicator is actually overbought. Pro adds a ✓/✕ matrix of every pair.
  - **Hover:** hovering any chart (price or any indicator pane) moves the crosshair on all of them and shows one read-out with the bar's OHLC and every active indicator's values at that bar.
  - **Recent candles section** (below the chart): last 5, 10 or 15 candles on any time frame (default: the chart's), drawn larger, with nearby support/resistance. Detects 27 patterns: doji (plain, dragonfly, gravestone), spinning top, hammer, hanging man, inverted hammer, shooting star, bullish/bearish marubozu, strong bullish/bearish candle, bullish/bearish engulfing, bullish/bearish harami, piercing line, dark cloud cover, tweezer top/bottom, inside bar, morning/evening star, three white soldiers, three black crows, three inside up/down.
    - Rules: body/shadow ratios against the bar's range and the 14-bar average body. The trend before a pattern is the 5-bar close change measured against the average range. Reversal patterns lose strength if they come after the "wrong" trend or no trend.
    - Context: backed by breaking or bouncing off a support/resistance level, volume ≥1.3× its 20-bar average, or RSI on the right side (below 40 for bullish, above 60 for bearish). Against: stopping under a ceiling or on a floor, volume below 0.7×, or RSI already overbought/oversold.
    - Confirmation: bullish is confirmed when the next candle closes above the pattern's last high and fails when it closes below its low (bearish mirrored). Unconfirmed and failed patterns lose strength.
    - Strength: Weak, Moderate or Strong. A candle that is part of a bigger pattern is shown only inside that pattern.
    - Lean of the window: recent patterns weighted most (failed ones ignored), plus the higher-highs/higher-lows structure.
  - **Browser-tested 2026-10-23:** all stocks, time frames, presets and 64 indicators at once with the new sections, hover sync across panes, phone width. No script errors.
- **Technicals tab approved by the owner on 2026-10-23.**

## D17. AI Verdict tab: one final call from all four tabs plus market mood

- **Date:** 2026-10-23
- **Decided by:** owner ("include all the verdicts (news, sector, fundamental, technical) and make a final verdict… also show other indexes that might affect the decision, like fear/greed, FOMO and foreign flows")
- **Prototype:** `design/ai-verdict-tab.html`
- **Pillars:** each tab's score per horizon, 0 to 100 (ACME: Fundamentals 53 / 70 / 76, Technicals 86 / 90 / 88, Sector 76 / 76 / 48, News 61 / 74 / 70).
- **Weights (starting values, to be checked by backtests):** short term Technicals 40, News 25, Sector 20, Fundamentals 15; medium term Fundamentals 30, Technicals 25, Sector 25, News 20; long term Fundamentals 55, Sector 20, Technicals 15, News 10. Pro users can change the weights for their own view; the standard verdict always uses these.
- **Market mood overlay:** each macro reading adds −2 to +2 points. The total applies in full to short term, half to medium term, and not at all to long term. Readings: Fear & Greed (our composite of 7: momentum vs 125-day average, breadth, VIX vs its 50-day average, put-call ratio, shares vs gold, FII flows, new highs vs lows), FOMO (our composite of 5: IPO subscription, small caps vs NIFTY, share of stocks at 52-week highs, retail share of F&O, new demat accounts), FII and DII net flows, India VIX, NIFTY put-call ratio, breadth, NIFTY trend, global cues, USD/INR, Brent crude, RBI repo and 10-year yield.
- **Rules:** final = weighted pillar score + mood points, then caps. Results within 15 days cap short term at Neutral (69). Bands as D12: 85+ Strong buy, 70 Buy, 40 Neutral, 25 Sell, below 25 Strong sell.
- **Conviction:** High when all 4 pillars are on the same side as the final call, Medium for 3, Low for 2 or fewer. It drops one step when the score is within 3 points of a band line.
- **ACME result:** short Neutral (72.8 − 2 = 70.8, capped at 69), medium Buy (77.3 − 1 = 76.3, high conviction), long Buy (71.6, low conviction: just over the line and Sector is Neutral).
- **Sections:**
  - Final verdict: compact tiles, a plan strip with entry, stop, targets and fair value.
  - How it's built: Pro adds contribution bars, weight sliders and the full matrix.
  - Market mood: a gauge and reading tiles; Pro adds the composite breakdowns and a table.
  - FII/DII flows over 10 sessions.
  - Bull vs bear case, written by AI from the figures on the four tabs, with every figure checked against them.
  - Your view vs the AI: compares your call and flags a stop tighter than one day's ATR, an R:R inflated by a tight stop or below 1.5, a target above fair value, an entry above the AI zone, and event risk. Prices apply to buy calls only (advice-only app, no short selling).
  - Triggers and event calendar.
- **Approved by the owner on 2026-10-23.**
- **Real data plan:** India VIX and NIFTY data from the index files already collected (D5); breadth and 52-week highs from bhavcopy; FII/DII from NSE's daily institutional activity report; put-call ratio from the NSE option chain; IPO subscription from NSE issue data; global markets, currency and commodities from a market data provider (to be chosen with the fundamentals source).

## D18. Overview tab: a one-page summary

- **Date:** 2026-10-23
- **Decided by:** owner ("about the stock, all verdicts, final verdict, key points of each verdict, target, stop loss, support/resistance, entry; one pager or max two; eye-catching, easy to read, not too much text")
- **Prototype:** `design/overview-tab.html`. About two screens on a laptop; stacks to one column on a phone.
- **Blocks:**
  - Dark verdict panel: one-line answer, Short / Medium / Long tiles with confidence dots, and quick chips (buy zone, exit, targets, market mood).
  - Company snapshot: one-sentence description, tags, 4 key stats against the sector, and a 52-week range bar.
  - 6-month price chart: entry zone shaded, exit, targets and the two nearest supports drawn and labelled, with labels spaced so they never overlap, and a hover read-out. Below it: entry, stop, T1, T2, reward to risk, then support and (projected) resistance chips.
  - All-verdicts grid: each tab's signal per horizon, market-mood points, and the final verdict, with a one-line agreement note.
  - Key points: one card per tab with its three signals and three bullets (two for, one against), each under about eight words.
- **Single source of truth:** every number repeats what the other tabs show (verdicts and scores from D17, levels from the Technicals trade plan and support/resistance, stats from Fundamentals). In the app, the Overview reads the same engine outputs; it calculates nothing of its own.
- **Downloads:** a one-page PDF summary (verdict table, chart image, levels, key points) and a CSV of verdicts and levels.
- **Revised 2026-10-23 after owner feedback ("data looks ok but not very eye catching; verdict doesn't show the default and selected verdict"):**
  - **New look:**
    - Gradient verdict panel with score rings (0 to 100) per horizon.
    - A risk-vs-reward bar from stop to T2, with the entry zone, now and T1 marked.
    - Your own call against the AI's, with risk flags.
    - Company card with a monogram and large stat numbers.
    - A full-colour verdict board.
    - A colour-coded price ladder beside the chart instead of labels on the chart.
    - A market-mood card.
    - Key-point cards with small score bars for each horizon.
  - **Default vs yours:** every pillar and the final verdict show Default (standard setup) next to Yours (the viewer's saved Pro choices: Technicals indicators and settings, AI Verdict weights), with = or ≠. The final "Yours" is recalculated with the same weights, mood points and caps. Your own call from "Your view vs AI" sits beside the AI's call for its horizon. In the prototype "Yours" is a sample (9 Pro indicators turn Technicals short term from Strong buy to Buy); in the app it is read from the user's account.
- **Approved by the owner on 2026-10-23.**

## D19. Blog tab: an AI-written story per stock, signals only

- **Date:** 2026-10-23
- **Decided by:** owner ("a blog of the selected stock with general market and news, about the company, recent news and the analysis; interesting to read; a button to publish; show all the previous published blogs" and "blog should never show buy/sell, it just suggests the signals bullish/bearish")
- **Prototype:** `design/blog-tab.html`
- **Signals only:** the blog never says buy or sell. Each time frame reads Very bullish, Bullish, Neutral, Bearish or Very bearish (same score bands as D17). Price levels are support, the level where the picture turns weak, and the next upside levels; there is no entry, stop loss, target or reward-to-risk. Reporting that funds or insiders bought or sold shares is allowed. A wording check blocks publishing if trade-call words appear (buy, sell, buy zone, stop loss, accumulate, book profit, entry point).
- **Today's draft:** written by AI from all five tabs after the close. Sections: the market this week (indices, mood, flows, macro and sector news), about the company, what's new, what our analysis says, what the signals say, what to watch, and the bottom line. Visuals in the story: market tiles, company facts, a news timeline, the 6-month price chart, the four-check scorecard, the three signals and a price-levels bar.
- **Options:** quick or full read, everyday or experienced readers (experienced adds a "by the numbers" box to each section), and which sections to include.
- **Editing:** every heading and paragraph can be edited in place. "Rewrite with AI" writes a fresh version from the same facts list, following the signals-only rule.
- **Checks before publishing:** every number in the text must match a figure on the other tabs (unmatched numbers are listed and need "publish anyway"), signal wording only, and a "not investment advice" note is always added.
- **Publish:** shows who can read it and saves a snapshot with the post (price and AI signals at that moment). Published posts are shared with everyone who opens the stock; the author or an editor can unpublish.
- **Published posts:** a switch at the top of the tab, filter by this stock or all stocks, newest first, each card showing the date, the three signals, read time and the price move since publishing. Posts open in a reader view.
- **Prototype storage:** posts are kept in the artifact's shared database (five sample posts for ACME, Orbit and Nova). The app will keep them in its own database per stock.
- **Approved by the owner on 2026-10-23.**

## D20. Time Machine tab: test one trade in thousands of simulated futures

- **Date:** 2026-10-23
- **Decided by:** owner ("simulate over 10,000 possibilities of the trade before I trade and give me a result")
- **Prototype:** `design/time-machine-tab.html`. The simulation really runs in the browser (10,000 futures in about a second).
- **Your trade:** buy price, stop loss, target, amount and maximum holding period (2 weeks to 3 months). Presets: AI plan with target 1, AI plan with target 2, your own call from the AI Verdict tab, or custom. Long trades only (no short selling, as D17). A buy price at or above today's price buys at the next open; a lower one is a limit order that fills only if the price dips to it within 10 trading days.
- **Engine (look forward):**
  - Each future is stitched from random 5-day stretches of the stock's own last 3 years of daily open, high, low and close moves (block bootstrap), so calm and volatile spells stay realistic.
  - The past trend is removed by default (fair test); "Assume it keeps rising like the last 3 years" is an option.
  - Results day: one of the stock's last 12 results-day moves is added to the first trading day after results (also de-meaned unless the trend is kept).
  - Fills: if the price opens past the stop or target, the trade exits at the open (gap). If both are touched in one day, the stop is assumed first.
  - Costs: 0.25% round trip by default, editable in Pro.
  - Pro: 5,000, 10,000 or 20,000 futures; calm, normal or stressed volatility; results jump on or off; move the stop to the buy price once halfway to target. Runs are seeded and repeatable, and "Try a fresh set of futures" re-rolls them.
- **Results:**
  - Headline win rate and average profit or loss after costs, with a rating: Favourable (≥ +1% a trade), Slight edge (≥ +0.2%), No clear edge, or Unfavourable (below −0.2%).
  - How trades ended: target, stop, gap through the stop, time ran out, never bought.
  - Average win and loss, bad case (1 in 20) and good case, days to target, and the win rate needed to break even.
  - Plain-English findings: a stop inside one normal day's move, results-day stop-outs and gap losses, unfilled orders, time-outs, and a better stop/target from the grid.
  - Charts: a price fan (half and 9 in 10 of futures, 60 sample paths coloured by outcome, hover read-out), a profit-and-loss histogram, and exit timing.
  - Pro adds a 7×7 what-if grid of stop vs target on the same futures (click to apply), a percentile table and the last 5 runs.
- **Look back:** every day in the 3 years that looked like today (a 60-day closing high on 1.5× normal volume, at least 10 sessions apart), replayed with the same % stop, target and holding period, listed with outcome and return. Small sample, shown as context.
- **Downloads:** a PDF report (results, fan chart, findings, look-back) and a CSV (summary, daily percentiles, what-if grid, look-back trades).
- **Real data plan:** NSE bhavcopy daily OHLCV (D1) replaces the sample history, and results dates and past reactions come from exchange filings. No new data source is needed.
- **Honesty rule:** the page always says results show what could happen if the future behaves like the past, not a forecast. With no trend assumed, stop and target choices alone cannot create an edge, and the grid says so.
- **Revised 2026-10-23 for beginners** (owner: "how will a layman understand these simulations and what it means"). Simple mode now:
  - **How it works in 3 steps:** look back at 3 years of real days, shuffle them like a deck of cards into 10,000 possible next few weeks, play your trade in each one and count. It can be hidden.
  - **Traffic-light answer first:** Good odds, Slightly in your favour, A close call or Poor odds, with one sentence covering how often it makes money (compared with a coin toss), whether wins or losses are bigger, the average result over many tries, and how often the trade never starts.
  - **"If 100 people placed this trade":** 100 figures, coloured by who made money, who lost and who never got to buy.
  - **"Your ₹1,00,000 at the end of the trade":** six plain bands (big loss, small loss, about even, small gain, big gain, never bought) instead of the histogram. The histogram, exit timing, grid and tables stay in Pro.
  - **"How to read this" note** on the price fan, with "Most likely" and "Possible" labels on the bands.
  - **Ideas to test, one click each:** for example a wider exit when the stop is inside one normal day's move, buying at today's price when the dip rarely comes, a longer hold, the grid's best pair, or the hopeful/fair trend switch. A message shows the win rate and average before → after.
  - **Look-back headline:** "In the past, this exact trade worked 7 out of 10 times", plus a note on why that can differ from the futures (a few real examples from a rising market vs a fair test).
- **Approved by the owner on 2026-10-23.**

## D21. Daily picks page: the day's best ideas from the whole market

- **Date:** 2026-10-24
- **Decided by:** owner ("add a daily picks page, based on latest news, sector analysis, technical and fundamental, market data")
- **Prototype:** `design/daily-picks.html`. This is an app-level page (Stocks · Daily picks · Watchlist · Portfolio), not a stock tab.
- **How picks are made (same engine as D17):**
  1. Universe: the NIFTY 500.
  2. Liquidity: 20-day average traded value of at least ₹10 Cr.
  3. Red-flag screen: rising promoter pledge, auditor resignation, SEBI or fraud news, rating downgrade, going-concern note.
  4. Pillar scores per horizon (fundamentals, technicals, sector, news) plus the market-mood overlay. Results within 15 days still cap short term at Neutral.
  5. Keep stocks with a final score of 70 or more and medium or high conviction.
  6. Rank by score, with at most 4 picks per horizon and at most 2 from one sector. While Fear & Greed is 65 or above, short-term picks are cut to 3.
  - Run every evening after the NSE files are published; picks are for the next trading day.
- **No analyst forecasts:** every input comes from exchange data, filings, index files and the licensed news feed, so each reason can be checked (see the 2026-10-23 realism review).
- **Page:**
  - **Hero:** pick count, a plain sentence on today's mood, and the selection funnel (500 → 431 → 409 → 402 → 61 → 27 → 10).
  - **Market backdrop:** six tiles (NIFTY, Fear & Greed, FII, DII, breadth, VIX) and a line on how the mood changed today's picks.
  - **Filters:** time frame (weeks, months, years), sector and company size.
  - **Pick cards:** horizon, price, score ring with Buy or Strong buy, a 2-month sparkline, four pillar bars, three reasons tagged by pillar, one "watch out" risk, and price levels. Short and medium picks show buy zone, exit, target 1 and target 2. Long picks show buy zone, the level where you'd rethink, and fair value.
  - **Card footer:** confidence dots, an event flag, Watch (saved to the watchlist), "Test it" (opens the Time Machine prefilled) and "Full analysis" (opens the stock's Overview).
  - **Pro:** pillar scores and weights, the mood points, reward to risk, average traded value, and a sortable table view.
- **Caution list:** sell-rated or red-flag stocks excluded from picks, each with its reason (falling trend, pledged shares, auditor exit).
- **How we pick:** the steps with counts, and the pillar weights per horizon.
- **Track record:** every closed pick since July, losers included. It shows target-hit and stop rates, average return against NIFTY over the same days, a monthly breakdown and the latest closed picks. Picks are measured from the next day's open with the Time Machine's exit rules.
- **Compliance note on the page:** these are research ideas from public data, not personal advice. Publishing stock picks to other people in India requires SEBI Research Analyst registration; personal use does not.
- **Sample picks:** Kestrel Bank, Vayu Power and Pelican Auto Parts (short term); ACME, Lumen Pharma, Tidewater Logistics and Teal Textiles (medium); Granite Cement, Coral Hospitals and Saffron Foods (long). All are made up, and their scores are computed with the D17 weights; ACME's 76.3 matches its AI Verdict tab.
- **Approved by the owner on 2026-10-24.**

## D22. Portfolio page: how good and how risky your holdings are today

- **Date:** 2026-10-24
- **Decided by:** owner ("the user's whole portfolio should show, and it should show how good or risky it is as of today's analysis")
- **Prototype:** `design/portfolio.html`, with a sample portfolio of 12 made-up holdings.
- **Holdings source:** read-only sync from INDmoney through the INDstocks API once connected; file upload and manual entry as fallbacks. The app never places orders.
- **Hero:**
  - Value, today's change, gain since bought and amount invested.
  - Two dials: **How good** (quality) and **How risky** (risk), plus a one-sentence summary.
- **How good:** each holding's AI final score (D17) weighted by its value, for weeks, months or years. Bands: 75+ Strong, 65 Good, 50 Okay, below 50 Weak. A bar shows the split of money by Buy, Hold/Neutral and Sell, and names the stocks in each.
- **How risky:** a 0 to 100 score made of points from nine checks. 60+ is High, 35 to 59 Moderate, below 35 Low.

| Check | Warn | Bad |
|---|---|---|
| Largest single holding | above 15% | above 20% |
| Largest sector | above 25% | above 35% |
| Red flags or Sell-rated (medium term) | any | above 10% of value |
| Holdings below the exit price you set | — | any |
| Beta | above 1.1 | above 1.3 |
| Hard to sell (traded value below ₹10 Cr a day) | above 10% of value | — |
| Small caps | above 25% | above 35% |
| Results within 15 days | above 25% of value | — |
| Number of holdings | fewer than 8 | — |

- **What to fix first:** the top five failed checks, ranked by points, each with a plain action and a link to the stock. For example: "Reduce ACME to about 15%: still rated Buy, this is about sizing".
- **Holdings table:**
  - Simple: value and weight, gain, today, AI view for months, notes.
  - Pro adds quantity, average cost, LTP, S/M/L scores, beta, average traded value and flags.
  - Sortable; a row expands to show why the AI rates it, with "Test in Time Machine" and "Full analysis".
- **Performance:** today's holdings against NIFTY 50 over 1M, 3M, 6M or 1Y, indexed to 100, with volatility, maximum drawdown, a bad month (1-in-20 21-day loss) and beta.
- **Allocation:** sector bars (Pro adds a NIFTY 500 weight tick) and a large/mid/small mix.
- **Stress tests:** market −10%, a 2020-style −25%, the largest sector −15%, small caps −20%, and results misses on holdings reporting soon. Each is shown in % and ₹.
- **Sample result:** value ₹9.78 lakh; How good 67 (Good); How risky 64 (High), driven by ACME at 23%, Capital goods at 43%, and two stops breached (Nova, Meera).
- **Added 2026-10-24, paper trading** (owner: "allow paper trading as well"):
  - **Two books, one page:** a switch between "Real portfolio" and "Paper trading". The paper book gets the same health check (How good, How risky, what to fix, allocation, stress tests). In the paper book, weights are shares of the whole account including cash, so ₹7 lakh in cash is not shown as concentration.
  - **Paper account:**
    - Starts with ₹10,00,000 of pretend money and can be reset.
    - Long only, no short selling, as D17.
    - Charges of 0.125% per side (STT, exchange fees, GST and stamp duty on delivery) and 0.05% slippage on market orders.
  - **Order ticket:** stock (★ marks today's Daily picks), buy or sell, quantity, market or limit, an optional exit price and target, and "why are you taking this trade?". The answer is saved to the journal.
  - **Pre-trade check:** shows order value, charges and cash after, plus:
    - the AI view, and whether the stock is on today's Daily picks
    - the stock's share of the account after the trade (warn above 15%) and its industry's share (above 30%)
    - no exit price set, or an exit closer than a normal day's move
    - reward to risk below 1.5
    - results within 15 days
    - hard to sell
    - a "Test in Time Machine" link
  - **Execution:**
    - Market orders fill at once.
    - Limit orders wait up to 10 trading days.
    - Exits and targets trigger automatically on the closing price, at the actual price, so a gap below the exit costs more than planned.
    - Pending orders can be cancelled.
  - **Journal and results:** every order with date, price, value, realised P&L, status and your reason. A results card shows the account's equity curve against the ₹10 lakh start, locked-in and open P&L, trades closed with win rate, and charges paid.
  - **Prototype vs app:** prices are frozen at the 16 Oct close, so a "Next trading day" button moves them by a random sample day to show trades playing out. In the app, paper trades use live INDstocks prices, are saved to the user's account, and are never sent to the broker.

## D23. Website stack, sign-in and roles

- **Date:** 2026-10-24
- **Decided by:** owner ("a server others can access", "only the admin can post a blog, other users can only read it", "go with PostgreSQL", "I have a Google Gemini API key", "exact copy of the prototypes, local server on my PC first")
- **Frontend:**
  - The approved prototype pages are served unchanged: `apps/web/pages` holds byte-identical copies of `design/*.html`.
  - The server wraps each page in the standard document shell and adds two scripts:
    - `claude-shim.js` provides the page features the artifacts got from claude.ai: downloads, user, the Blog's `db` and the AI `sample`.
    - `app.js` turns the tabs into links (adding Time Machine and Blog to the six pages designed before those tabs existed), adds the account menu, and shows blog readers only the published posts.
  - New pages in the same style: sign-in, invite/reset, admin, and a Watchlist placeholder.
  - React/Next.js (planned in the Mac README) is deferred: the plain pages need no rewrite or second runtime.
- **Backend:** Python FastAPI inside the existing engine package (`stockai.web`), started with `stockai serve`. Security headers are set on every response, including a content security policy that allows only Google Fonts and the two CDNs the pages use.
- **Database:** PostgreSQL 17 (MongoDB considered and declined: the engine and money logic need tables, joins and transactions). TimescaleDB is now optional: migrations use it where installed (the cloud server) and fall back to plain tables (local Windows).
- **Sign-in:**
  - Invite only. The admin creates a link (works once, expires in 7 days); the person sets their own name and password.
  - Passwords are hashed with Argon2id, at least 10 characters, with common passwords refused.
  - A session is a random token in an HttpOnly, SameSite=Lax cookie (Secure on HTTPS). Only its SHA-256 hash is stored, and it lasts 30 days.
  - Every change needs a CSRF token from `/api/me` as well as the cookie.
  - 5 failed sign-ins per email (or 30 per address) in 15 minutes locks sign-in for 15 minutes. Unknown emails take as long to check as wrong passwords.
  - The admin can make 24-hour password-reset links, switch accounts off (which ends their sessions) and change roles, but can't switch off or demote themselves. `stockai set-password` covers a forgotten admin password.
  - Sign-ins, invites, publishing and account changes are written to `audit_log`.
- **Roles:**
  - **admin:** everything, including publishing and unpublishing blog posts, invites, people, and Rewrite with AI.
  - **member:** reads everything, including the Blog's published posts, and can't write blog posts. Enforced by the server on every request (403), not only by hiding buttons; tests cover it.
- **AI:** Google Gemini through the owner's API key (`GEMINI_API_KEY`, model in `GEMINI_MODEL`), called from the server only and admin-only. The free templates stay the fallback when there's no key or Gemini fails. No paid Claude API.
- **Blog readers:** signed-in users only (default; switchable to public later).
- **Not yet:**
  - Real data in the pages (still ACME sample data).
  - Paper trades, starred stocks and the Simple/Pro choice saved to the account (still per browser).
  - The cloud server (HTTPS, nightly jobs, backups).
  - INDstocks live prices per user.
  - Email for self-service password resets.
