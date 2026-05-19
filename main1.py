import os
import re
import time
import random
import librosa
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Список матерных корней для проверки текста
BAD_WORDS_PATTERN = re.compile(
    r"\b(хуй|хуе|хуи|пизд|еба|ебл|бля|сук|мудак|гондо|гандо)\w*",
    re.IGNORECASE
)

def has_profanity(text):
    """Проверяет текст на наличие мата."""
    if not text:
        return False
    return bool(BAD_WORDS_PATTERN.search(text))

def get_bpm_folder(bpm):
    """Определяет имя папки в зависимости от диапазона BPM."""
    if isinstance(bpm, str) or bpm == 0:
        return "Unknown_BPM"
    if bpm < 100:
        return "Slow_Tracks_under_100"
    elif 100 <= bpm < 120:
        return "Mid_Tracks_100_120"
    elif 120 <= bpm < 130:
        return "House_Techno_120_130"
    else:
        return "Fast_Tracks_above_130"

def process_single_track(url, base_folder="dj_library"):
    """Скачивает, анализирует и сортирует один трек."""
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3"
    }

    print(f"\n Начинаем обработку: {url}")
    print(f"Используем User-Agent: {headers['User-Agent']}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ Ошибка загрузки страницы: Статус {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Не удалось подключиться к сайту: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Поиск текста песни и названия для проверки на мат
    lyrics_div = soup.find("div", class_="lyrics") or soup.find("div", class_="song-text")
    lyrics_text = lyrics_div.text if lyrics_div else ""
    
    title_tag = soup.find("title")
    title_text = title_tag.text.replace("скачать mp3 бесплатно", "").strip() if title_tag else "track"
    
    print("-> Проверка на ненормативную лексику...")
    if has_profanity(title_text) or has_profanity(lyrics_text):
        print("❌ Трек отбракован: найден мат!")
        return
    print("✅ Проверка пройдена: мата нет.")

    # Очистка имени файла
    filename_clean = re.sub(r'[\\/*?:"<>| ]', "_", title_text)

    # 2. Поиск ссылки на MP3
    download_link = None
    for a_tag in soup.find_all("a", href=True):
        if ".mp3" in a_tag["href"]:
            download_link = a_tag["href"]
            break

    if not download_link:
        print("❌ Прямая ссылка на MP3 не найдена.")
        return

    if download_link.startswith("/"):
        download_link = "https://lmusic.kz" + download_link

    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
        
    temp_path = os.path.join(base_folder, "temp_track.mp3")

    # 3. Скачивание аудиофайла с буферизацией (stream=True)
    print("-> Скачивание файла в буфер...")
    try:
        # stream=True позволяет скачивать файл частями, не загружая его в ОЗУ целиком
        with requests.get(download_link, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(temp_path, "wb") as f:
                # Скачиваем блоками (буфером) по 8 КБ
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
    except Exception as e:
        print(f"❌ Ошибка при скачивании файла: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return

    # 4. Анализ BPM (первые 45 секунд для скорости)
    print("-> Анализ темпа (BPM)...")
    try:
        y, sr = librosa.load(temp_path, sr=None, duration=45)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = int(round(float(tempo)))
        print(f"-> Определенный BPM: {bpm}")
    except Exception as e:
        print(f"⚠ Ошибка анализа аудио (возможно, битый файл): {e}")
        bpm = 0

    # 5. Распределение по папкам
    target_folder_name = get_bpm_folder(bpm)
    final_dir = os.path.join(base_folder, target_folder_name)
    
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)

    bpm_prefix = f"{bpm}_BPM_" if bpm > 0 else "UNKNOWN_BPM_"
    final_filename = f"{bpm_prefix}{filename_clean}.mp3"
    final_path = os.path.join(final_dir, final_filename)

    if os.path.exists(temp_path):
        os.rename(temp_path, final_path)
        print(f"🎉 Файл успешно сохранен в: {final_path}")


def run_pipeline(url_list, min_delay=3, max_delay=7):
    """Запускает пакетную обработку ссылок с задержками."""
    total = len(url_list)
    print(f"=== Запуск автоматизации для {total} треков ===")
    
    for idx, url in enumerate(url_list, start=1):
        process_single_track(url)
        
        # Если это не последний трек, делаем паузу
        if idx < total:
            # Рандомная задержка делает поведение скрипта «человечным»
            delay = random.uniform(min_delay, max_delay)
            print(f"\n[Ожидание] Пауза {delay:.2f} сек. перед следующим треком...")
            time.sleep(delay)
            
    print("\n=== Все треки обработаны! ===")


# --- ТЕСТОВЫЙ ЗАПУСК ---
if __name__ == "__main__":
    # Сюда можно добавлять сколько угодно ссылок для скачивания
    urls_to_download = [
        "https://lmusic.kz",
        # "https://lmusic.kz... еще трек ...",
    ]
    
    # Запускаем конвейер (задержка от 3 до 7 секунд между запросами)
    run_pipeline(urls_to_download, min_delay=3, max_delay=7)
