import openpyxl


def parse_excel_schedule(file_path):
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        lessons = []

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row[0] or not row[3]:  # проверяем день и предмет
                continue

            day = row[0]
            subject = row[3]

            # Время начала (колонка B - индекс 1)
            if hasattr(row[1], 'strftime'):
                start_time = row[1].strftime("%H:%M")
            else:
                start_time = str(row[1])[:5] if row[1] else ""

            # Время конца (колонка C - индекс 2)
            if hasattr(row[2], 'strftime'):
                end_time = row[2].strftime("%H:%M")
            else:
                end_time = str(row[2])[:5] if row[2] else ""

            # Аудитория (колонка E - индекс 4)
            classroom = ""
            if len(row) > 4 and row[4]:
                classroom = str(row[4]).strip()

            # ТИП НЕДЕЛИ (колонка F - индекс 5) - ЭТО БЫЛО НЕПРАВИЛЬНО!
            week_type = "both"
            if len(row) > 5 and row[5]:  # индекс 5, а не 4!
                week_type_val = str(row[5]).strip().lower()
                # Поддерживаем разные варианты написания
                if week_type_val in ["even", "чётная", "четная", "even week", "чет"]:
                    week_type = "even"
                elif week_type_val in ["odd", "нечётная", "нечетная", "odd week", "нечет"]:
                    week_type = "odd"
                elif week_type_val in ["both", "каждая", "both week", "каж"]:
                    week_type = "both"

            lesson = {
                "day": day,
                "start_time": str(start_time).strip(),
                "end_time": str(end_time).strip(),
                "subject": str(subject).strip(),
                "classroom": classroom,
                "week_type": week_type  # Теперь правильный week_type
            }

            lessons.append(lesson)

        return lessons

    except FileNotFoundError:
        print(f"❌ Файл не найден: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        return []
