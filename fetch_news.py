import os
import json
import urllib.request
import xml.etree.ElementTree as ET

CURRENTS_KEY = os.getenv("CURRENTS_API_KEY", "")

# Parole chiave per calcolo euristico del divertimento/tragicità
SAD_WORDS = ['dead', 'death', 'war', 'killed', 'disaster', 'crash', 'murder', 'tragedy', 'morte', 'guerra', 'incidente', 'ucciso', 'tragedia', 'crisi', 'strage']
FUN_WORDS = ['funny', 'bizarre', 'viral', 'cat', 'dog', 'joke', 'win', 'lottery', 'meme', 'divertente', 'buffo', 'gatto', 'cane', 'vincita', 'curioso', 'festa', 'assurdo']

def calculate_fun_score(title):
    text = title.lower()
    score = 5
    for w in SAD_WORDS:
        if w in text: score -= 1.5
    for w in FUN_WORDS:
        if w in text: score += 1.5
    return max(1, min(9, round(score)))

def fetch_rss(url, region, source_name):
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:15]:
                title = item.find('title').text if item.find('title') is not None else ''
                link = item.find('link').text if item.find('link') is not None else ''
                if title and link:
                    articles.append({
                        "title": title,
                        "url": link,
                        "source": source_name,
                        "region": region,
                        "score": calculate_fun_score(title)
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
            for item in data.get('news', [])[:20]:
                articles.append({
                    "title": item.get('title', ''),
                    "url": item.get('url', ''),
                    "source": "Currents API",
                    "region": "GLOBAL",
                    "score": calculate_fun_score(item.get('title', '') + " " + item.get('description', ''))
                })
    except Exception as e:
        print(f"Errore Currents API: {e}")
    return articles

if __name__ == "__main__":
    all_news = []
    
    # Notizie Italia (Google News Italia + Fonti Nazionali)
    all_news.extend(fetch_rss('https://news.google.com/rss?hl=it&gl=IT&ceid=IT:it', 'IT', 'Google News Italia'))
    all_news.extend(fetch_rss('https://www.ilpost.it/feed/', 'IT', 'Il Post'))
    all_news.extend(fetch_rss('https://www.fanpage.it/feed/', 'IT', 'Fanpage'))

    # Notizie Globali (Google News Mondo + Currents API + Fonti Estere/Satira)
    all_news.extend(fetch_rss('https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en', 'GLOBAL', 'Google News World'))
    all_news.extend(fetch_rss('https://theonion.com/feed/', 'GLOBAL', 'The Onion (Satire)'))
    all_news.extend(fetch_currents())

    # Salva il file JSON per il frontend
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    print(f"Salvate {len(all_news)} notizie con successo!")
