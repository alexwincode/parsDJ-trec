import json
import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# 1. Загружаем первые 5 треков
try:
    with open("tracks.json", "r", encoding="utf-8") as f:
        all_tracks = json.load(f)
        test_tracks = all_tracks[:5]
except FileNotFoundError:
    print("Ошибка: Сначала запустите первый скрипт, чтобы создать tracks.json!")
    exit()

ua = UserAgent()
print(f"=== ЗАПУСК УЛЬТРА-БЫСТРОГО ТЕСТА (БЕЗ БРАУЗЕРА) ===")

for index, track in enumerate(test_tracks, start=1):
    url = track.get("track_page_url")
    print(f"\n--------------------------------------------------")
    print(f"Трек [{index}/5]: {track.get('artist')} - {track.get('song')}")
    
    if not url:
        print("Результат: Ссылка на страницу отсутствует!")
        continue

    # Безопасный запрос с динамическим User-Agent
    headers = {"User-Agent": ua.random}
    
    try:
        # Загружаем только HTML-код страницы (это происходит мгновенно)
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Ошибка: Сервер вернул код {response.status_code}")
            continue
            
        # Передаем HTML парсеру BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # --- ТЕСТ ЖАНРОВ ---
        print("[Проверка Жанров]: ", end="")
        genre_section = soup.find(class_="c-mp3-header__sections")
        if genre_section:
            genre_links = genre_section.find_all("a")
            genres = [g.get_text(strip=True) for g in genre_links if g.get_text(strip=True)]
            print(f"УСПЕХ! Найдены жанры: {genres}")
        else:
            print("Блок жанров не найден.")

        # --- ТЕСТ ТЕКСТА ПЕСНИ ---
        print("[Проверка Текста]: ", end="")
        lyrics_box = soup.find(class_="c-mp3-header__lyrics")
        if lyrics_box:
            # Ищем спан с текстом
            lyrics_text_element = lyrics_box.find(class_="c-mp3-header__lyrics-text")
            if lyrics_text_element:
                # get_text(separator=" ") автоматически заменяет теги <br> на пробелы
                raw_text = lyrics_text_element.get_text(separator=" ")
                
                # Очищаем от лишних переносов и пробелов
                clean_lyrics = " ".join([line.strip() for line in raw_text.split("\n") if line.strip()])
                
                if clean_lyrics and "Предложить текст" not in clean_lyrics:
                    print(f"УСПЕХ! Текст найден (длина {len(clean_lyrics)} симв.)")
                    print(f"Кусочек текста: {clean_lyrics[:60]}...")
                else:
                    print("На странице только кнопка 'Предложить текст'.")
            else:
                print("Спан c-mp3-header__lyrics-text не найден.")
        else:
            print("Блок c-mp3-header__lyrics отсутствует.")

    except Exception as e:
        print(f"Ошибка при запросе к странице: {e}")
        
    # Крошечная пауза, чтобы не спамить сервер
    time.sleep(0.5)

print(f"\n==================================================")
print("Быстрый тест завершен!")
