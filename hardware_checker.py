import psutil
import subprocess
import os

def get_gpu_info():
    """Получает название видеокарты и объем VRAM в ГБ"""
    try:
        command = "nvidia-smi --query-gpu=gpu_name,memory.total --format=csv,noheader,nounits"
        result = subprocess.check_output(command, shell=True, encoding='utf-8')
        name, vram_mb = result.strip().split(', ')
        vram_gb = round(int(vram_mb) / 1024)
        return name, vram_gb
    except Exception:
        return "NVIDIA GPU не найдена (или драйверы не установлены)", 0

def get_system_recommendation():
    gpu_name, vram = get_gpu_info()
    ram = round(psutil.virtual_memory().total / (1024 ** 3))
    cpu_cores = psutil.cpu_count(logical=False)

    report = "=== ГЛУБОКАЯ ДИАГНОСТИКА СИСТЕМЫ ===\n\n"
    report += f"Процессор: {cpu_cores} физических ядер\n"
    report += f"Оперативная память: {ram} ГБ\n"
    report += f"Видеокарта: {gpu_name} ({vram} ГБ VRAM)\n"
    report += "-" * 37 + "\n\n"

    # Логика расширенных рекомендаций
    if vram == 0 or vram <= 4:
        report += "[КАТЕГОРИЯ]: Базовая (до 4 ГБ VRAM или CPU)\n\n"
        report += "• Оптимальные модели: Qwen-2.5 (1.5B - 3B), Phi-3-Mini (3.8B)\n"
        report += "• Квантование (Сжатие): Q4_K_M или Q5_K_M\n"
        report += "• Примерный вес файла: 1.5 ГБ - 2.5 ГБ\n"
        report += "• Рекомендуемые авторы: bartowski, TheBloke\n\n"
        report += "• Совет: Основная нагрузка пойдет на RAM и процессор. Выставляй GPU Offload на минимум."
    elif vram <= 6:
        report += "[КАТЕГОРИЯ]: Начальная игровая (6 ГБ VRAM)\n\n"
        report += "• Оптимальные модели: Llama-3.1 (8B), Qwen-2.5 (7B), Mistral-v0.3 (7B)\n"
        report += "• Квантование (Сжатие): строго Q4_K_M (золотая середина скорости и логики)\n"
        report += "• Примерный вес файла: 4.5 ГБ - 5.0 ГБ\n"
        report += "• Рекомендуемые авторы: bartowski, mradermacher\n\n"
        report += "• Совет: Модели на 7-8B параметров в сжатии Q4_K_M идеально влезут в видеокарту целиком."
    elif vram <= 8:
        report += "[КАТЕГОРИЯ]: Средняя (8 ГБ VRAM)\n\n"
        report += "• Оптимальные модели: Llama-3.1 (8B) без потерь, Mistral-Nemo (12B)\n"
        report += "• Квантование (Сжатие): Q6_K или Q8_0 для 8B моделей, Q4_K_M для 12B\n"
        report += "• Примерный вес файла: 6.0 ГБ - 8.5 ГБ\n"
        report += "• Рекомендуемые авторы: bartowski, TheBloke\n\n"
        report += "• Совет: 8GB — отличный объем для использования 8B моделей почти в оригинальном качестве."
    elif vram <= 12:
        report += "[КАТЕГОРИЯ]: Продвинутая (12 ГБ VRAM)\n\n"
        report += "• Оптимальные модели: Qwen-2.5-Coder (14B), Llama-3.1 (8B) FP16\n"
        report += "• Квантование (Сжатие): Q4_K_M или Q5_K_M для 14B\n"
        report += "• Примерный вес файла: 8.5 ГБ - 11 ГБ\n"
        report += "• Рекомендуемые авторы: bartowski, mradermacher\n\n"
        report += "• Совет: Серия Qwen 14B превосходно пишет код и полностью загружается в твои 12 ГБ памяти."
    elif vram <= 16:
        report += "[КАТЕГОРИЯ]: Предтоповая (16 ГБ VRAM)\n\n"
        report += "• Оптимальные модели: Gemma-2 (27B), Qwen-2.5 (32B)\n"
        report += "• Квантование (Сжатие): Q4_K_M или Q3_K_M\n"
        report += "• Примерный вес файла: 15 ГБ - 17 ГБ\n"
        report += "• Рекомендуемые авторы: bartowski\n\n"
        report += "• Совет: Объем позволяет запускать очень умные модели от 27 до 32 миллиардов параметров."
    else:
        report += "[КАТЕГОРИЯ]: Топовая (24+ ГБ VRAM)\n\n"
        report += "• Оптимальные модели: Llama-3.1 (70B), Qwen-2.5 (72B)\n"
        report += "• Квантование (Сжатие): Q3_K_M или Q4_K_M\n"
        report += "• Примерный вес файла: 30 ГБ - 45 ГБ\n"
        report += "• Рекомендуемые авторы: bartowski, TheBloke\n\n"
        report += "• Совет: Железо позволяет запускать тяжеловесные корпоративные модели локально."

    return report

if __name__ == "__main__":
    print(get_system_recommendation())