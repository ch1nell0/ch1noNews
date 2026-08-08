import os
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import requests
from google import genai

CURRENTS_KEY = os.getenv("CURRENTS_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

SYSTEM_PROMPT = """
Sei un valutatore di notizie per il sito 'ch1noNews'. Il tuo unico scopo è valutare il grado di 'INCHINELLITUDINE' (concetto dello streamer Ch1nello, simile a 'nzallanuto).
'Inchinellito' descrive una situazione di confusione estrema, assurdità caotica, eventi no-sense, bizzarri, o persone che non riescono a comprendere ciò che sta accadendo.

Punteggio da 1 a 9:
1 = Notizia ordinaria, seriosa, tragica, politica rigida o noiosa.
5 = Notizia moderatamente insolita o bizzarra.
9 = FULL INCHINELLITA: assurdità pura, caos totale, situazioni no-sense o paradossali.

Rispondi TASSATIVAMENTE ed ESCLUSIVAMENTE con un solo numero intero da 1 a 9.
"""

def evaluate_inchinellito(title):
    if not client:
        return 5
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Titolo notizia: '{title}'. Grado di inchinellitudine (1-9)?",
            config={'system_instruction': SYSTEM_PROMPT, 'temperature': 0.2}
        )
        score_str = response.text.strip()
        score = int(''.join(filter(str.isdigit, score_str)))
        return max(1, min(9, score))
    except Exception as e:
        print(f"Errore Gemini su '{title}': {e}")
        return 5

# Funzione per risalire all'URL reale (sostituisce i link protetti di Google News)
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

def fetch_rss(url, region):
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            root = ET.fromstring(response.read())
            # Limite per fonte per garantire varietà
            for item in root.findall('.//item')[:6]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                if title and link:
                    real_url = unwrap_url(link)
                    articles.append({
                        "title": title,
                        "url": real_url,
                        "domain": extract_domain(real_url),
                        "region": region
                    })
    except Exception as e:
        print(f"Errore recupero RSS {url}: {e}")
    return articles

if __name__ == "__main__":
    raw_articles = []
    
    # FONTI ITALIA (Integrazione diretta + Google News IT)
    rss_sources_it = [
        'https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it',
        'https://www.ansa.it/sito/ansait_rss.xml',
        'https://www.ilpost.it/feed/',
        'https://www.fanpage.it/feed/',
        'https://xml2.corriere.it/rss/homepage.xml',
        'https://www.repubblica.it/rss/homepage/rss2.0.xml'
    ]
    for src in rss_sources_it:
        raw_articles.extend(fetch_rss(src, 'IT'))

    # FONTI MONDO (Google News Global + Testate internazionali)
    rss_sources_global = [
        'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en',
        'http://feeds.bbci.co.uk/news/rss.xml',
        'https://www.wired.com/feed/rss',
        'https://theonion.com/feed/' # Mantenuto in quota ridotta per non saturare
    ]
    for src in rss_sources_global:
        raw_articles.extend(fetch_rss(src, 'GLOBAL'))

    # Rimuovi duplicati in base all'URL
    unique_articles = {a['url']: a for a in raw_articles}.values()

    # Valutazione con Gemini AI
    processed_articles = []
    for art in unique_articles:
        art["score"] = evaluate_inchinellito(art["title"])
        processed_articles.append(art)

    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)
    print(f"Salvate {len(processed_articles)} notizie valutate con successo!")
