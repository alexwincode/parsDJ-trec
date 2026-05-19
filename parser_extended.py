import json
import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# 1. Читаем базовый JSON с треками
try:
    with open("tracks.json", "r", encoding="utf-8") as f:
        base_tracks = json.load(f)
except FileNotFoundError:
    print("Ошибка: Файл tracks.json не найден! Сначала запустите первый скрипт.")
    exit()

extended_tracks = []
ua = UserAgent()

print(f"=== ЗАПУСК СВЕРХБЫСТРОГО РАСШИРЕННОГО ПАРСИНГА ===")
print(f"Всего треков для обработки: {len(base_tracks)}")

# 2. Основной цикл прохода по страницам треков
for index, track in enumerate(base_tracks, start=1):
    url = track.get("track_page_url")
    
    if not url:
        extended_tracks.append(track)
        continue

    print(f"[{index}/{len(base_tracks)}] Мгновенный запрос к: {track.get('artist')} - {track.get('song')}")

    # Защита: каждый запрос идет со случайным User-Agent
    headers = {"User-Agent": ua.random}
    
    try:
        # Скачиваем только чистый HTML без картинок, стилей и рекламы
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # --- Сбор Жанров ---
            genres = ["Разное"]
            genre_section = soup.find(class_="c-mp3-header__sections")
            if genre_section:
                genre_links = genre_section.find_all("a")
                genres = [g.get_text(strip=True) for g in genre_links if g.get_text(strip=True)]

            # --- Сбор Текста песни ---
            lyrics = "Текст песни отсутствует"
            lyrics_box = soup.find(class_="c-mp3-header__lyrics")
            if lyrics_box:
                lyrics_text_element = lyrics_box.find(class_="c-mp3-header__lyrics-text")
                if lyrics_text_element:
                    # separator=" " автоматически превращает <br> в пробелы
                    raw_text = lyrics_text_element.get_text(separator=" ")
                    # Чистим от рваных отступов и пустых строк
                    clean_lyrics = " ".join([line.strip() for line in raw_text.split("\n") if line.strip()])
                    
                    if clean_lyrics and "Предложить текст" not in clean_lyrics:
                        lyrics = clean_lyrics

            # --- Перекомпоновка данных ---
            extended_info = track.copy()
            extended_info["genres"] = genres
            extended_info["lyrics"] = lyrics
            extended_tracks.append(extended_info)

        else:
            print(f"    Ошибка сервера (код {response.status_code}), добавляем базовую инфо.")
            extended_tracks.append(track)

    except Exception as e:
        print(f"    Ошибка при обработке: {e}")
        extended_tracks.append(track)

    # Крошечная пауза 0.7 секунды, чтобы сайт не посчитал это спам-атакой
    time.sleep(0.7)

# 3. Сохраняем расширенный результат
with open("tracks_extended.json", "w", encoding="utf-8") as f:
    json.dump(extended_tracks, f, ensure_ascii=False, indent=4)

print(f"\n🎉 Обработка завершена! Все 100 треков сохранены в tracks_extended.json")
