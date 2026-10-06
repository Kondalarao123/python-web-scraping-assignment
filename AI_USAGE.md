# AI_USAGE.md

> **Candidate: please read and edit this file after you have run the project yourself.**
> Sections marked ✏️ must be completed with *your own* findings. You will be asked to explain
> the code in the interview, so do not submit anything here you have not checked.

## AI tools used
**Claude (Anthropic)** – used in a chat conversation.

## What it was used for
- Reading the assignment document and turning it into a project plan and folder structure
- Generating the first version of all code: scrapers, cleaning, validation, deduplication,
  pipeline, CLI, retry/backoff HTTP client
- Designing the common data model and the duplicate-key strategy
- Writing the unit tests and offline HTML fixtures
- Drafting README.md and this file

## Representative prompts
1. "I want to build a small project" … followed by sharing the assignment reference document
   (the Notion link did not load for the AI, so the text was pasted instead).
2. ✏️ Add the follow-up prompts you actually used (for example about pagination, duplicates,
   or anything you asked to be changed).

## Which parts were AI-assisted
All of the code, tests and documentation in this repository started as AI output.
✏️ State which files/functions you then modified yourself.

## Verification done
- 26 automated tests (`python -m pytest -q`) run against **offline HTML fixtures** that copy the
  structure of both sites: pagination, missing elements, malformed cards, failed pages, a source
  being down, retries/backoff, cleaning functions, validation rules, duplicate variants and a
  full end-to-end run checking the CSV and JSON outputs.
- The CLI was smoke-tested in an environment with no access to the target sites; it handled the
  failures gracefully (logged errors, wrote empty valid outputs, exited normally).
- **Not verified by the AI:** a live run against books.toscrape.com and quotes.toscrape.com, because
  those sites were unreachable from the AI's environment. The selectors were written from the
  sites' known structure and covered by fixtures that mimic it.
- ✏️ **Your live verification** – run `python main.py` and record here: the final counts from
  `summary_report.json`, a manual comparison of 5–10 records against the website (title, price,
  rating, category), and the total number of pages scraped for each source
  (the sites should have 50 book pages and 10 quote pages – confirm).

## Incorrect / incomplete AI suggestions found
✏️ Fill in after your review. Things worth checking yourself:
- Does the number of books/quotes collected match what the websites show?
- Are any book categories or descriptions empty, and why?
- Does the duplicate logic remove anything it shouldn't?
Record any bug you find and how you fixed it – even small ones – this is exactly what the
reviewers ask about ("Did AI-generated code create any problems?").

## Important changes made after reviewing AI output
✏️ List the changes you made (selectors, defaults, validation rules, naming, etc.).
