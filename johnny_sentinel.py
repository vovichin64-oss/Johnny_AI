import os
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import sys
import json
import time
import winsound
from openai import OpenAI
from playsound import playsound
import random
import glob
import requests

# Заставляем Python игнорировать прокси для локальных связей
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

# --- НАСТРОЙКИ ---
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
is_working = True

try:
    model_vosk = Model("model")
    rec = KaldiRecognizer(model_vosk, 16000)
except Exception as e:
    print(f"[!] Ошибка модели Vosk: {e}")
    model_vosk = None

q = queue.Queue()

SKILLS_PATH = "./skills"
DICT_FILE = "corrections.txt"


def johnny_say(phrase_name):
    pattern = os.path.join("sounds", f"{phrase_name}_*.wav")
    variation_files = glob.glob(pattern)

    if variation_files:
        target_path = random.choice(variation_files)
        try:
            playsound(target_path)
        except Exception as e:
            print(f"[!] Ошибка воспроизведения звука: {e}")
    else:
        fallback = os.path.join("sounds", f"{phrase_name}.wav")
        if os.path.exists(fallback):
            try:
                playsound(fallback)
            except:
                pass


def callback(indata, frames, time, status):
    q.put(bytes(indata))


def listen_for_text(prompt_msg, beep=False):
    print(f"\n{prompt_msg}")
    if beep:
        winsound.Beep(1000, 200)

    while not q.empty():
        q.get()

    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            text = res['text'].strip()
            if text:
                return text


def load_corrections():
    corr = {}
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, val = line.split(":", 1)
                    corr[key.strip().lower()] = val.strip()
    return corr


def fix_task(text):
    corr = load_corrections()
    for word, replacement in corr.items():
        text = text.replace(word, replacement)
    return text


def find_existing_skill(task_text):
    if not os.path.exists(SKILLS_PATH):
        return None

    words_in_task = set(task_text.lower().split())
    skills = [f[:-3] for f in os.listdir(SKILLS_PATH) if f.endswith(".py")]

    for skill in skills:
        skill_name_words = set(skill.replace('_', ' ').lower().split())
        if skill_name_words.issubset(words_in_task):
            return skill
    return None


def start_listening(gui_app=None):
    if not model_vosk:
        print("[!] Модель не загружена. Проверь папку 'model'.")
        return

    print("--- ДЖОННИ v2.0 АКТИВИРОВАН И ЖДЕТ КОМАНДЫ ---")

    with sd.RawInputStream(samplerate=16000, blocksize=2000, dtype='int16',
                           channels=1, callback=callback):

        while is_working:
            data = q.get()
            if rec.AcceptWaveform(data):
                recognized_text = json.loads(rec.Result()).get("text", "").lower()
            else:
                partial = json.loads(rec.PartialResult())
                recognized_text = partial.get("partial", "").lower()

            if "джонни" in recognized_text:
                if gui_app:
                    gui_app.status_bar.configure(state="normal")
                    gui_app.status_bar.delete(0, "end")
                    gui_app.status_bar.insert(0, "Слушаю вас...")
                    gui_app.status_bar.configure(state="disabled")

                print("[!] Джонни проснулся!")
                rec.Reset()

                is_active = True
                last_activity_time = time.time()

                while is_active:
                    johnny_say("start")
                    task = listen_for_text("[СЛУШАЮ...] Говорите задачу:", beep=True)
                    task_fixed = fix_task(task).lower()

                    if not task_fixed or any(x in task_fixed for x in ["выход", "отмена", "стоп"]):
                        johnny_say("cancel")
                        is_active = False
                        break

                    last_activity_time = time.time()
                    print(f"[?] Обработка задачи: '{task_fixed}'")

                    existing_skill = find_existing_skill(task_fixed)
                    if existing_skill:
                        print(f"[!] Нашел готовый навык: {existing_skill}")
                        johnny_say("done")
                        try:
                            exec(open(os.path.join(SKILLS_PATH, f"{existing_skill}.py"), encoding="utf-8").read())
                        except Exception as e:
                            print(f"Ошибка в навыке: {e}")
                            johnny_say("error")

                        last_activity_time = time.time()
                        continue

                    johnny_say("confirm_ai")
                    ans = listen_for_text("УЧИСЬ или ОТМЕНА:", beep=True).lower()

                    if "учись" in ans or "запроси" in ans:
                        johnny_say("thinking")

                        # --- ЗАЩИТА ОТ ВЫЛЕТОВ И АВТОПОИСК МОДЕЛИ ---
                        active_model = "local-model"
                        try:
                            req = requests.get("http://localhost:1234/v1/models", timeout=1.5)
                            models_data = req.json()
                            if models_data.get("data") and len(models_data["data"]) > 0:
                                active_model = models_data["data"][0]["id"]
                        except Exception:
                            print("[!] Ошибка: Сервер LM Studio не отвечает.")
                            johnny_say("error")
                            if gui_app:
                                gui_app.status_bar.configure(state="normal")
                                gui_app.status_bar.delete(0, "end")
                                gui_app.status_bar.insert(0, "ОШИБКА: Сервер LM Studio выключен!")
                                gui_app.status_bar.configure(state="disabled")
                            continue

                        # --- ЗАПРОС К НЕЙРОСЕТИ ---
                        try:
                            print(f"[*] Используется модель: {active_model}")
                            response = client.chat.completions.create(
                                model=active_model,
                                messages=[
                                    {"role": "system",
                                     "content": "Ты - терминал Windows. Пиши ТОЛЬКО код Python без лишнего текста."},
                                    {"role": "user", "content": f"Напиши код Python для задачи: {task_fixed}"}
                                ]
                            )
                            code = response.choices[0].message.content.strip()

                            if gui_app:
                                gui_app.status_bar.configure(state="normal")
                                gui_app.status_bar.delete(0, "end")
                                gui_app.status_bar.insert(0, f"Задача: {task_fixed}")
                                gui_app.status_bar.configure(state="disabled")

                            if "```" in code:
                                code = code.split("```")[1].replace("python", "").split("```")[0].strip()

                            print(f"--- СГЕНЕРИРОВАННЫЙ КОД ---\n{code}\n-----------")

                            exec(code)
                            johnny_say("done")

                            johnny_say("save")
                            ans_save = listen_for_text("ЗАПОМНИ или НЕ НАДО:", beep=True).lower()

                            if "запомни" in ans_save:
                                skill_name = task_fixed.replace(" ", "_")[:30] + ".py"
                                if not os.path.exists(SKILLS_PATH):
                                    os.makedirs(SKILLS_PATH)
                                with open(os.path.join(SKILLS_PATH, skill_name), "w", encoding="utf-8") as f:
                                    f.write(code)
                                print(f"[!] Сохранил как {skill_name}")
                                johnny_say("saved")
                            else:
                                johnny_say("cancel")

                            last_activity_time = time.time()

                        except Exception as e:
                            print(f"[!] Ошибка ИИ: {e}")
                            johnny_say("error")
                    else:
                        johnny_say("cancel")
                        is_active = False
                        break

                    if time.time() - last_activity_time > 15:
                        is_active = False
                        break

            time.sleep(0.05)

    print("Поток Джонни остановлен.")

if __name__ == "__main__":
    start_listening()