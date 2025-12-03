import json
import os

# --- КОНФИГУРАЦИЯ ---

INPUT_JSON = "input_files/products.json" 
OUTPUT_TEXT = "output_md/products_optimized.md"

def optimize_products():
    if not os.path.exists(INPUT_JSON):
        print(f"Грешка: Не намирам файла '{INPUT_JSON}'.")
        return

    try:
        print(f"📖 Четене на {INPUT_JSON}...")
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data if isinstance(data, list) else []

        if not products:
            print("Файлът изглежда празен или структурата не е списък.")
            return

        print(f"Открити са {len(products)} продукта...")

        with open(OUTPUT_TEXT, 'w', encoding='utf-8') as f:

            f.write("СПИСЪК С ПРОДУКТИ НА FOREVER LIVING PRODUCTS И ТЕХНИТЕ ЦЕНИ:\n\n")

            for prod in products:
                # Извличане на данните
                name = prod.get('Име', 'Неизвестен продукт')
                price = prod.get('Цена', 'Цена при запитване')
                desc = prod.get('Описание', 'Няма описание').replace("\n", " ") 
                ingr = prod.get('Състав', 'Няма данни за състава')
                usage = prod.get('Начин на употреба', 'Виж етикета')

                entry = (
                    f"=== ПРОДУКТ: {name} ===\n"
                    f"Име на продукта: {name}\n"
                    f"Цена: {price}\n"
                    f"Съставки: {ingr}\n"
                    f"Начин на употреба: {usage}\n"
                    f"Описание и ползи: {desc}\n"
                    f"--------------------------------------------------\n\n" 
                )
                
                f.write(entry)
        
        print(f"Създаден е файл '{OUTPUT_TEXT}'.")

    except Exception as e:
        print(f"Възникна грешка: {e}")

if __name__ == "__main__":
    optimize_products()