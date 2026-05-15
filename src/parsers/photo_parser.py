import easyocr
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

reader = easyocr.Reader(['ru', 'en'])


def ocr_photo(photo_path):
    try:
        if not os.path.exists(photo_path):
            print(f"Файл не найден: {photo_path}")
            return ""

        result = reader.readtext(photo_path)

        text_lines = []
        for detection in result:
            text = detection[1]
            confidence = detection[2]
            if confidence > 0.5:
                text_lines.append(text)

        return "\n".join(text_lines)

    except Exception as e:
        print(f"Ошибка OCR: {e}")
        return ""


def normalize_day(day_str: str) -> str:
    """Приводит день недели к стандартному виду"""
    day_str = day_str.lower().strip()
    day_map = {
        'пн': 'пн', 'понедельник': 'пн', 'пон': 'пн',
        'вт': 'вт', 'вторник': 'вт', 'вто': 'вт',
        'ср': 'ср', 'среда': 'ср', 'сред': 'ср',
        'чт': 'чт', 'четверг': 'чт', 'чет': 'чт',
        'пт': 'пт', 'пятница': 'пт', 'пят': 'пт',
        'сб': 'сб', 'суббота': 'сб', 'суб': 'сб',
        'вс': 'вс', 'воскресенье': 'вс', 'воск': 'вс',
        # Заглавные варианты
        'пн.': 'пн', 'вт.': 'вт', 'ср.': 'ср', 'чт.': 'чт',
        'пт.': 'пт', 'сб.': 'сб', 'вс.': 'вс',
    }
    return day_map.get(day_str, None)


def normalize_week_type(week_str: str) -> str:
    """Приводит тип недели к стандартному виду"""
    if not week_str:
        return "both"

    week_map = {
        'both': 'both', 'оба': 'both', 'каждая': 'both', 'все': 'both',
        'even': 'even', 'чётная': 'even', 'четная': 'even', 'чет': 'even', 'ч': 'even',
        'odd': 'odd', 'нечётная': 'odd', 'нечетная': 'odd', 'нечет': 'odd', 'н': 'odd',
    }
    return week_map.get(week_str.lower().strip(), "both")


def parse_time(time_str: str) -> str:
    """Приводит время к формату HH:MM"""
    # Ищем числа в строке
    numbers = re.findall(r'\d{1,2}', time_str)
    if len(numbers) >= 2:
        hours = int(numbers[0])
        minutes = int(numbers[1])
        # Корректируем часы (0-23)
        if hours > 23:
            hours = hours % 10 if hours % 10 < 24 else 9
        # Корректируем минуты (0-59)
        if minutes > 59:
            minutes = minutes % 10 if minutes % 10 < 60 else 0
        return f"{hours:02d}:{minutes:02d}"

    # Если только одно число — считаем что это часы, минуты 00
    if numbers:
        hours = int(numbers[0])
        return f"{hours:02d}:00"

    return ""


def normalize_subject(text: str) -> str:
    """Очищает название предмета от мусора"""
    # Убираем лишние символы
    text = re.sub(r'[^\w\sа-яА-Я\-]', ' ', text)
    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    # Убираем пробелы по краям
    text = text.strip()
    # Ограничиваем длину
    return text[:50]


def parse_schedule_from_photo(text: str) -> List[Dict[str, str]]:
    """
    Простой парсер расписания из фото.
    Ожидает формат: день время предмет [week_type]
    Пример: понедельник 09:00-10:30 Математика
           вторник 10:45-12:15 Физика even
    """
    lessons = []

    # Нормализация текста: убираем лишние переносы строк
    # Заменяем переносы на пробелы, но сохраняем структуру
    lines = text.split('\n')

    # Список всех возможных дней недели
    day_map = {
        'понедельник': 'пн', 'пн': 'пн', 'пон': 'пн',
        'вторник': 'вт', 'вт': 'вт', 'вто': 'вт',
        'среда': 'ср', 'ср': 'ср', 'сред': 'ср',
        'четверг': 'чт', 'чт': 'чт', 'чет': 'чт',
        'пятница': 'пт', 'пт': 'пт', 'пят': 'пт',
        'суббота': 'сб', 'сб': 'сб', 'суб': 'сб',
        'воскресенье': 'вс', 'вс': 'вс', 'вос': 'вс'
    }

    # Склеиваем строки обратно, но умно
    # Ищем паттерны в слитном тексте
    full_text = ' '.join(lines)

    # Разбиваем по дням недели
    for day_full, day_short in day_map.items():
        # Ищем паттерн: день + время + предмет
        pattern = rf'{day_full}\s+(\d{{1,2}}[:.]?\d{{0,2}}?\s*[-–—]\s*\d{{1,2}}[:.]?\d{{0,2}}?)\s+([а-яА-Яa-zA-Z\s]+?)(?=\s*(?:{"|".join(day_map.keys())}|$))'

        matches = re.findall(pattern, full_text, re.IGNORECASE)

        for match in matches:
            time_str = match[0]
            subject_part = match[1].strip()

            # Парсим время
            time_match = re.search(r'(\d{1,2})[:.]?(\d{0,2})\s*[-–—]\s*(\d{1,2})[:.]?(\d{0,2})', time_str)
            if time_match:
                start_h = int(time_match.group(1))
                start_m = int(time_match.group(2)) if time_match.group(2) else 0
                end_h = int(time_match.group(3))
                end_m = int(time_match.group(4)) if time_match.group(4) else 0

                start_time = f"{start_h:02d}:{start_m:02d}"
                end_time = f"{end_h:02d}:{end_m:02d}"
            else:
                continue

            # Парсим тип недели и предмет
            week_type = "both"
            subject = subject_part

            # Ищем тип недели в конце строки
            week_match = re.search(r'\b(even|odd|both|чётная|нечётная|четная|нечетная|каждая)\b', subject,
                                   re.IGNORECASE)
            if week_match:
                week_raw = week_match.group(1).lower()
                if week_raw in ['even', 'чётная', 'четная']:
                    week_type = "even"
                elif week_raw in ['odd', 'нечётная', 'нечетная']:
                    week_type = "odd"
                else:
                    week_type = "both"
                # Убираем тип недели из названия предмета
                subject = re.sub(r'\b(even|odd|both|чётная|нечётная|четная|нечетная|каждая)\b', '', subject,
                                 flags=re.IGNORECASE)

            # Очищаем предмет от лишних пробелов
            subject = re.sub(r'\s+', ' ', subject).strip()

            if subject and start_time and end_time:
                lessons.append({
                    "day": day_short,
                    "start_time": start_time,
                    "end_time": end_time,
                    "subject": subject[:50],
                    "week_type": week_type
                })

    # Убираем дубликаты
    unique = []
    for l in lessons:
        if l not in unique:
            unique.append(l)

    return unique


@dataclass
class PhotoData:
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: Optional[int] = None
    uploaded_at: str = None

    def __post_init__(self):
        if not self.uploaded_at:
            self.uploaded_at = datetime.now().isoformat()


class PhotoParser:

    def __init__(self):
        self.photos_cache = {}

    def extract_photo_info(self, message) -> Optional[PhotoData]:
        try:
            if not message.photo:
                return None

            photo = message.photo[-1]

            photo_data = PhotoData(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                width=photo.width,
                height=photo.height,
                file_size=getattr(photo, 'file_size', None)
            )

            self.photos_cache[message.message_id] = photo_data
            return photo_data

        except Exception as e:
            print(f"Ошибка извлечения фото: {e}")
            return None

    def get_file_id_only(self, message) -> Optional[str]:
        photo_data = self.extract_photo_info(message)
        return photo_data.file_id if photo_data else None


# Глобальный экземпляр
photo_parser = PhotoParser()


# ===== ФУНКЦИЯ ДЛЯ ИМПОРТА В import_homework =====
def get_photo_file_id_from_message(message) -> Optional[str]:
    return photo_parser.get_file_id_only(message)


def validate_photo_file_id(file_id: str) -> bool:
    if not file_id or not isinstance(file_id, str):
        return False

    if len(file_id) < 20:
        return False

    if re.match(r'^[A-Za-z0-9\-_=\./+]+$', file_id):
        return True

    return False


def extract_photo_metadata(message) -> Optional[Dict[str, Any]]:
    photo_data = photo_parser.extract_photo_info(message)

    if photo_data:
        return {
            'file_id': photo_data.file_id,
            'file_unique_id': photo_data.file_unique_id,
            'width': photo_data.width,
            'height': photo_data.height,
            'file_size': photo_data.file_size,
            'uploaded_at': photo_data.uploaded_at
        }

    return None


def get_photo_info_by_file_id(bot, file_id: str) -> Optional[Dict[str, Any]]:
    try:
        file_info = bot.get_file(file_id)
        return {
            'file_id': file_id,
            'file_path': file_info.file_path,
            'file_size': file_info.file_size,
            'file_unique_id': file_info.file_unique_id
        }
    except Exception as e:
        print(f"Ошибка получения информации о файле: {e}")
        return None


def clear_photo_cache():
    photo_parser.clear_cache()
