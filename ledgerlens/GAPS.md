# LedgerLens — completion assessment

Assessed 01 Sep 2026 against the uploaded `Ledgerlens.zip`.
Every item below was verified by running the code, not by reading it.

## Verdict

The product works. The engine and the report are done and are good. What is
missing is not features — it is the shell around them: a correct HTML
document head, honesty about rows it drops, a ceiling on input size, and a
currency label. Roughly a day of work.

## How it was verified

- Engine extracted and driven in Node against the bundled samples and against
  synthetic edge cases (empty files, header-only, ragged rows, junk text,
  6 currency formats, 8 date formats, comma/semicolon/tab delimiters, BOM, CRLF,
  quoted embedded newlines).
- Full UI driven in headless Chromium through all three stages, twice: once via
  "Load the worked example", once by loading the two sample CSVs through the
  real file inputs. Google Fonts requests were blocked to confirm offline operation.
- Scaling measured at 3k / 5k / 10k / 20k rows per side.

Result: **zero JavaScript errors** in any run. Column auto-detection was correct
on both sample files. Receivables and payables directions both produce correctly
worded findings. No horizontal overflow at 390px or 1280px.

## Blockers — fix before this goes to a client

1. **No document head at all.** The file has no `<!doctype html>`, no
   `<meta charset>`, no `<meta name="viewport">`, no `<html lang>`.
   - Confirmed `document.compatMode === "BackCompat"` — the page renders in
     **quirks mode**, where box-model and table layout can differ from what was
     designed.
   - 42 lines contain raw UTF-8 em-dashes. Chrome guessed UTF-8 from `file://`,
     but with no declared charset another browser, or any HTTP server that sends
     a different default, renders them as mojibake in a client-facing report.
   - Without a viewport tag, phones lay the page out at ~980px and zoom out.

2. **Rows are dropped silently.** `normalise()` already counts them and returns
   `skipped`, but no UI code reads that value — `grep skipped` over the UI
   script returns nothing. A row with a missing amount, an unparseable figure,
   or too few columns just vanishes. Verified: a 4-row file yielded 2 items and
   `skipped: 2`, with nothing shown to the user. In a reconciliation tool,
   silently ignoring input is the one failure that destroys trust in the number.
   The value is computed — it only needs surfacing.

3. **No ceiling on input size, and the work is synchronous.** Matching is
   quadratic and runs on the main thread with no progress indicator:

   | Rows per side | Time |
   |---|---|
   | 3,000 | 1.0 s |
   | 5,000 | 4.0 s |
   | 10,000 | 17.1 s |
   | 20,000 | 71.9 s |

   The UI accepted a 120,000-row / 2.9 MB CSV without comment. Pressing
   Reconcile on that file freezes the tab long enough for Chrome to offer to
   kill the page. Needs a row-count warning at load and either a Web Worker or a
   progress indicator.

4. **Currency is never set.** The printed report header reads
   `ALL FIGURES IN` followed by an empty box. The field exists (`#curcode`) but
   is blank by default and nothing infers it from the data. A financial report
   that does not name its currency is not a finished report.

## Worth fixing

5. **No file download.** Exports are clipboard-only; the UI itself tells the
   user "Browser downloads are blocked on this page." A Blob + `download`
   attribute works from `file://` in current browsers and would remove a step
   the README currently has to apologise for.

6. **Excel is rejected with a misleading message.** Loading an `.xlsx` shows
   "No rows found in that file — is it a CSV with a header line?" It should
   detect the extension and say plainly that Excel files must be saved as CSV
   first — which is what the README already tells people.

7. **Default tolerance is 4%.** On the sample data this matched a 57.26
   discrepancy as a match (it was also raised as a note, so nothing is lost).
   4% is loose for reconciliation; consider defaulting to 1-2%. It is
   user-configurable, so this is a judgement call, not a defect.

8. **`parseAmount("12.3%")` returns 1230** — a percentage column mapped to an
   amount is read as money rather than rejected.

## Missing scaffolding

9. No test suite. The engine is a clean dependency-free UMD module that already
   runs under Node — the samples plus the edge cases above are a ready-made
   regression suite, and matching logic is exactly what should be pinned before
   anyone touches it again.
10. No LICENSE, no version number, no `package.json`.
11. `README.txt` should be `README.md`, and should state the supported input
    size once a limit exists.

## Explicitly not problems

- Reconciliation logic, exception classification, headline wording, coverage
  bar, method note, and print stylesheet are all complete and working.
- Offline operation is genuine: with both font hosts blocked the tool runs fully
  and only the typeface degrades, exactly as the README claims.
- Payables ("money going out") is fully implemented, with correctly reworded
  findings — not a stub.
- Group/batch payouts and split instalment matching both work on the samples.
