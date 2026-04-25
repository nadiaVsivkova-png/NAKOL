import openpyxl


def parse_excel_schedule(file_path):
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        lessons = []

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row[0] or not row[3]:
                continue

            day = row[0]
            subject = row[3]

            if hasattr(row[1], 'strftime'):
                start_time = row[1].strftime("%H:%M")
            else:
                start_time = str(row[1])[:5] if row[1] else ""

            if hasattr(row[2], 'strftime'):
                end_time = row[2].strftime("%H:%M")
            else:
                end_time = str(row[2])[:5] if row[2] else ""

            lesson = {
                "day": str(day).strip(),
                "start_time": str(start_time).strip(),
                "end_time": str(end_time).strip(),
                "subject": str(subject).strip()
            }

            lessons.append(lesson)

        return lessons

    except FileNotFoundError:
        print(f"❌ Файл не найден: {file_path}")
        return []
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        return []
