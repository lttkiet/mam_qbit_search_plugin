# MyAnonaMouse qBittorrent Search Plugin

Search [MyAnonaMouse.net](https://www.myanonamouse.net) torrents directly from qBittorrent.

## Prerequisites

The machine running qBittorrent must be registered on MAM to obtain a valid cookie. Follow the instructions in the MAM forum.

## Install

**Provide a session cookie**
Place the cookie somewhere qBittorrent have access.

**Modify the cookie path in [`myanonamouse.py`](myanonamouse.py)**

**Install in qBittorrent**: Search tab → Search engines… → Install a new one → [`myanonamouse.py`](myanonamouse.py).

## Usage

Type your query into qBittorrent's search box. The plugin fetches up to 500 results across multiple pages.

### Inline parameters

Any `tor[]` parameter can be overridden in the search box using `key:value` syntax:

| Example | Effect |
|---|---|
| `searchType:fl harry potter` | Freeleech only |
| `sortType:seedersDesc test` | Sort by seeders descending |
| `main_cat:13 mp3` | AudioBooks only |
| `cat:13,108` | Specific sub-categories |
| `browse_lang:1` | English only |
| `srchIn:title,author` | Search only in title and author |
| `startDate:2024-01-01` | From this date (inclusive) |
| `endDate:2024-12-31` | Until this date (exclusive) |

List values use commas (`cat:13,108`). Parameters are stripped from the search text automatically.

For details about parameter, visit the API document page.