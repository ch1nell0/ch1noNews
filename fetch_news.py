import os
import json
import urllib.request
import xml.etree.ElementTree as ET
from google import genai

CURRENTS_KEY = os.getenv("CURRENTS_API_KEY", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# Inizializza il client Gemini se la chiave è presente
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

SYSTEM_PROMPT = """
Sei un valutatore di notizie specializzato nel concetto di 'INCHINELLITO' (coniato dallo streamer Ch1nello).
'Inchinellito' (simile a 'nzallanuto) descrive una situazione di confusione estrema, assurdità caotica, eventi no-sense o persone/situazioni che non riescono a orientarsi o capire cosa stia accadendo.

Analizza il titolo fornito e assegna un punteggio da 1 a 9:
1 = Notizia del tutto normale, tragica, seria, politica o noiosa.
5 = Notizia leggermente bizzarra o insolita.
9 = NOTIZIA FULL INCHINELLITA: assurdità pura, caos totale, situazioni paradossali o no-sense.

Rispondi TASSATIVAMENTE ed ESCLUSIVAMENTE con un numero intero da 1 a 9. Nessun altro testo.
"""

def evaluate_inchinellito(title):
    if not client:
        return 5 # Punteggio di default se Gemini non è configurato
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Titolo notizia: '{title}'. Qual è il grado di inchinellitudine da 1 a 9?",
            config={'system_instruction': SYSTEM_PROMPT, 'temperature': 0.1}
        )
        score_str = response.text.strip()
        score = int(''.join(filter(str.isdigit, score_str)))
        return max(1, min(9, score))
    except Exception as e:
        print(f"Errore Gemini su '{title}': {e}")
        return 5

def fetch_rss(url, region, source_name):
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            root = ET.fromstring(response.read())
            for item in root.findall('.//item')[:12]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                if title and link:
                    articles.append({
                        "title": title,
                        "url": link,
                        "source": source_name,
                        "region": region
                    })
    except Exception as e:
        print(f"Errore RSS {source_name}: {e}")
    return articles

def fetch_currents():
    articles = []
    if not CURRENTS_KEY:
        return articles
    url = f"https://api.currentsapi.services/v1/latest-news?apiKey={CURRENTS_KEY}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for item in data.get('news', [])[:12]:
                articles.append({
                    "title": item.get('title', ''),
                    "url": item.get('url', ''),
                    "source": "Currents API",
                    "region": "GLOBAL"
                })
    except Exception as e:
        print(f"Errore Currents API: {e}")
    return articles

if __name__ == "__main__":
    raw_articles = []
    
    # Fonti Italia
    raw_articles.extend(fetch_rss('https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it', 'IT', 'Google News IT'))
    raw_articles.extend(fetch_rss('https://www.ilpost.it/feed/', 'IT', 'Il Post'))
    raw_articles.extend(fetch_rss('https://www.fanpage.it/feed/', 'IT', 'Fanpage'))

    # Fonti Globali / No-sense
    raw_articles.extend(fetch_rss('https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en', 'GLOBAL', 'Google News World'))
    raw_articles.extend(fetch_rss('https://theonion.com/feed/', 'GLOBAL', 'The Onion (Satire)'))
    raw_articles.extend(fetch_currents())

    # Valutazione con Gemini AI
    processed_articles = []
    for art in raw_articles:
        art["score"] = evaluate_inchinellito(art["title"])
        processed_articles.append(art)

    # Salva il file JSON
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(processed_articles, f, ensure_ascii=False, indent=2)
    print(f"Salvate {len(processed_articles)} notizie valutate con successo!")
