import os
from markitdown import MarkItDown

# --- КОНФИГУРАЦИЯ ---
INPUT_FOLDER = "input_files"
OUTPUT_FOLDER = "output_md"

def process_files():
    # 1. Проверка дали съществува папката с входни файлове
    if not os.path.exists(INPUT_FOLDER):
        print(f" Грешка: Папката '{INPUT_FOLDER}' не съществува.")
        return

    # 3. Инициализиране на MarkItDown
    md = MarkItDown()

    # 4. Взимане на списък с файлове
    files = os.listdir(INPUT_FOLDER)
    
    # Филтрираме само файлове (игнорираме папки) и скрити файлове
    files = [f for f in files if os.path.isfile(os.path.join(INPUT_FOLDER, f)) and not f.startswith('.')]

    if not files:
        print("Папката е празна.")
        return

    print(f"Обработване на {len(files)} файла...\n")

    # 5. Цикъл през всеки файл
    for filename in files:
        input_path = os.path.join(INPUT_FOLDER, filename)
        
        # Смяна на разширението на .md
        file_base_name = os.path.splitext(filename)[0]
        output_filename = f"{file_base_name}.md"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        print(f"Обработва се: {filename} ...", end=" ")

        try:
            # Същинското конвертиране
            result = md.convert(input_path)
            
            # Записване на резултата
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.text_content)
            
            print("Готово!")

        except Exception as e:
            print(f"\n Грешка при файла {filename}: {e}")

    print("\n Всички операции приключиха.")

if __name__ == "__main__":
    process_files()