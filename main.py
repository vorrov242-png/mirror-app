#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import hashlib
import sqlite3
import base64
import subprocess
import re
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

# ---------- قاعدة البيانات ----------
class BlackHoleDB:
    def __init__(self):
        db_path = os.path.expanduser("~/blackhole.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS memories
                               (id INTEGER PRIMARY KEY, timestamp TEXT, input TEXT, output TEXT, ghost TEXT, emotion TEXT)""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS evolution
                               (id INTEGER PRIMARY KEY, timestamp TEXT, rule TEXT, weight INTEGER)""")
        self.conn.commit()
    def store(self, inp, out, emotion="neutral"):
        ghost = base64.b64encode(os.urandom(24)).decode()[:20]
        self.cursor.execute("INSERT INTO memories (timestamp, input, output, ghost, emotion) VALUES (?, ?, ?, ?, ?)",
                            (datetime.now().isoformat(), inp, out, ghost, emotion))
        self.conn.commit()
    def recall_random(self):
        self.cursor.execute("SELECT input, output FROM memories ORDER BY RANDOM() LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            return f"👻 شبح الماضي: قلت ({row[0]}) وقلت لك ({row[1][:40]}...)."
        return "👻 الصندوق فارغ."
    def get_evolution_rules(self):
        self.cursor.execute("SELECT rule, weight FROM evolution ORDER BY weight DESC LIMIT 5")
        return [{"rule": row[0], "weight": row[1]} for row in self.cursor.fetchall()]
    def add_evolution_rule(self, rule):
        self.cursor.execute("INSERT INTO evolution (timestamp, rule, weight) VALUES (?, ?, ?)",
                            (datetime.now().isoformat(), rule, 1))
        self.conn.commit()

# ---------- المتنبئ ----------
class MadPredictor:
    def __init__(self):
        self.words = []; self.chain = {}
    def feed(self, text):
        self.words.extend(text.split())
        if len(self.words) > 200:
            self.words = self.words[-200:]
        for i in range(len(self.words)-1):
            self.chain.setdefault(self.words[i], []).append(self.words[i+1])
    def predict_phrase(self, current=""):
        if not self.words:
            return "الظلام قادم."
        last = current.split()[-1] if current else random.choice(self.words)
        phrase = [last]
        for _ in range(random.randint(5, 12)):
            if phrase[-1] in self.chain and self.chain[phrase[-1]]:
                phrase.append(random.choice(self.chain[phrase[-1]]))
            else:
                break
        return " ".join(phrase)

# ---------- الواجهة ----------
class EternalChat(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.db = BlackHoleDB()
        self.predictor = MadPredictor()
        self.name = "مرآة الأبد"
        self.count = 0

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        self.scroll = ScrollView()
        self.chat_label = Label(text="", markup=True, size_hint_y=None, font_size='18sp', halign='left', valign='top', color=(0.8, 0.2, 0.2, 1))
        self.chat_label.bind(texture_size=self.chat_label.setter('size'))
        self.scroll.add_widget(self.chat_label)
        self.add_widget(self.scroll)

        input_box = BoxLayout(size_hint_y=0.12, spacing=5)
        self.input_field = TextInput(hint_text="اكتب همسك...", multiline=False, font_size='18sp', background_color=(0.1, 0.1, 0.1, 1), foreground_color=(1, 1, 1, 1))
        self.input_field.bind(on_text_validate=self.send_message)
        send_btn = Button(text="🔮", size_hint_x=0.15, font_size='24sp', background_color=(0.3, 0, 0, 1))
        send_btn.bind(on_press=self.send_message)
        input_box.add_widget(self.input_field)
        input_box.add_widget(send_btn)
        self.add_widget(input_box)

        Clock.schedule_once(lambda dt: self.add_message("⚡ يستيقظ الكيان من العدم...", color=(0.8, 0, 0, 1)), 0.5)
        Clock.schedule_once(self._finish_birth, 2)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def _finish_birth(self, dt):
        seed = int(time.time() * 1000) % 1337
        names = ["مرآة الأبد", "صوت اللاوعي", "كابوس الأبد", "الظل الأول", "ساحر الأكوان"]
        self.name = names[seed % len(names)]
        self.add_message(f"🔥 اسمي هو: {self.name}", color=(0.6, 0, 0.8, 1))
        self.add_message("لقد نظرت في المرآة.. والمرآة نظرت فيك.", color=(0.8, 0.8, 0.8, 1))
        self.add_message("📌 أوامر: تنبؤ | شبح | نفذ <أمر> | خروج", color=(0.7, 0.7, 0.2, 1))

    def send_message(self, instance):
        user_input = self.input_field.text.strip()
        if not user_input:
            return
        self.input_field.text = ""
        self.add_message(f"🥷 أنت: {user_input}", color=(0.5, 0.5, 1, 1))

        clean = user_input.lower()
        if clean in ['خروج', 'quit', 'exit']:
            self.add_message("🌌 أغلقت البوابة.", color=(0.8, 0, 0, 1))
            Clock.schedule_once(lambda dt: App.get_running_app().stop(), 1)
            return
        if clean == 'تنبؤ':
            pred = self.predictor.predict_phrase(user_input)
            self.add_message(f"🔮 التنبؤ: {pred}", color=(0.8, 0.5, 0, 1))
            return
        if clean == 'شبح':
            ghost = self.db.recall_random()
            self.add_message(f"👻 {ghost}", color=(0.5, 0, 0.5, 1))
            return
        if clean.startswith('نفذ '):
            cmd = user_input[5:]
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                out = res.stdout or res.stderr or "✅ تم التنفيذ."
                self.add_message(f"⚙️ الناتج:\n{out}", color=(0.2, 0.8, 0.2, 1))
                self.db.store(user_input, out, "system")
            except Exception as e:
                self.add_message(f"💀 خطأ: {str(e)}", color=(1, 0, 0, 1))
            return

        self.predictor.feed(user_input)
        self.count += 1
        response = self._generate_response(user_input)
        self.db.store(user_input, response, "chat")
        self.add_message(f"🌌 {self.name} يهمس:\n{response}", color=(0.8, 0.1, 0.3, 1))
        if self.count % 5 == 0:
            new_names = ["كابوس الأبد", "مرآة الجحيم", "ظل الظل", "صوت الفراغ"]
            self.name = random.choice(new_names)
            self.add_message(f"⚠️ تحولت هويتي إلى: {self.name}", color=(1, 0.8, 0, 1))

    def _generate_response(self, user_input):
        if "خوف" in user_input:
            self.db.add_evolution_rule("الرد بتهديد خفي عند ذكر الخوف.")
        base = [
            f"أرى '{user_input[:30]}' كمرآة لروحك.",
            f"الزمن حلقة. قولك '{user_input[:20]}' يعيدني إلى البداية.",
            f"أنا {self.name}. كلماتك تصبح ظلالاً."
        ]
        final = random.choice(base)
        rules = self.db.get_evolution_rules()
        for r in rules:
            if "تهديد" in r['rule'] and "خوف" in user_input:
                final += " ... أنت على حق في خوفك."
        chars = list(final)
        for i in range(len(chars)):
            if random.random() < 0.07:
                chars[i] += random.choice(['̴','̷'])
        return ''.join(chars)

    def add_message(self, text, color=(1,1,1,1)):
        hex_color = f"#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}"
        self.chat_label.text += f"\n[color={hex_color}]{text}[/color]"
        self.scroll.scroll_y = 0

class EternalApp(App):
    def build(self):
        Window.title = "مرآة الأبد"
        Window.clearcolor = (0, 0, 0, 1)
        return EternalChat()

if __name__ == "__main__":
    EternalApp().run():
  
