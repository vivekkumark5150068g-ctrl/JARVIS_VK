import json
import os
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup

DATA_FILE = "jarvis_data.json"

DEFAULT_DATA = {
    "rules": [
        "Study every day",
        "Exercise for health",
        "Sleep on time",
        "Avoid unnecessary phone usage"
    ],
    "tasks": [],
    "timetable": {
        "09:00": "College starts",
        "16:20": "College ends",
        "18:00": "Study / Skill Growth",
        "20:00": "Dinner",
        "21:00": "Revision",
        "22:30": "Sleep preparation"
    }
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class JarvisApp(App):
    def build(self):
        self.title = "JARVIS V1.1.1"
        self.data = load_data()

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        self.header = Label(
            text="🤖 JARVIS V1.1.1\nYour Personal Assistant",
            font_size=dp(24),
            size_hint_y=None,
            height=dp(90)
        )
        root.add_widget(self.header)

        self.status = Label(
            text="ONLINE • " + datetime.now().strftime("%d-%m-%Y  %I:%M %p"),
            size_hint_y=None,
            height=dp(35)
        )
        root.add_widget(self.status)

        self.output = Label(
            text="Welcome. JARVIS is ready.",
            halign="left",
            valign="top",
            size_hint_y=None
        )
        self.output.bind(texture_size=lambda *_: setattr(self.output, "height", self.output.texture_size[1] + dp(20)))

        scroll = ScrollView()
        scroll.add_widget(self.output)
        root.add_widget(scroll)

        self.command = TextInput(
            hint_text="Type a command...",
            multiline=False,
            size_hint_y=None,
            height=dp(50)
        )
        self.command.bind(on_text_validate=lambda *_: self.run_command())
        root.add_widget(self.command)

        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
        for text, cmd in [
            ("Rules", "rules"),
            ("Timetable", "timetable"),
            ("Tasks", "tasks"),
            ("Summary", "summary"),
        ]:
            b = Button(text=text)
            b.bind(on_press=lambda _, c=cmd: self.handle(c))
            row.add_widget(b)
        root.add_widget(row)

        send = Button(text="▶  RUN COMMAND", size_hint_y=None, height=dp(55))
        send.bind(on_press=lambda *_: self.run_command())
        root.add_widget(send)

        Clock.schedule_interval(self.update_clock, 30)
        return root

    def update_clock(self, *_):
        self.status.text = "ONLINE • " + datetime.now().strftime("%d-%m-%Y  %I:%M %p")

    def run_command(self):
        cmd = self.command.text.strip().lower()
        self.command.text = ""
        if cmd:
            self.handle(cmd)

    def write(self, text):
        self.output.text = text

    def handle(self, cmd):
        if cmd in ("rules", "rule", "1"):
            self.show_rules()
        elif cmd in ("timetable", "schedule", "2"):
            self.show_timetable()
        elif cmd in ("tasks", "task", "5"):
            self.show_tasks()
        elif cmd in ("summary", "7"):
            self.show_summary()
        elif cmd in ("time", "8"):
            self.write("⏰ Current time: " + datetime.now().strftime("%I:%M %p"))
        elif cmd in ("date", "9"):
            self.write("📅 Today: " + datetime.now().strftime("%d %B %Y"))
        elif cmd.startswith("add task "):
            task = cmd[9:].strip()
            if task:
                self.data["tasks"].append({"task": task, "completed": False})
                save_data(self.data)
                self.write("✅ Task added:\n" + task)
        elif cmd.startswith("add rule "):
            rule = cmd[9:].strip()
            if rule:
                self.data["rules"].append(rule)
                save_data(self.data)
                self.write("✅ Rule added:\n" + rule)
        elif cmd.startswith("complete "):
            try:
                n = int(cmd.split()[1]) - 1
                if 0 <= n < len(self.data["tasks"]):
                    self.data["tasks"][n]["completed"] = True
                    save_data(self.data)
                    self.write("✅ Task completed.")
                else:
                    self.write("❌ Invalid task number.")
            except Exception:
                self.write("Use: complete 1")
        elif cmd in ("help", "?"):
            self.write(
                "COMMANDS\n\n"
                "rules\n"
                "timetable\n"
                "tasks\n"
                "summary\n"
                "time\n"
                "date\n"
                "add task <task>\n"
                "add rule <rule>\n"
                "complete <number>"
            )
        else:
            self.write("🤖 I don't know that command yet.\nTry: help")

    def show_rules(self):
        text = "📜 DAILY RULES\n\n"
        for i, rule in enumerate(self.data["rules"], 1):
            text += f"{i}. {rule}\n"
        self.write(text)

    def show_timetable(self):
        text = "🕒 DAILY TIMETABLE\n\n"
        for t, activity in self.data["timetable"].items():
            text += f"{t}  →  {activity}\n"
        self.write(text)

    def show_tasks(self):
        if not self.data["tasks"]:
            self.write("📝 TASKS\n\nNo tasks yet.\n\nUse:\nadd task your task")
            return
        text = "📝 TASKS\n\n"
        for i, item in enumerate(self.data["tasks"], 1):
            mark = "✅" if item["completed"] else "⬜"
            text += f"{i}. {mark} {item['task']}\n"
        self.write(text)

    def show_summary(self):
        completed = sum(x["completed"] for x in self.data["tasks"])
        pending = len(self.data["tasks"]) - completed
        self.write(
            "🤖 DAILY SUMMARY\n\n"
            f"📅 {datetime.now().strftime('%d-%m-%Y')}\n"
            f"⏰ {datetime.now().strftime('%I:%M %p')}\n\n"
            f"📜 Rules: {len(self.data['rules'])}\n"
            f"✅ Completed tasks: {completed}\n"
            f"⬜ Pending tasks: {pending}\n"
        )

if __name__ == "__main__":
    JarvisApp().run()
