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
    day_map = {
        # Сокращения с опечатками
        'пн': 'пн', 'понедельник': 'пн', 'пон': 'пн',
        'вт': 'вт', 'вторник': 'вт', 'вто': 'вт',
        'ср': 'ср', 'среда': 'ср', 'сред': 'ср',
        'чт': 'чт', 'четверг': 'чт', 'чет': 'чт',
        'пт': 'пт', 'пятница': 'пт', 'пят': 'пт',
        'сб': 'сб', 'суббота': 'сб', 'суб': 'сб',
        'вс': 'вс', 'воскресенье': 'вс', 'воск': 'вс',
        # Ошибки распознавания
        'пн.': 'пн', 'вт.': 'вт', 'ср.': 'ср', 'чт.': 'чт',
        'пт.': 'пт', 'сб.': 'сб', 'вс.': 'вс',
    }
    return day_map.get(day_str.lower().strip(), None)


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
    Распознаёт расписание из текста, полученного с фото.
    Поддерживает форматы:
    - пн 09:00-10:30 Математика
    - вт 10:45-12:15 Физика even
    - ср 13:00-14:30 Информатика odd
    - чт 9:00-10:30 Русский
    - пт 12:00-13:30 Физра both
    """
    lessons = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # 1. Ищем день недели
        day_match = re.search(r'\b(пн|вт|ср|чт|пт|сб|вс|[а-я]+)\b', line.lower())
        day = None
        if day_match:
            day = normalize_day(day_match.group(1))

        if not day:
            continue

        # 2. Ищем время (разные форматы)
        # Формат: 09:00-10:30 или 9:00-10:30 или 09:00 - 10:30
        time_patterns = [
            r'(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})',  # 09:00-10:30
            r'(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})',  # 9:00-10:30
            r'(\d{1,2})\s*[-–—]\s*(\d{1,2})',  # 9-10 (только часы)
        ]

        start_time = ""
        end_time = ""

        for pattern in time_patterns:
            match = re.search(pattern, line)
            if match:
                if len(match.groups()) == 2 and ':' not in match.group(1):
                    # Формат: 9-10 (только часы)
                    start_time = parse_time(f"{match.group(1)}:00")
                    end_time = parse_time(f"{match.group(2)}:00")
                elif len(match.groups()) == 2:
                    # Формат: 09:00-10:30
                    start_time = parse_time(match.group(1))
                    end_time = parse_time(match.group(2))
                elif len(match.groups()) == 4:
                    # Формат: 9:00-10:30
                    start_time = parse_time(f"{match.group(1)}:{match.group(2)}")
                    end_time = parse_time(f"{match.group(3)}:{match.group(4)}")
                break

        if not start_time or not end_time:
            continue

        # 3. Ищем тип недели
        week_type_match = re.search(r'\b(odd|even|both|чётная|нечётная|четная|нечетная)\b', line.lower())
        week_type = normalize_week_type(week_type_match.group(1) if week_type_match else "")

        # 4. Извлекаем название предмета (всё, что осталось после удаления дня, времени и типа недели)
        subject_text = line
        # Удаляем день
        subject_text = re.sub(r'\b(пн|вт|ср|чт|пт|сб|вс|[а-я]+)\b', '', subject_text, flags=re.IGNORECASE)
        # Удаляем время
        subject_text = re.sub(r'(\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2})', '', subject_text)
        subject_text = re.sub(r'(\d{1,2}\s*[-–—]\s*\d{1,2})', '', subject_text)
        # Удаляем тип недели
        subject_text = re.sub(r'\b(odd|even|both|чётная|нечётная|четная|нечетная)\b', '', subject_text,
                              flags=re.IGNORECASE)

        subject = normalize_subject(subject_text)

        if not subject:
            continue

        lessons.append({
            "day": day,
            "start_time": start_time,
            "end_time": end_time,
            "subject": subject,
            "week_type": week_type
        })

    return lessons


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
