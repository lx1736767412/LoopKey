import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import time
import random
import threading
import keyboard
import sv_ttk
import json
import os

# 配置文件路径
CONFIG_FILE = "macro_config.json"


class HardcoreMacroFinal:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("循环点 - LoopKey v1.1")
        self.root.geometry("1100x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.tasks = []
        self.is_running = False
        self.all_keys = self._get_categorized_keys()
        self.running_thread = None
        
        # 强制浅色模式
        sv_ttk.set_theme("light")
        
        self.setup_ui()
        self.load_config() # 启动时加载配置
        self.setup_hotkeys()
        

    def _get_categorized_keys(self):
        letters = sorted(list("abcdefghijklmnopqrstuvwxyz"))
        numbers = sorted(list("0123456789"))
        f_keys = [f'f{i}' for i in range(1, 13)]
        func = sorted(['enter','esc', 'shift', 'ctrl', 'alt', 'space', 'backspace', 
                       'tab', 'capslock', 'delete', 'up', 'down', 'left', 'right'])
        py_keys = set(pyautogui.KEYBOARD_KEYS)
        return [k for k in (letters + numbers + f_keys + func) if k in py_keys]

    def setup_ui(self):
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("微软雅黑", 10, "bold"), padding=10, relief="flat")
        style.configure("Treeview", rowheight=38, font=("微软雅黑", 10))
        style.configure("Accent.TButton", font=("微软雅黑", 10, "bold"))

        # 直接进入功能容器，不再留标题空隙
        main_box = ttk.Frame(self.root, padding=25)
        main_box.pack(fill=tk.BOTH, expand=True)

        body = ttk.Frame(main_box)
        body.pack(fill=tk.BOTH, expand=True)

        # 【左侧】：选择与配置
        left_col = ttk.Frame(body, width=320)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 35))
        left_col.pack_propagate(False)

        ttk.Label(left_col, text="● 选择按键 (双击添加)", font=("微软雅黑", 10, "bold")).pack(anchor="w")
        
        self.search_entry = ttk.Entry(left_col)
        self.search_entry.pack(fill=tk.X, pady=(10, 8))
        self.search_entry.insert(0, "搜索按键...")
        self.search_entry.bind("<FocusIn>", lambda e: self._handle_placeholder(True))
        self.search_entry.bind("<FocusOut>", lambda e: self._handle_placeholder(False))
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_keys())

        self.key_listbox = tk.Listbox(
            left_col, font=("Consolas", 12), bg="#ffffff", borderwidth=1, 
            relief="solid", highlightthickness=0, selectbackground="#0078d4"
        )
        self.key_listbox.pack(fill=tk.BOTH, expand=True)
        self.key_listbox.bind('<Double-1>', lambda e: self.add_task())
        self.filter_keys()

        # 参数配置
        param_group = ttk.LabelFrame(left_col, text=" 动作预设 ", padding=15)
        param_group.pack(fill=tk.X, pady=(20, 0))

        ttk.Label(param_group, text="按下时长 (s):").pack(anchor="w")
        self.dur_entry = ttk.Entry(param_group); self.dur_entry.insert(0, "0.1")
        self.dur_entry.pack(fill=tk.X, pady=(5, 12))

        ttk.Label(param_group, text="之后延迟 (s):").pack(anchor="w")
        self.delay_entry = ttk.Entry(param_group); self.delay_entry.insert(0, "0.5")
        self.delay_entry.pack(fill=tk.X, pady=(5, 18))

        ttk.Button(param_group, text="➕ 添加至序列", style="Accent.TButton", command=self.add_task).pack(fill=tk.X, ipady=5)

        # 【右侧】：执行序列
        right_col = ttk.Frame(body)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 管理按钮在上方
        top_action = ttk.Frame(right_col)
        top_action.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(top_action, text="● 执行流程序列", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(top_action, text="全部清空", command=self.clear_tasks).pack(side=tk.RIGHT)
        ttk.Button(top_action, text="删除选中项", command=self.delete_selected).pack(side=tk.RIGHT, padx=10)
        
        self.tree = ttk.Treeview(right_col, columns=("key", "dur", "delay"), show='headings')
        self.tree.heading("key", text="按键名称")
        self.tree.heading("dur", text="持续时间")
        self.tree.heading("delay", text="之后延迟")
        self.tree.column("key", anchor="center")
        self.tree.column("dur", anchor="center", width=120)
        self.tree.column("delay", anchor="center", width=120)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 循环设置
        loop_group = ttk.LabelFrame(right_col, text=" 🌀 全局循环间歇 (Loop Delay) ", padding=20)
        loop_group.pack(fill=tk.X, pady=(20, 0))

        lb_frame = ttk.Frame(loop_group)
        lb_frame.pack(fill=tk.X)
        ttk.Label(lb_frame, text="序列跑完一遍后随机停顿:").pack(side=tk.LEFT)
        self.loop_min = ttk.Entry(lb_frame, width=8); self.loop_min.insert(0, "2.0")
        self.loop_min.pack(side=tk.LEFT, padx=10)
        ttk.Label(lb_frame, text="至").pack(side=tk.LEFT)
        self.loop_max = ttk.Entry(lb_frame, width=8); self.loop_max.insert(0, "5.0")
        self.loop_max.pack(side=tk.LEFT, padx=10)
        ttk.Label(lb_frame, text="秒 (无限循环)").pack(side=tk.LEFT, padx=5)

        # --- 底部控制 ---
        footer = ttk.Frame(main_box, padding=(0, 25, 0, 0))
        footer.pack(fill=tk.X)
        
        status_box = ttk.Frame(footer)
        status_box.pack(side=tk.LEFT)
        self.indicator = tk.Label(status_box, text="●", fg="#bbb", font=("Arial", 20))
        self.indicator.pack(side=tk.LEFT)
        self.status_msg = ttk.Label(status_box, text="就绪 | F9/F10 控制", font=("微软雅黑", 11))
        self.status_msg.pack(side=tk.LEFT, padx=15)

        btn_box = ttk.Frame(footer)
        btn_box.pack(side=tk.RIGHT)
        ttk.Button(btn_box, text=" 停止脚本 (F10) ", command=self.toggle_stop).pack(side=tk.RIGHT, padx=5)
        self.start_btn = ttk.Button(btn_box, text=" 启动脚本 (F9) ", style="Accent.TButton", command=self.toggle_start)
        self.start_btn.pack(side=tk.RIGHT, padx=5)
        
        # 添加提示标签
        info_label = ttk.Label(footer, text="注意：请合理使用此工具 | 关闭窗口自动保存配置", font=("微软雅黑", 9))
        info_label.pack(side=tk.BOTTOM, pady=(10, 0))

    # 逻辑处理
    def _handle_placeholder(self, is_focus_in):
        val = self.search_entry.get()
        if is_focus_in and val == "搜索按键...":
            self.search_entry.delete(0, tk.END)
        elif not is_focus_in and not val:
            self.search_entry.insert(0, "搜索按键...")

    def filter_keys(self):
        term = self.search_entry.get().lower()
        if term == "搜索按键...": term = ""
        self.key_listbox.delete(0, tk.END)
        for k in self.all_keys:
            if term in k.lower():
                self.key_listbox.insert(tk.END, k.upper())

    def add_task(self):
        sel = self.key_listbox.curselection()
        if not sel: return
        key = self.key_listbox.get(sel[0])
        try:
            dur_val = float(self.dur_entry.get())
            delay_val = float(self.delay_entry.get())
            if dur_val <= 0 or delay_val < 0:
                messagebox.showerror("输入错误", "持续时间必须大于0，延迟时间不能小于0！")
                return
                
            self.tasks.append({
                "key": key.lower(), "display": key, 
                "dur": dur_val, 
                "delay": delay_val
            })
            self.update_tree()
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数字！")
        except Exception as e:
            messagebox.showerror("错误", f"添加失败: {str(e)}")

    def update_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, t in enumerate(self.tasks):
            self.tree.insert("", tk.END, values=(t['display'], f"{t['dur']}s", f"{t['delay']}s"), tags=(f"item_{idx}",))
            # 如果是偶数行，添加浅灰色背景
            if idx % 2 == 0:
                self.tree.tag_configure(f"item_{idx}", background="#f9f9f9")

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请选择要删除的项目！")
            return
            
        for item in selected_items:
            index = self.tree.index(item)
            del self.tasks[index]
        self.update_tree()

    def clear_tasks(self):
        if not self.tasks:
            return
            
        if not messagebox.askyesno("确认", "确定要清空所有任务吗？"):
            return
            
        self.tasks.clear()
        self.update_tree()

    # 配置保存与读取
    def save_config(self):
        try:
            config = {
                "tasks": self.tasks,
                "loop_min": self.loop_min.get(),
                "loop_max": self.loop_max.get(),
                "default_dur": self.dur_entry.get(),
                "default_delay": self.delay_entry.get()
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.tasks = config.get("tasks", [])
                    self.update_tree()
                    self.loop_min.delete(0, tk.END); self.loop_min.insert(0, config.get("loop_min", "2.0"))
                    self.loop_max.delete(0, tk.END); self.loop_max.insert(0, config.get("loop_max", "5.0"))
                    self.dur_entry.delete(0, tk.END); self.dur_entry.insert(0, config.get("default_dur", "0.1"))
                    self.delay_entry.delete(0, tk.END); self.delay_entry.insert(0, config.get("default_delay", "0.5"))
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败: {str(e)}")

    def on_closing(self):
        if self.is_running:
            self.toggle_stop()
            time.sleep(0.1)  # 等待线程结束
        self.save_config()
        self.root.quit()
        self.root.destroy()

    # 运行引擎
    def run_engine(self):
        while self.is_running:
            for t in self.tasks:
                if not self.is_running: break
                try:
                    pyautogui.keyDown(t['key'])
                    time.sleep(t['dur'])
                    pyautogui.keyUp(t['key'])
                    self._safe_sleep(t['delay'])
                except Exception as e:
                    print(f"执行按键 {t['key']} 时出错: {str(e)}")
                    break
                    
            if not self.is_running: break
            try:
                l_min, l_max = float(self.loop_min.get()), float(self.loop_max.get())
                if l_max >= l_min:
                    sleep_time = random.uniform(l_min, l_max)
                else:
                    sleep_time = l_min
                self._safe_sleep(sleep_time)
            except ValueError:
                self._safe_sleep(1)  # 默认睡眠1秒
            except Exception as e:
                print(f"计算循环延迟时出错: {str(e)}")
                self._safe_sleep(1)

    def _safe_sleep(self, duration):
        end_t = time.time() + duration
        while time.time() < end_t and self.is_running:
            time.sleep(0.05)

    def toggle_start(self):
        if not self.is_running and self.tasks:
            self.is_running = True
            self.indicator.config(fg="#28a745")
            self.status_msg.config(text="正在无限循环... | F9暂停 F10停止")
            self.start_btn.config(text="暂停脚本 (F9)")
            self.start_btn.config(command=self.toggle_pause)
            self.running_thread = threading.Thread(target=self.run_engine, daemon=True)
            self.running_thread.start()
        elif self.is_running:
            self.toggle_pause()

    def toggle_pause(self):
        if self.is_running:
            self.is_running = False
            self.indicator.config(fg="#ffc107")
            self.status_msg.config(text="已暂停 | F9继续 F10停止")
            self.start_btn.config(text="继续脚本 (F9)")
            self.start_btn.config(command=self.continue_script)
        else:
            self.toggle_continue()

    def continue_script(self):
        if not self.is_running and self.tasks:
            self.is_running = True
            self.indicator.config(fg="#28a745")
            self.status_msg.config(text="正在无限循环... | F9暂停 F10停止")
            self.start_btn.config(text="暂停脚本 (F9)")
            self.start_btn.config(command=self.toggle_pause)
            self.running_thread = threading.Thread(target=self.run_engine, daemon=True)
            self.running_thread.start()

    def toggle_stop(self):
        self.is_running = False
        self.indicator.config(fg="#dc3545")
        self.status_msg.config(text="已停止 | F9重启")
        self.start_btn.config(text="启动脚本 (F9)")
        self.start_btn.config(command=self.toggle_start)
        self.start_btn.config(state=tk.NORMAL)

    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('f9', self.toggle_start)
            keyboard.add_hotkey('f10', self.toggle_stop)
        except Exception as e:
            print(f"注册热键失败: {str(e)}")


if __name__ == "__main__":
    app = HardcoreMacroFinal()
    app.root.mainloop()