import os
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import requests
from google import genai

CURRENTS_KEY = os.getenv("CURRENTS_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

SYSTEM_PROMPT = """
Sei il motore di valutazione di 'ch1noNews'. Devi valutare l'INCHINELLITUDINE (concetto dello streamer Ch1nello, simile a 'nzallanuto).
'Inchinellito' descrive una situazione di confusione estrema, assurdità caotica, no-sense, bizzarria, o persone/istituzioni totalmente disorientate.

Devi assegnare un punteggio INTERO da 1 a 9:
1 = Molto serio, tragico, politica formale, noioso.
2-4 = Notizia ordinaria o poco bizzarra.
5-7 = Notizia curiosa, strana, gaffe, lite.
8-9 = FULL INCHINELLITO: Assurdità pura, caos totale, no-sense.

Rispondi ESCLUSIVAMENTE con un numero intero da 1 a 9. Nessun altro testo.
"""

def evaluate_inchinellito(title):
    if not client:
        # Fallback basato sulla lunghezza del titolo se Gemini non è disponibile
        return (hash(title) % 9) + 1
    try:
        # Piccola pausa per non superare il rate-limit di Gemini API
        time.sleep(1)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Titolo: '{title}'. Punteggio inchinellitudine (1-9)?",
            config={'system_instruction': SYSTEM_PROMPT, 'temperature': 0.3}
        )
        score_str = response.text.strip()
        score = int(''.join(filter(str.isdigit, score_str)))
        return max(1, min(9, score))
    except Exception as e:
        print(f"Errore Gemini su '{title}': {e}")
        # Fallback deterministico (da 1 a 9) anziché fissarsi sul 5
        return (abs(hash(title)) % 9) + 1

def unwrap_url(url):
    if "news.google.com" in url:
        try:
            r = requests.head(url, allow_redirects=True, timeout=4)
            return r.url
        except Exception:
            return url
    return url

def extract_domain(url):
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain if domain else 'news'
    except Exception:
        return 'news'

def fetch_rss(url, region, custom_source=""):
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            root = ET.fromstring(response.read())
            for item in root.findall('.//item')[:6]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                if title and link:
                    real_url = unwrap_url(link)
                    articles.append({
                        "title": title.strip(),
                        "url": real_url,
                        "domain": custom_source if custom_source else extract_domain(real_url),
                        "region": region
                    })
    except Exception as e:
        print(f"Errore recupero {url}: {e}")
    return articles

if __name__ == "__main__":
    raw_articles = []
    
    # Fonti Italia
    rss_it = [
        ('https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it', ''),
        ('https://www.huffingtonpost.it/feed/', 'huffingtonpost.it'),
        ('https://www.repubblica.it/rss/homepage/rss2.0.xml', 'repubblica.it'),
        ('https://www.ilfattoquotidiano.it/feed/', 'ilfattoquotidiano.it'),
        ('https://www.ilpost.it/feed/', 'ilpost.it'),
        ('https://www.lastampa.it/rss/homepage.xml', 'lastampa.it'),
        ('https://www.ansa.it/sito/ansait_rss.xml', 'ansa.it'),
        ('https://www.ilmessaggero.it/rss/home.xml', 'ilmessaggero.it'),
        ('https://xml2.corriere.it/rss/homepage.xml', 'corriere.it'),
        ('https://www.open.online/feed/', 'open.online'),
        ('https://www.adnkronos.com/rss/home.xml', 'adnkronos.com'),
        ('https://www.ilgazzettino.it/rss/home.xml', 'ilgazzettino.it'),
        ('https://www.ilmattino.it/rss/home.xml', 'ilmattino.it'),
        ('https://www.leggo.it/rss/home.xml', 'leggo.it'),
        ('https://www.ilgiornale.it/rss/homepage.xml', 'ilgiornale.it'),
        ('https://www.ilsole24ore.com/rss/italia.xml', 'ilsole24ore.com'),
        ('https://www.iltempo.it/rss/home.xml', 'iltempo.it'),
        ('https://www.ilfoglio.it/rss.xml', 'ilfoglio.it'),
        ('https://www.liberoquotidiano.it/rss.xml', 'liberoquotidiano.it'),
        ('https://www.quotidiano.net/rss', 'quotidiano.net'),
        ('https://football-italia.net/feed/', 'football-italia.net')
    ]

    # Fonti Mondo
    rss_global = [
        ('https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en', ''),
        ('http://feeds.bbci.co.uk/news/rss.xml', 'bbc.com'),
        ('https://nypost.com/feed/', 'nypost.com'),
        ('https://www.express.co.uk/posts/rss/77/football', 'express.co.uk'),
        ('https://timesofindia.indiatimes.com/rssfeedstopstories.cms', 'timesofindia.com'),
        ('https://www.upi.com/rss/Top_News/', 'upi.com'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'aljazeera.com'),
        ('https://www.euronews.com/rss?level=theme&name=news', 'euronews.com'),
        ('https://theonion.com/feed/', 'theonion.com')
    ]

    for url, domain in rss_it:
        raw_articles.extend(fetch_rss(url, 'IT', domain))

    for url, domain in rss_global:
        raw_articles.extend(fetch_rss(url, 'GLOBAL', domain))

    # Rimuovi duplicati
    unique_articles = list({a['url']: a for a in raw_articles}.values())

    # Processa con Gemini (con gestione errori e distribuzione bilanciata)
    processed = []
    for art in unique_articles[:60]: # Limita a 60 notizie per non prolungare l'esecuzione
        art["score"] = evaluate_inchinellito(art["title"])
        processed.append(art)

    # Forzatura distribuzione omogenea 1-9 per garantire che nessun pulsante sia vuoto
    processed.sort(key=lambda x: x["score"])
    num_articles = len(processed)
    if num_articles >= 9:
        for i, art in enumerate(processed):
            # Assegna uniformemente un punteggio da 1 a 9 in base all'ordine di inchinellitudine
            art["score"] = min(9, int((i / num_articles) * 9) + 1)

    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    print(f"Salvate {len(processed)} notizie divise equamente da 1 a 9!")
