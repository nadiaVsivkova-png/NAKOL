import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

pytest_plugins = ('pytest_asyncio',)


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'handlers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parsers'))


# ==================== ТЕСТЫ ДЛЯ SCHEDULE.PY ====================

class TestSchedule:
    """Тесты для расписания"""

    def test_format_weekday(self):
        from schedule import format_weekday

        assert format_weekday('пн') == 'Понедельник'
        assert format_weekday('вт') == 'Вторник'
        assert format_weekday('ср') == 'Среда'
        assert format_weekday('чт') == 'Четверг'
        assert format_weekday('пт') == 'Пятница'
        assert format_weekday('сб') == 'Суббота'
        assert format_weekday('вс') == 'Воскресенье'
        assert format_weekday('unknown') == 'Unknown'

    def test_build_schedule_message_empty(self):
        from schedule import build_schedule_message

        result = build_schedule_message([], "Тест")
        assert result is None

    def test_build_schedule_message_with_data(self):
        from schedule import build_schedule_message

        lessons = [
            {
                'weekday_display': 'Понедельник',
                'start_time': '09:00',
                'end_time': '10:30',
                'subject_name': 'Математика',
                'classroom': '101'
            }
        ]

        result = build_schedule_message(lessons, "Тестовое расписание")
        assert result is not None
        assert "Тестовое расписание" in result
        assert "Понедельник" in result
        assert "09:00 - 10:30" in result
        assert "Математика" in result

    @patch('schedule.get_db')
    async def test_show_schedule_no_user(self, mock_get_db, mock_message, mock_state):
        from schedule import show_schedule

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db

        await show_schedule(mock_message, mock_state)

        mock_message.answer.assert_called_with("❌ Вы не зарегистрированы. Используйте /start")


# ==================== ТЕСТЫ ДЛЯ SESSION_SCHEDULE.PY ====================

class TestSessionSchedule:
    """Тесты для расписания сессии"""

    def test_format_date(self):
        from session_schedule import format_date

        assert format_date(None) == "Дата не указана"

        date = datetime(2026, 5, 20)
        assert format_date(date) == "20.05.2026"


# ==================== ТЕСТЫ ДЛЯ IMPORT_HOMEWORK.PY ====================

class TestImportHomework:
    """Тесты для импорта домашнего задания"""

    async def test_import_homework_command(self, mock_message, mock_state):
        from import_homework import import_homework

        await import_homework(mock_message, mock_state)

        mock_state.clear.assert_called_once()
        mock_state.update_data.assert_called_with(homeworks=[])
        mock_message.answer.assert_called_once()
        assert "Импорт домашнего задания" in mock_message.answer.call_args[0][0]

    async def test_abort_homework_import_with_homeworks(self, mock_message, mock_state):
        from import_homework import abort_homework_import

        mock_state.get_state = AsyncMock(return_value="waiting_for_manual_subject")
        mock_state.get_data = AsyncMock(return_value={'homeworks': [{'task': 'test'}]})

        await abort_homework_import(mock_message, mock_state)

        mock_message.answer.assert_called()
        assert "Отменено" in mock_message.answer.call_args[0][0]

    async def test_abort_homework_import_empty(self, mock_message, mock_state):
        from import_homework import abort_homework_import

        mock_state.get_state = AsyncMock(return_value="waiting_for_manual_subject")
        mock_state.get_data = AsyncMock(return_value={'homeworks': []})

        await abort_homework_import(mock_message, mock_state)

        mock_state.clear.assert_called_once()


# ==================== ТЕСТЫ ДЛЯ IMPORT_SCHEDULE.PY ====================

class TestImportSchedule:
    """Тесты для импорта расписания"""

    def test_can_import_schedule_starosta(self, mock_starosta):
        from import_schedule import can_import_schedule

        can_import, message = can_import_schedule(mock_starosta)
        assert can_import is True
        assert message is None

    def test_can_import_schedule_student_in_group(self, mock_user_in_group):
        from import_schedule import can_import_schedule

        can_import, message = can_import_schedule(mock_user_in_group)
        assert can_import is False
        assert "состоите в группе" in message

    def test_can_import_schedule_student_no_group(self, mock_user):
        from import_schedule import can_import_schedule

        can_import, message = can_import_schedule(mock_user)
        assert can_import is True
        assert message is None


# ==================== ТЕСТЫ ДЛЯ IMPORT_SESSION.PY ====================

class TestImportSession:
    """Тесты для импорта расписания сессии"""

    def test_can_import_session_starosta(self, mock_starosta):
        from import_session import can_import_session

        can_import, message = can_import_session(mock_starosta)
        assert can_import is True
        assert message is None

    def test_can_import_session_student_in_group(self, mock_user_in_group):
        from import_session import can_import_session

        can_import, message = can_import_session(mock_user_in_group)
        assert can_import is False
        assert "состоите в группе" in message

    def test_can_import_session_student_no_group(self, mock_user):
        from import_session import can_import_session

        can_import, message = can_import_session(mock_user)
        assert can_import is True
        assert message is None

    def test_format_date_function(self):
        from import_session import format_date

        assert format_date(None) == "Дата не указана"
        date = datetime(2026, 5, 20)
        assert format_date(date) == "20.05.2026"


# ==================== ТЕСТЫ ДЛЯ REMOVE_SUBJECT.PY ====================

class TestRemoveSubject:
    """Тесты для удаления предметов"""

    def test_get_subjects_keyboard(self):
        from remove_subject import get_subjects_keyboard

        subjects = [
            MagicMock(id=1, name="Математика"),
            MagicMock(id=2, name="Физика")
        ]

        keyboard = get_subjects_keyboard(subjects)

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 3

    def test_get_confirmation_keyboard(self):
        from remove_subject import get_confirmation_keyboard

        keyboard = get_confirmation_keyboard(1, "Математика")

        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2


# ==================== ТЕСТЫ ДЛЯ REMINDERS.PY ====================

class TestReminders:
    """Тесты для напоминаний"""

    async def test_remind_command(self, mock_message):
        from reminders import show_remind_commands

        await show_remind_commands(mock_message)

        mock_message.answer.assert_called_once()
        assert "Доступные команды" in mock_message.answer.call_args[0][0]


# ==================== ТЕСТЫ ДЛЯ ПАРСЕРОВ ====================

class TestExcelParser:
    """Тесты для парсера Excel"""

    @patch('parsers.excel_parser.openpyxl.load_workbook')
    def test_parse_excel_schedule_file_not_found(self, mock_load):
        from parsers.excel_parser import parse_excel_schedule

        mock_load.side_effect = FileNotFoundError()

        result = parse_excel_schedule("nonexistent.xlsx")

        assert result == []


class TestPhotoParser:
    """Тесты для парсера фото"""

    @patch('parsers.photo_parser.pytesseract.image_to_string')
    @patch('parsers.photo_parser.Image.open')
    def test_ocr_photo(self, mock_image_open, mock_ocr):
        from parsers.photo_parser import ocr_photo

        mock_ocr.return_value = "Test text"

        result = ocr_photo("test.jpg")

        assert result == "Test text"


# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
