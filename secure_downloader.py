import json
import os
import re
import requests
from tqdm import tqdm

HISTORY_FILE = "downloaded_history.json"
BASE_MUSIC_DIR = "DJ_Library"

def load_history():
    """Загружает глобальную историю скачиваний."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_history(history):
    """Сохраняет историю."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def sanitize_name(name):
    """Очищает имена папок и файлов от запрещенных символов Windows."""
    if isinstance(name, list):
        name = name[0] if name else "Разное"
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

def download_file(url, target_path, file_name):
    """Качает mp3 с индикатором прогресса."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            with open(target_path, 'wb') as f, tqdm(
                desc=file_name[:25], total=total_size, unit='B', unit_scale=True, unit_divisor=1024, leave=False
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
            return True
        else:
            print(f" Ошибка сервера при скачивании {file_name}: статус {response.status_code}")
    except Exception as e:
        print(f" Не удалось загрузить {file_name}: {e}")
    return False

# 1. Интерактивное меню в консоли
print("=== МЕНЕДЖЕР ДИДЖЕЙСКОЙ БИБЛИОТЕКИ ===")
print("Выберите, какую категорию треков вы хотите скачать прямо сейчас:")
print("1 - Только проверенные чистые треки (Без мата)")
print("2 - Только гарантированный мат (С матом)")
print("3 - Скачать ЗОНУ РИСКА (На проверку: иностранные / без текста)")
print("4 - Скачать ВООБЩЕ ВСЕ треки из текущего топа")
choice = input("Введите цифру (1, 2, 3 или 4): ").strip()

# Сопоставляем выбор с файлами и будущей подпапкой
download_tasks = []
if choice == "1":
    download_tasks = [("tracks_relevant.json", "Без мата")]
elif choice == "2":
    download_tasks = [("tracks_explicit.json", "С матом")]
elif choice == "3":
    download_tasks = [("tracks_unknown_checking.json", "На проверку")]
elif choice == "4":
    download_tasks = [
        ("tracks_relevant.json", "Без мата"),
        ("tracks_explicit.json", "С матом"),
        ("tracks_unknown_checking.json", "На проверку")
    ]
else:
    print("Неверный выбор. Завершение программы.")
    exit()

# 2. Читаем треки из выбранных файлов
target_tracks = []
for file_name, folder_type in download_tasks:
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            file_data = json.load(f)
            # Запоминаем для каждого трека, в какую подпапку его класть
            for t in file_data:
                t["target_subfolder"] = folder_type
                target_tracks.append(t)
    else:
        print(f"Предупреждение: Файл {file_name} не найден. Пропускаем.")

if not target_tracks:
    print("Нет треков для скачивания. Убедитесь, что запустили прошлые скрипты.")
    exit()

# 3. Загружаем глобальную базу для исключения дубликатов
history_db = load_history()
history_keys = {f"{t['artist'].lower()} - {t['song'].lower()}" for t in history_db}

print(f"\nВсего треков в глобальной истории (скачано ранее): {len(history_db)}")
print(f"Выбрано треков для обработки сейчас: {len(target_tracks)}")
print("Начинаем процесс...")

# 4. Основной цикл скачивания и сортировки
for index, track in enumerate(target_tracks, start=1):
    artist = track.get("artist", "Unknown Artist")
    song = track.get("song", "Unknown Song")
    download_url = track.get("download_url")
    genres = track.get("genres", [])
    subfolder = track.get("target_subfolder", "На проверку")
    processed_date = track.get("processed_date", "Не указана")
    
    # Ключ уникальности трека
    track_key = f"{artist.lower()} - {song.lower()}"
    
    # Защита от повторного скачивания треков из прошлых месяцев
    if track_key in history_keys:
        print(f"[{index}/{len(target_tracks)}] Пропуск (уже скачивался ранее): {artist} - {song}")
        continue

    if not download_url:
        print(f"[{index}/{len(target_tracks)}] Пропуск (нет ссылки): {artist} - {song}")
        continue

    # Вычисляем имя жанра для главной папки
    genre_name = sanitize_name(genres) if genres else "Разное"
    if genre_name == "Не указан":
        genre_name = "Разное"

    # Строим путь: DJ_Library / Жанр / [Без мата | С матом | На проверку]
    target_dir = os.path.join(BASE_MUSIC_DIR, genre_name, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    file_name = sanitize_name(f"{artist} - {song}.mp3")
    file_path = os.path.join(target_dir, file_name)

    print(f"[{index}/{len(target_tracks)}] Загрузка -> [{genre_name} / {subfolder}]: {artist} - {song}")
    
    # Качаем файл
    if download_file(download_url, file_path, file_name):
        # Добавляем в общую базу данных только при успешном скачивании
        history_db.append({
            "artist": artist,
            "song": song,
            "genre": genre_name,
            "category": subfolder,
            "download_date": processed_date
        })
        history_keys.add(track_key)
        save_history(history_db)

print(f"\n🎉 Все выбранные операции завершены! История в {HISTORY_FILE} обновлена.")
