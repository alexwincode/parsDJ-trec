import os
import re
import time
import random
import requests
import librosa
from fake_useragent import UserAgent

# Настройки Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Базовый список матерных слов для фильтрации треков
BAD_WORDS_PATTERN = re.compile(
    r"\b(хуй|хуе|хуи|пизд|еба|ебл|бля|сук|мудак|гондо|гандо)\w*",
    re.IGNORECASE
)

def init_driver(current_user_agent):
    """Инициализирует Яндекс.Браузер в оптимизированном режиме."""
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={current_user_agent}")
    
    # Отключение картинок для экономии трафика и ускорения
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    yandex_exact_path = r"C:\Program Files (x86)\Yandex\YandexBrowser\Application\browser.exe"
    if os.path.exists(yandex_exact_path):
        options.binary_location = yandex_exact_path
    else:
        raise FileNotFoundError(f"❌ Яндекс.Браузер не найден: {yandex_exact_path}")

    service = Service(ChromeDriverManager(driver_version="146.0.7680.1026").install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def get_tracks_with_pagination(driver, category_url, max_pages=1):
    """Собирает ссылки на треки со страницы категории."""
    print(f"\n🔎 Шаг 1: Сбор ссылок из категорий...")
    all_track_data = []
    
    for page in range(1, max_pages + 1):
        if page == 1:
            current_url = category_url
        else:
            separator = "&" if "?" in category_url else "?"
            current_url = f"{category_url}{separator}page={page}"
        
        print(f"Сканируем страницу {page}: {current_url}")
        driver.get(current_url)
        time.sleep(2)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        links = driver.find_elements(By.TAG_NAME, "a")
        page_tracks_count = 0
        
        for link in links:
            try:
                url = link.get_attribute("href")
                title = link.text.strip() or "track"
                if url and "/mp3/" in url and not any(d[0] == url for d in all_track_data):
                    all_track_data.append((url, title))
                    page_tracks_count += 1
            except:
                continue
                    
        print(f"   Найдено потенциальных треков: {page_tracks_count}")
        
    print(f"✅ Сбор завершен. Всего найдено треков: {len(all_track_data)}")
    return all_track_data

def process_audio_and_save(temp_path, title_text, base_folder):
    """Выполняет мат-фильтр, анализ темпа и раскладывает аудио по директориям."""
    if BAD_WORDS_PATTERN.search(title_text):
        print("❌ Отбраковано: мат в названии.")
        if os.path.exists(temp_path): os.remove(temp_path)
        return

    print("-> Анализ темпа (BPM)...")
    try:
        y, sr = librosa.load(temp_path, sr=None, duration=30)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = int(round(float(tempo)))
        print(f"-> Определен BPM: {bpm}")
    except Exception as e:
        print(f"⚠ Ошибка аудио-анализа: {e}")
        bpm = 0

    # Определение папки по диапазону темпа
    if bpm == 0: folder_name = "Unknown_BPM"
    elif bpm < 100: folder_name = "Slow_under_100"
    elif 100 <= bpm < 120: folder_name = "Mid_100_120"
    elif 120 <= bpm < 130: folder_name = "House_Techno_120_130"
    else: folder_name = "Fast_above_130"

    final_dir = os.path.join(base_folder, folder_name)
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)

    filename_clean = re.sub(r'[\\/*?:"<>| ]', "_", title_text)
    final_path = os.path.join(final_dir, f"{bpm}_BPM_{filename_clean}.mp3")

    if os.path.exists(temp_path):
        os.rename(temp_path, final_path)
        print(f"🎉 Успешно распределено: {final_path}")

def mode_1_full_browser(driver, track_list, main_user_agent, base_folder):
    """РЕЖИМ 1: Открытие страницы каждого трека через браузер (Надежный, медленный метод)."""
    print("\n⚡ Запущен Режим 1: Полная эмуляция браузера.")
    for idx, (url, _) in enumerate(track_list, start=1):
        print(f"\n🎵 Переходим к треку [{idx}/{len(track_list)}]: {url}")
        try:
            driver.get(url)
            WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
            title_text = driver.title.replace("скачать mp3 бесплатно", "").strip()
            
            download_btn = WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '.mp3') or contains(@class, 'download')]"))
            )
            download_link = download_btn.get_attribute("href")
            
            if not download_link:
                print("❌ Ссылка на MP3 не найдена.")
                continue

            temp_path = os.path.join(base_folder, "temp_track.mp3")
            headers = {"User-Agent": main_user_agent}
            with requests.get(download_link, headers=headers, stream=True, timeout=20) as r:
                r.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk: f.write(chunk)

            process_audio_and_save(temp_path, title_text, base_folder)
            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            print(f"❌ Ошибка обработки трека в браузере: {e}")










def mode_2_fast_requests(track_list, main_user_agent, base_folder):
    """РЕЖИМ 2: Сверхбыстрое скачивание через официальный API эндпоинт без участия браузера."""
    print("\n⚡ Запущен Режим 2: Сверхбыстрый (Прямые API-запросы без окон браузера).")
    
    for idx, (url, short_title) in enumerate(track_list, start=1):
        print(f"\n🚀 Скачиваем напрямую [{idx}/{len(track_list)}]: {short_title}")
        try:
            # Выдергиваем только цифры ID из любого места ссылки с помощью регулярного выражения
            match = re.search(r'(\d+)', url)
            if not match:
                print(f"❌ Пропускаем ссылку (не найден цифровой ID): {url}")
                continue
                
            track_id = match.group(1)
            
            # 🔥 ИСПОЛЬЗУЕМ СТАБИЛЬНЫЙ API-ЭНДПОИНТ
            direct_download_url = f"https://lmusic.kz/api/download/{track_id}"
            print(f"-> API URL для загрузки: {direct_download_url}")
            
            temp_path = os.path.join(base_folder, "temp_track.mp3")
            headers = {
                "User-Agent": main_user_agent,
                "Referer": f"https://lmusic.kz{track_id}",
                "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.8"
            }
            
            # Скачивание потоком
            with requests.get(direct_download_url, headers=headers, stream=True, timeout=20) as r:
                if r.status_code != 200:
                    print(f"❌ API вернул ошибку скачивания (Статус {r.status_code}). Переключитесь на Режим 1.")
                    continue
                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=16384):
                        if chunk: f.write(chunk)

            process_audio_and_save(temp_path, short_title, base_folder)
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            print(f"❌ Ошибка прямого API скачивания: {e}")

def run_dj_automation(category_url, max_pages_to_scan=1, max_tracks_to_download=5):
    """Главный управляющий конвейер скрипта."""
    base_folder = "dj_library"
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
        
    main_user_agent = UserAgent().random
    driver = init_driver(main_user_agent)
    
    try:
        track_list = get_tracks_with_pagination(driver, category_url, max_pages=max_pages_to_scan)
        track_list = track_list[:max_tracks_to_download]
    except Exception as e:
        print(f"❌ Ошибка на этапе сбора ссылок: {e}")
        track_list = []

    if not track_list:
        print("❌ Список треков пуст. Выходим.")
        driver.quit()
        return

    print("\nВыбери метод обработки сохраненного списка:")
    print("1 — Оставлять браузер открытым и переходить по страницам (Медленнее)")
    print("2 — Закрыть браузер и качать всё скрыто через быстрые запросы к API (Максимальная скорость) 🚀")
    
    choice = input("Введи цифру 1 или 2 и нажми Enter: ").strip()

    if choice == "2":
        driver.quit()  # Браузер закрывается, работаем только через requests
        mode_2_fast_requests(track_list, main_user_agent, base_folder)
    else:
        mode_1_full_browser(driver, track_list, main_user_agent, base_folder)
        driver.quit()
        
    print("\n🏁 Программа успешно завершила работу!")

if __name__ == "__main__":
    # На целевой странице чарта скрипт соберет треки и скачает первые 5 штук
    TARGET_CATEGORY = "https://lmusic.kz/top_kz/monthly" 
    run_dj_automation(TARGET_CATEGORY, max_pages_to_scan=1, max_tracks_to_download=5)
