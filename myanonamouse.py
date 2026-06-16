#VERSION: 1.0
#AUTHORS: lk
#SITE: https://www.myanonamouse.net

import os
import sys
import json
import time
import tempfile
import http.cookiejar
import urllib.request
import urllib.parse
import urllib.error

from novaprinter import prettyPrinter
from helpers import download_file

# --- USER CONFIGURATION ---
# Path to your MAM session cookie file (Netscape format).
# Obtain it by creating a session on MAM.
COOKIE_FILE = os.path.expanduser('~/mam.cookies')

# Custom tor[] query parameters applied to every search.
# Set a value to '' or [] to omit it.  See the MAM API docs for all options.
#   cat:        list of category IDs (["0"] = all)
#   main_cat:   list of main category IDs (13=AudioBooks, 14=E-Books, 15=Musicology, 16=Radio)
#   browse_lang: list of language IDs (e.g. [1] for English)
#   searchType: 'all', 'active', 'inactive', 'fl', 'fl-VIP', 'VIP', 'nVIP', 'nMeta'
#   searchIn:   'torrents', 'bookmarks', 'myReseed', 'allReseed'
#   sortType:   'default', 'titleAsc', 'titleDesc', 'sizeAsc', 'sizeDesc', 'seedersAsc', ...
#   startDate:  YYYY-MM-DD or unix timestamp (inclusive)
#   endDate:    YYYY-MM-DD or unix timestamp (exclusive)
#   hash:       hex-encoded torrent hash
#   id:         single torrent ID to return
TOR_PARAMS = {
    'cat': [],
    'main_cat': [],
    'browse_lang': [],
    'searchType': '',
    'searchIn': '',
    'sortType': '',
    'startDate': '',
    'endDate': '',
    'hash': '',
    'id': '',
}

# Fields to search in when tor[text] is provided.
# Options: title, author, narrator, tags, series, description, filenames, fileTypes
SRCH_IN = ['title', 'author', 'narrator', 'tags']

# Query-string parameter names recognized in the search box.
# List params accept comma-separated values (e.g. cat:13,108).
_QUERY_PARAM_KEYS = {
    'cat', 'main_cat', 'browse_lang', 'srchIn',
    'searchType', 'searchIn', 'sortType', 'startDate', 'endDate', 'hash', 'id',
}
# --------------------------


class myanonamouse(object):
    url = 'https://www.myanonamouse.net'
    name = 'MyAnonaMouse'
    supported_categories = {
        'all': '0',
        'books': '14',
        'music': '15',
    }

    def __init__(self):
        self.cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except Exception:
            pass
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    @staticmethod
    def _parse_query(what):
        overrides = {}
        tokens = what.split()
        remaining = []
        for token in tokens:
            if ':' in token:
                key, _, val = token.partition(':')
                if key in _QUERY_PARAM_KEYS:
                    overrides[key] = [v.strip() for v in val.split(',') if v.strip()] if key in {'cat', 'main_cat', 'browse_lang', 'srchIn'} else val.strip()
                    continue
            remaining.append(token)
        return ' '.join(remaining).strip(), overrides

    def search(self, what, cat='all'):
        search_text, overrides = self._parse_query(what)
        tor_params = dict(TOR_PARAMS)
        srch_in = list(SRCH_IN)
        for key, val in overrides.items():
            if key == 'srchIn':
                srch_in = val
            elif isinstance(val, list):
                tor_params[key] = val
            else:
                tor_params[key] = val

        params = {}
        qbt_cat_id = self.supported_categories.get(cat, '0')
        use_qbt_cat = cat != 'all'
        user_set_cat = 'cat' in overrides
        user_set_main = 'main_cat' in overrides

        if use_qbt_cat and not user_set_cat and not user_set_main:
            params['tor[main_cat][]'] = [qbt_cat_id]
        else:
            for key, val in tor_params.items():
                if isinstance(val, list):
                    if not val:
                        continue
                    if key == 'cat' and user_set_main:
                        continue
                    if key == 'main_cat' and use_qbt_cat and not user_set_main:
                        continue
                    params['tor[{}][]'.format(key)] = val
                elif val == '':
                    continue
                else:
                    params['tor[{}]'.format(key)] = val

        if search_text:
            params['tor[text]'] = search_text
            if srch_in:
                params['tor[srchIn][]'] = srch_in
        params['dlLink'] = ''

        step = 20
        start = 0
        max_results = 500
        seen = set()
        while len(seen) < max_results:
            params['tor[startNumber]'] = str(start)

            url = ('https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php?'
                   + urllib.parse.urlencode(params, doseq=True))

            try:
                req = urllib.request.Request(url)
                resp = self.opener.open(req, timeout=60)
                self._save_cookies()
                data = json.loads(resp.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    sys.stderr.write('MAM: cookie expired, refresh ~/mam.cookies\n')
                else:
                    sys.stderr.write('MAM HTTP error: {} {}\n'.format(e.code, e.reason))
                break
            except Exception as e:
                sys.stderr.write('MAM error: {}\n'.format(e))
                break

            items = data.get('data', [])
            if not items:
                break

            for item in items:
                name = (item.get('title') or item.get('name') or '').strip()
                if not name:
                    continue
                tid = str(item.get('id', ''))
                if tid in seen:
                    continue
                seen.add(tid)

                tags = []
                if item.get('free') not in ('0', '', None):
                    tags.append('FL')
                if item.get('vip') not in ('0', '', None):
                    tags.append('VIP')
                if tags:
                    name = '[{}] {}'.format(']['.join(tags), name)

                dl_hash = item.get('dl') or ''
                if dl_hash:
                    link = 'https://www.myanonamouse.net/tor/download.php/' + dl_hash
                else:
                    link = 'https://www.myanonamouse.net/tor/download.php?tid=' + tid

                res = {
                    'link': link,
                    'name': name,
                    'size': str(item.get('size', '0')),
                    'seeds': int(item.get('seeders', 0) or 0),
                    'leech': int(item.get('leechers', 0) or 0),
                    'engine_url': self.url,
                    'desc_link': 'https://www.myanonamouse.net/t/' + tid,
                }
                pub_date = item.get('added', '')
                if pub_date:
                    try:
                        dt = time.strptime(str(pub_date), '%Y-%m-%d %H:%M:%S')
                        res['pub_date'] = int(time.mktime(dt))
                    except (ValueError, OSError):
                        pass
                prettyPrinter(res)

            found = data.get('found', 0)
            start += step
            if found and start >= found:
                break

    def download_torrent(self, info):
        if '/download.php/' in info:
            print(download_file(info))
            return

        tid = info.split('tid=')[-1].split('&')[0]
        try:
            params = urllib.parse.urlencode({
                'tor[id]': tid,
                'dlLink': '',
            }, doseq=True)
            url = 'https://www.myanonamouse.net/tor/js/loadSearchJSONbasic.php?' + params
            req = urllib.request.Request(url)
            resp = self.opener.open(req, timeout=60)
            self._save_cookies()
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('data', [])
            if items:
                dl_hash = items[0].get('dl') or ''
                if dl_hash:
                    dl_url = 'https://www.myanonamouse.net/tor/download.php/' + dl_hash
                    print(download_file(dl_url))
                    return
        except Exception as e:
            sys.stderr.write('MAM: fetch dl hash failed: {}\n'.format(e))

    def _save_cookies(self):
        try:
            self.cookie_jar.save(COOKIE_FILE, ignore_discard=True, ignore_expires=True)
        except Exception:
            pass
