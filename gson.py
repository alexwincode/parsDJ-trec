import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. Настройка браузера (окно открыто, чтобы вы видели процесс)
options = webdriver.ChromeOptions()
options.add_argument("--blink-settings=imagesEnabled=false") # Отключаем картинки для скорости
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

all_tracks = []
# Начальный адрес топа
next_url = "https://lmusic.kz/top_kz/monthly"

try:
    while next_url:
        print(f"Загружаем страницу: {next_url}")
        driver.get(next_url)
        time.sleep(2.5)  # Обязательно ждем, пока прогрузятся треки

        # 2. Собираем треки с текущей страницы
        track_elements = driver.find_elements(By.CLASS_NAME, "js-item-mp3")
        print(f"Найдено треков на текущей странице: {len(track_elements)}")
        
        for track in track_elements:
            download_path = track.get_attribute("data-download_url")
            track_path = track.get_attribute("data-url")
            
            all_tracks.append({
                "artist": track.get_attribute("data-artist_name"),
                "song": track.get_attribute("data-song_name"),
                "cover_image": track.get_attribute("data-cover_url"),
                "track_page_url": f"https://lmusic.kz{track_path}" if track_path else None,
                "download_url": f"https://lmusic.kz{download_path}" if download_path else None
            })

        # 3. Ищем ссылку на следующую страницу через класс c-pagination
        try:
            # Находим элемент строго по его классу
            pagination_button = driver.find_element(By.CLASS_NAME, "c-pagination")
            next_url = pagination_button.get_attribute("href")
            
            # Если href пустой или ведет на тот же адрес, останавливаемся
            if not next_url or next_url == driver.current_url:
                next_url = None
                
        except Exception:
            # Если класса c-pagination больше нет на странице, топ-100 закончился
            print("Элемент пагинации больше не найден. Сбор завершен.")
            next_url = None

    # 4. Сохраняем все собранные страницы в JSON-файл
    with open("tracks.json", "w", encoding="utf-8") as f:
        json.dump(all_tracks, f, ensure_ascii=False, indent=4)

    print(f"\nУспех! Всего собрано и сохранено треков: {len(all_tracks)}")

except Exception as main_error:
    print(f"Произошла ошибка в работе скрипта: {main_error}")

finally:
    driver.quit()
