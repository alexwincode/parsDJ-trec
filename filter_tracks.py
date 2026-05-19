import json
import re
import time
from datetime import datetime
import lyricsgenius
import translators as ts
import tk as TOKEN
# --- НАСТРОЙКИ СЕКЬЮРНОСТИ ---
GENIUS_ACCESS_TOKEN = "TOKEN"  # Проверьте, чтобы тут стоял ваш свежий токен

BAD_WORDS_PATTERNS = [
    r'хуй', r'хуе', r'хуя', r'пизд', r'еба', r'ебл', r'ебу', r'бля', r'сука', 
    r'гандон', r'гондон', r'мудак', r'манда', r'хер', r'дроч', r'залуп',
    r'fuck', r'bitch', r'shit', r'dick', r'pussy', r'asshole'
]

def has_explicit_content(text):
    if not text:
        return False
    text_lower = text.lower()
    for pattern in BAD_WORDS_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

def clean_artist_name(artist_name):
    """Оставляет только первого артиста."""
    parts = re.split(r'\s+(?:and|feat\.?|&|,|x)\s+', artist_name, flags=re.IGNORECASE)
    return parts[0].strip()

def clean_song_name(song_name):
    """Убирает приписки в скобках из названий треков, чтобы Genius не тупил."""
    # "Pinterest (Portuguese)" -> "Pinterest"
    return re.sub(r'\(.*?\)', '', song_name).strip()

# --- ОСНОВНОЙ ПРОЦЕСС ---
try:
    with open("tracks_extended.json", "r", encoding="utf-8") as f:
        tracks = json.load(f)
except FileNotFoundError:
    print("Ошибка: Файл tracks_extended.json не найден. Запустите Скрипт 2.")
    exit()

# Инициализируем API Genius с жесткими лимитами на таймаут
# timeout=5 не позволит скрипту висеть дольше 5 секунд на одной песне
# Увеличиваем таймаут до 15 и добавляем пропуск мусора (skip_non_songs)
genius = lyricsgenius.Genius(
    GENIUS_ACCESS_TOKEN, 
    remove_section_headers=True, 
    timeout=15, 
    skip_non_songs=True
)


explicit_tracks = []     
relevant_tracks = []     
unknown_checking = []    

current_date = datetime.now().strftime("%Y-%m-%d")

print(f"=== СТАРТ СТАБИЛЬНОЙ ФИЛЬТРАЦИИ С ЗАЩИТОЙ ОТ ЗАВИСАНИЙ ===")
print(f"Всего треков на обработку: {len(tracks)}")

for index, track in enumerate(tracks, start=1):
    updated_track = track.copy()
    updated_track["processed_date"] = current_date
    
    artist = track.get("artist", "")
    song = track.get("song", "")
    lyrics = track.get("lyrics", "")
    
    # 1. Если текст уже есть с сайта lmusic
    if lyrics and lyrics != "Текст песни отсутствует":
        if has_explicit_content(lyrics):
            explicit_tracks.append(updated_track)
        else:
            relevant_tracks.append(updated_track)
            
    # 2. Если текста нет — запрашиваем Genius с тройной защитой
    else:
        cleaned_artist = clean_artist_name(artist)
        cleaned_song = clean_song_name(song)
        print(f"[{index}/{len(tracks)}] Проверяем на Genius: {cleaned_artist} - {cleaned_song}")
        
        try:
            # Ищем песню (метод внутри try защитит от вылетов самой библиотеки)
            song_data = genius.search_song(cleaned_song, cleaned_artist)
            
            if song_data and song_data.lyrics:
                genius_lyrics = song_data.lyrics
                updated_track["lyrics"] = genius_lyrics  
                
                # Безопасный перевод
                clean_translation = ""
                try:
                    translated_text = ts.translate_text(genius_lyrics[:1000], from_language='auto', to_language='ru')
                    if translated_text:
                        clean_translation = " ".join([line.strip() for line in translated_text.split("\n") if line.strip()])
                except Exception:
                    pass 
                
                # Проверка мата
                if has_explicit_content(genius_lyrics) or (clean_translation and has_explicit_content(clean_translation)):
                    print("   -> ❌ Найдено нецензурное содержание. В 'С матом'.")
                    explicit_tracks.append(updated_track)
                else:
                    print("   ->  Чистый трек по данным Genius. В 'Без мата'.")
                    relevant_tracks.append(updated_track)
            else:
                print("   -> ⚠️ Текст не найден в базе Genius. В 'На проверку'.")
                updated_track["reason_to_check"] = "Отсутствует в базах данных"
                unknown_checking.append(updated_track)
                
        except Exception as err:
            # Сюда код попадет, если Genius завис или сбросил соединение. Скрипт пойдет дальше!
            print(f"   -> ⚠️ Пропуск из-за таймаута/ошибки API. В 'На проверку'.")
            updated_track["reason_to_check"] = f"Таймаут или ошибка поиска API"
            unknown_checking.append(updated_track)
            
        time.sleep(1.2)

# Сохраняем результаты в файлы
with open("tracks_explicit.json", "w", encoding="utf-8") as f:
    json.dump(explicit_tracks, f, ensure_ascii=False, indent=4)

with open("tracks_relevant.json", "w", encoding="utf-8") as f:
    json.dump(relevant_tracks, f, ensure_ascii=False, indent=4)

with open("tracks_unknown_checking.json", "w", encoding="utf-8") as f:
    json.dump(unknown_checking, f, ensure_ascii=False, indent=4)

print("\n--- Фильтрация успешно завершена! ---")
print(f" Категория 'С матом': {len(explicit_tracks)} треков")
print(f" Категория 'Без мата': {len(relevant_tracks)} треков")
print(f" Категория 'На проверку': {len(unknown_checking)} треков")
