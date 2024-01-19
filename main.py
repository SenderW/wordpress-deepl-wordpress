import deepl
import requests
import base64
from datetime import datetime
import time

# Funktion zum Protokollieren
def log_to_file(source_id, dest_id):
    with open("protokoll.txt", "a") as file:
        file.write(f"{datetime.now().date()} UrsprungDE: {source_id}, ZielRU: {dest_id}\n")

# Funktion zum Überprüfen, ob ein Beitrag bereits übersetzt wurde
def is_already_translated(source_id):
    try:
        with open("protokoll.txt", "r") as file:
            for line in file:
                if f"UrsprungDE: {source_id}," in line:
                    return True
    except FileNotFoundError:
        pass
    return False

# Erstelle einen Übersetzer-Client mit dem DeepL-API-Schlüssel
translator = deepl.Translator("YOUR DEEPL API HERE")

# Konfiguration für die Quell-WordPress-Website
base_url = "Source Wordpress URL"
source_url = base_url + "/wp-json/wp/v2/posts"
source_auth = ('A USERNAME', 'Credentials')
source_auth_header = 'Basic ' + base64.b64encode(f"{source_auth[0]}:{source_auth[1]}".encode()).decode()

# Konfiguration für die Ziel-WordPress-Website
dest_base_url = "Destination Wordpress URL"
dest_wp_auth = ('A USERNAME', 'Credentials')
dest_wp_url = f"{dest_base_url}/wp-json/wp/v2/posts"
dest_media_url = f"{dest_base_url}/wp-json/wp/v2/media"
dest_auth_header = 'Basic ' + base64.b64encode(f"{dest_wp_auth[0]}:{dest_wp_auth[1]}".encode()).decode()

# Parameter für das Abrufen der jüngsten 20 veröffentlichten Posts
params = {
    'per_page': 20,
    'order': 'desc',
    'orderby': 'date',
    'status': 'publish'
}

# Artikel von der Quell-WordPress abrufen
response = requests.get(source_url, headers={'Authorization': source_auth_header}, params=params, verify=False)
posts = response.json()

for post in posts:
    post_id = post['id']

    if is_already_translated(post_id):
        print(f"Beitrag {post_id} wurde bereits übersetzt. Überspringe...")
        continue

    original_text = post['content']['rendered']
    original_title = post['title']['rendered']
    publish_date = post['date']
    image_url = post['_links']['wp:featuredmedia'][0]['href'] if 'wp:featuredmedia' in post['_links'] else None

    try:
        # Übersetzung des Inhalts und Titels mit DeepL
        translated_text = translator.translate_text(original_text, source_lang="DE", target_lang="RU", preserve_formatting=True).text
        translated_title = translator.translate_text(original_title, source_lang="DE", target_lang="RU", preserve_formatting=True).text

        # Artikel in der Ziel-WordPress hochladen
        new_post_data = {
            'title': translated_title,
            'content': translated_text,
            'status': 'publish',
            'date': publish_date,
            'categories': [673]  # Kategorie-ID
        }
        new_post_response = requests.post(dest_wp_url, headers={'Authorization': dest_auth_header}, json=new_post_data, timeout=50, verify=False)

        if new_post_response.status_code >= 200 and new_post_response.status_code < 300:
            new_post_id = new_post_response.json().get('id')
            if new_post_id:
                # Warte 20 Sekunden, bevor die URL überprüft wird
                time.sleep(20)
                check_url = f"{dest_base_url}/?p={new_post_id}"
                url_response = requests.get(check_url, verify=False)

                if url_response.status_code != 404:
                    log_to_file(post_id, new_post_id)

                    # Featured Image hochladen
                    if image_url:
                        image_response = requests.get(image_url, headers={'Authorization': source_auth_header}, timeout=50, verify=False)
                        image_data = image_response.content
                        image_upload_url = f"{dest_media_url}?post={new_post_id}"
                        image_headers = {
                            'Content-Disposition': 'attachment; filename=featured_image.jpg',
                            'Authorization': dest_auth_header,
                            'Content-Type': 'image/jpeg'
                        }
                        requests.post(image_upload_url, headers=image_headers, data=image_data, timeout=50, verify=False)
                else:
                    print(f"Fehler: Beitrag {new_post_id} konnte nicht verifiziert werden (404 gefunden).")
            else:
                print("Keine Post-ID in der Antwort gefunden.")
        else:
            print("Fehler beim Hochladen des Posts:", new_post_response.status_code)
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
        continue

print("Die jüngsten 20 Artikel wurden erfolgreich übertragen, übersetzt und mit dem ursprünglichen Veröffentlichungsdatum veröffentlicht.")
