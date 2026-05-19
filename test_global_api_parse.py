import json
import time
import re
import lyricsgenius
import translators as ts
import tk 
# --- НАСТРОЙКИ СЕКЬЮРНОСТИ ---
GENIUS_ACCESS_TOKEN = tk.TOKEN
# ВСТАВЬТЕ СЮДА ВАШ СКОПИРОВАННЫЙ ТОКЕН С САЙТА GENIUS
# GENIUS_ACCESS_TOKEN = "3re-3rrTP5lwg-8TL3du0P4aLfV5RKhcCrFWX3pabqsCizsdz2m3EPkzHz2G5OT6"

# Расширенный список мата (русский + английский)
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
    parts = re.split(r'\s+(?:and|feat\.?|&|,|x)\s+', artist_name, flags=re.IGNORECASE)
    return parts[0].strip()

# Инициализируем Genius API с исправленным параметром
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, remove_section_headers=True)

try:
    with open("tracks_unknown_checking.json", "r", encoding="utf-8") as f:
        suspicious_tracks = json.load(f)
except FileNotFoundError:
    print("Ошибка: Файл tracks_unknown_checking.json не найден.")
    exit()

test_list = suspicious_tracks[:5]

print(f"=== ЗАПУСК НАДЕЖНОГО ТЕСТА GENIUS API ДЛЯ {len(test_list)} ТРЕКОВ ===")

for index, track in enumerate(test_list, start=1):
    raw_artist = track.get("artist", "")
    song = track.get("song", "")
    artist = clean_artist_name(raw_artist)
    
    print(f"\n--------------------------------------------------")
    print(f"[{index}/{len(test_list)}] Проверяем: {raw_artist} -> (Поиск на Genius: {artist} - {song})")
    
    try:
        # Ищем песню
        song_data = genius.search_song(song, artist)
        
        if song_data and song_data.lyrics:
            print(" Текст песни успешно получен из Genius API!")
            original_lyrics = song_data.lyrics
            
            # Попытка перевода с защитой от сбоев переводчика
            clean_translation = ""
            print(" Переводим текст на русский язык...")
            try:
                text_to_translate = original_lyrics[:1000] # берем чуть меньше текста для стабильности
                translated_text = ts.translate_text(text_to_translate, from_language='auto', to_language='ru')
                if translated_text:
                    clean_translation = " ".join([line.strip() for line in translated_text.split("\n") if line.strip()])
                    print(f" Кусочек перевода: {clean_translation[:70]}...")
            except Exception as translate_error:
                print(f" ⚠️ Переводчик временно недоступен. Проверяем только по оригиналу текста.")

            # ФИНАЛЬНЫЙ ВЕРДИКТ БЕЗОПАСНОСТИ
            # Проверяем оригинал (на английском/корейском) и перевод (на русском)
            if has_explicit_content(original_lyrics) or (clean_translation and has_explicit_content(clean_translation)):
                print("❌ РЕЗУЛЬТАТ: НАЙДЕН МАТ! Отправляем в папку 'С матом'.")
            else:
                print("✅ РЕЗУЛЬТАТ: Текст чистый. Можно переносить в 'Без мата'.")
                
        else:
            print(" ❌ Текст для этого трека отсутствует в базе Genius.")
            
    except Exception as e:
        print(f" ❌ Ошибка запроса к Genius API: {e}")
        
    time.sleep(1.5)

print(f"\n==================================================")
print("Проверка через Genius API завершена!")
