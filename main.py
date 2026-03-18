"""
LoopKey - 桌面自动化宏工具
一个自动循环按键宏工具，用于游戏或重复性操作场景
"""

import json
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import keyboard
import pynput.keyboard as kb


class MacroConfig:
    """宏配置数据类"""
    
    def __init__(self):
        self.tasks = []  # 任务序列列表
        self.min_pause = 2.0  # 最小随机停顿时间
        self.max_pause = 5.0  # 最大随机停顿时间
        self.default_duration = 0.1  # 默认按下时长
        self.default_delay = 0.5  # 默认后延迟
    
    def to_dict(self) -> dict:
        return {
            'tasks': self.tasks,
            'min_pause': self.min_pause,
            'max_pause': self.max_pause,
            'default_duration': self.default_duration,
            'default_delay': self.default_delay,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MacroConfig':
        config = cls()
        config.tasks = data.get('tasks', [])
        config.min_pause = data.get('min_pause', 2.0)
        config.max_pause = data.get('max_pause', 5.0)
        config.default_duration = data.get('default_duration', 0.1)
        config.default_delay = data.get('default_delay', 0.5)
        return config


class ConfigManager:
    """配置管理器"""
    
    CONFIG_FILE = Path(__file__).parent / 'macro_config.json'
    
    @staticmethod
    def save(config: MacroConfig) -> bool:
        try:
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败：{e}")
            return False
    
    @staticmethod
    def load() -> MacroConfig:
        if not ConfigManager.CONFIG_FILE.exists():
            return MacroConfig()
        try:
            with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return MacroConfig.from_dict(data)
        except Exception as e:
            print(f"加载配置失败：{e}")
            return MacroConfig()


class MacroEngine:
    """宏执行引擎"""
    
    def __init__(self):
        self.controller = kb.Controller()
        self.is_running = False
        self.is_paused = False
        self._thread = None
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
    
    def start(self, tasks: list, min_pause: float, max_pause: float):
        """启动宏执行"""
        if self.is_running:
            return
        
        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self._pause_event.set()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(tasks, min_pause, max_pause),
            daemon=True
        )
        self._thread.start()
    
    def pause(self):
        """暂停宏执行"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self._pause_event.clear()
    
    def resume(self):
        """恢复宏执行"""
        if self.is_running and self.is_paused:
            self.is_paused = False
            self._pause_event.set()
    
    def stop(self):
        """停止宏执行"""
        if self.is_running:
            self.is_running = False
            self._stop_event.set()
            self._pause_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
            self._thread = None
    
    def _run_loop(self, tasks: list, min_pause: float, max_pause: float):
        """主执行循环"""
        while self.is_running and not self._stop_event.is_set():
            # 执行一轮任务序列
            for task in tasks:
                if not self.is_running or self._stop_event.is_set():
                    break
                
                # 等待暂停状态解除
                self._pause_event.wait()
                
                try:
                    key_name = task['key']
                    # 尝试获取特殊功能键
                    if hasattr(kb.Key, key_name):
                        key = getattr(kb.Key, key_name)
                    else:
                        # 对于字母和数字，转换为小写以兼容 pynput
                        key = kb.KeyCode.from_char(key_name.lower())
                    
                    duration = task.get('duration', 0.1)
                    delay = task.get('delay', 0.5)
                    
                    # 按下键
                    self.controller.press(key)
                    time.sleep(duration)
                    # 释放键
                    self.controller.release(key)
                    # 后延迟
                    time.sleep(delay)
                except (ValueError, AttributeError):
                    continue
            
            # 随机停顿
            if self.is_running and not self._stop_event.is_set():
                pause_time = random.uniform(min_pause, max_pause)
                end_time = time.time() + pause_time
                while time.time() < end_time and self.is_running and not self._stop_event.is_set():
                    self._pause_event.wait(timeout=0.1)


class LoopKeyApp:
    """LoopKey 主应用程序"""
    
    # 可用按键列表 - 按字母、数字、其他分类
    KEYS = (
        [chr(c) for c in range(ord('A'), ord('Z') + 1)] +  # 字母 A-Z
        [str(i) for i in range(10)] +  # 数字 0-9
        [f'F{i}' for i in range(1, 13)] +  # 功能键 F1-F12
        ['space', 'tab', 'enter', 'backspace', 'escape', 'ctrl', 'alt', 'shift',
         'up', 'down', 'left', 'right', 'insert', 'delete', 'home', 'end',
         'page_up', 'page_down', 'caps_lock', 'num_lock', 'scroll_lock']  # 其他功能键
    )
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LoopKey - 桌面自动化宏工具")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        self.config = ConfigManager.load()
        self.engine = MacroEngine()
        
        self._setup_ui()
        self._load_tasks_to_table()
        self._update_status("就绪 - 按 F7 启动/停止")
        self._register_hotkeys()
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_ui(self):
        """设置用户界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 左侧面板 - 按键选择
        left_panel = ttk.LabelFrame(main_frame, text="按键选择", padding="10")
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left_panel.rowconfigure(0, weight=1)
        
        # 搜索框
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.insert(0, "搜索按键...")
        search_entry.bind("<FocusIn>", lambda e: self._on_search_focus_in())
        search_entry.bind("<FocusOut>", lambda e: self._on_search_focus_out())
        search_entry.bind("<KeyRelease>", lambda e: self._filter_keys())
        
        # 添加按钮
        add_btn = ttk.Button(search_frame, text="添加", command=self._add_selected_key)
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 按键列表
        keys_frame = ttk.Frame(left_panel)
        keys_frame.pack(fill=tk.BOTH, expand=True)
        
        self.keys_listbox = tk.Listbox(keys_frame, font=('Consolas', 10))
        self.keys_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        keys_scrollbar = ttk.Scrollbar(keys_frame, orient=tk.VERTICAL, 
                                       command=self.keys_listbox.yview)
        keys_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.keys_listbox.config(yscrollcommand=keys_scrollbar.set)
        self.keys_listbox.bind('<Double-Button-1>', lambda e: self._add_selected_key())
        
        self._populate_keys_list()
        
        # 右侧面板 - 执行序列
        right_panel = ttk.LabelFrame(main_frame, text="执行序列", padding="10")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        
        # 任务表格
        columns = ('key', 'duration', 'delay')
        self.task_tree = ttk.Treeview(right_panel, columns=columns, show='headings', height=18)
        self.task_tree.heading('key', text='按键名称')
        self.task_tree.heading('duration', text='持续时间 (秒)')
        self.task_tree.heading('delay', text='延迟时间 (秒)')
        self.task_tree.column('key', width=150)
        self.task_tree.column('duration', width=100)
        self.task_tree.column('delay', width=100)
        self.task_tree.grid(row=0, column=0, sticky="nsew")
        self.task_tree.bind('<Double-Button-1>', self._edit_task)
        
        task_scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, 
                                       command=self.task_tree.yview)
        task_scrollbar.grid(row=0, column=1, sticky="ns")
        self.task_tree.config(yscrollcommand=task_scrollbar.set)
        
        # 任务操作按钮
        task_btn_frame = ttk.Frame(right_panel)
        task_btn_frame.grid(row=1, column=0, pady=(10, 0), sticky="w")
        
        delete_btn = ttk.Button(task_btn_frame, text="删除选中", command=self._delete_selected_task)
        delete_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_btn = ttk.Button(task_btn_frame, text="清空所有", command=self._clear_all_tasks)
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 顺序调整按钮
        up_btn = ttk.Button(task_btn_frame, text="上移", command=self._move_task_up)
        up_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        down_btn = ttk.Button(task_btn_frame, text="下移", command=self._move_task_down)
        down_btn.pack(side=tk.LEFT)
        
        # 底部面板区域
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.columnconfigure(1, weight=1)
        
        # 按键参数面板（左侧）
        param_frame = ttk.LabelFrame(bottom_frame, text="按键参数", padding="10")
        param_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        param_frame.columnconfigure(1, weight=1)
        param_frame.columnconfigure(3, weight=1)
        
        ttk.Label(param_frame, text="默认按下时长 (秒):").grid(row=0, column=0, padx=(0, 5))
        self.default_duration_var = tk.StringVar(value=str(self.config.default_duration))
        ttk.Entry(param_frame, textvariable=self.default_duration_var, width=10).grid(row=0, column=1, padx=(0, 20), sticky="w")
        
        ttk.Label(param_frame, text="默认后延迟 (秒):").grid(row=0, column=2, padx=(0, 5))
        self.default_delay_var = tk.StringVar(value=str(self.config.default_delay))
        ttk.Entry(param_frame, textvariable=self.default_delay_var, width=10).grid(row=0, column=3, sticky="w")
        
        # 循环设置面板（右侧）
        cycle_frame = ttk.LabelFrame(bottom_frame, text="循环设置", padding="10")
        cycle_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        cycle_frame.columnconfigure(1, weight=1)
        cycle_frame.columnconfigure(3, weight=1)
        
        ttk.Label(cycle_frame, text="最小停顿时间 (秒):").grid(row=0, column=0, padx=(0, 5))
        self.min_pause_var = tk.StringVar(value=str(self.config.min_pause))
        min_pause_entry = ttk.Entry(cycle_frame, textvariable=self.min_pause_var, width=10)
        min_pause_entry.grid(row=0, column=1, padx=(0, 20), sticky="w")
        
        ttk.Label(cycle_frame, text="最大停顿时间 (秒):").grid(row=0, column=2, padx=(0, 5))
        self.max_pause_var = tk.StringVar(value=str(self.config.max_pause))
        max_pause_entry = ttk.Entry(cycle_frame, textvariable=self.max_pause_var, width=10)
        max_pause_entry.grid(row=0, column=3, sticky="w")
        
        # 控制与状态面板
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        self.start_btn = ttk.Button(control_frame, text="启动 (F7)", command=self._start_macro)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(control_frame, text="停止 (F8)", command=self._stop_macro, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = ttk.Label(control_frame, text="", foreground="gray")
        self.status_label.pack(side=tk.RIGHT)
    
    def _populate_keys_list(self):
        """填充按键列表"""
        self.keys_listbox.delete(0, tk.END)
        for key in self.KEYS:
            self.keys_listbox.insert(tk.END, key)
    
    def _filter_keys(self, *args):
        """过滤按键列表"""
        if not hasattr(self, 'keys_listbox'):
            return
        
        search_text = self.search_var.get().lower().strip()
        if search_text and search_text != "搜索按键...":
            self.keys_listbox.delete(0, tk.END)
            for key in self.KEYS:
                if search_text in key.lower():
                    self.keys_listbox.insert(tk.END, key)
        else:
            self._populate_keys_list()
    
    def _on_search_focus_in(self):
        """搜索框获得焦点"""
        if self.search_var.get() == "搜索按键...":
            self.search_var.set("")
    
    def _on_search_focus_out(self):
        """搜索框失去焦点"""
        if not self.search_var.get():
            self.search_var.set("搜索按键...")
    
    def _add_selected_key(self):
        """添加选中的按键到序列"""
        selection = self.keys_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个按键")
            return
        
        key = self.keys_listbox.get(selection[0])
        
        try:
            duration = float(self.default_duration_var.get())
            delay = float(self.default_delay_var.get())
        except ValueError:
            messagebox.showerror("错误", "按键参数必须是数字")
            return
        
        self.config.tasks.append({
            'key': key,
            'duration': duration,
            'delay': delay
        })
        
        self._refresh_task_table()
    
    def _refresh_task_table(self):
        """刷新任务表格"""
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        for task in self.config.tasks:
            self.task_tree.insert('', tk.END, values=(
                task['key'],
                f"{task['duration']:.2f}",
                f"{task['delay']:.2f}"
            ))
    
    def _load_tasks_to_table(self):
        """加载任务到表格"""
        self._refresh_task_table()
    
    def _delete_selected_task(self):
        """删除选中的任务"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的任务")
            return
        
        indices = [self.task_tree.index(item) for item in selection]
        for index in sorted(indices, reverse=True):
            del self.config.tasks[index]
        
        self._refresh_task_table()
    
    def _clear_all_tasks(self):
        """清空所有任务"""
        if not self.config.tasks:
            return
        
        if messagebox.askyesno("确认", "确定要清空所有任务吗？"):
            self.config.tasks.clear()
            self._refresh_task_table()
    
    def _edit_task(self, event):
        """编辑任务"""
        selection = self.task_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.task_tree.index(item)
        task = self.config.tasks[index]
        
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title("编辑任务")
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()
        
        # 设置对话框在主窗口中心显示
        edit_dialog.update_idletasks()
        dialog_width = 300
        dialog_height = 180
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog_width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog_height) // 2
        edit_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        ttk.Label(edit_dialog, text="持续时间 (秒):").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        duration_var = tk.StringVar(value=str(task['duration']))
        duration_entry = ttk.Entry(edit_dialog, textvariable=duration_var, width=20)
        duration_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(edit_dialog, text="延迟时间 (秒):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        delay_var = tk.StringVar(value=str(task['delay']))
        delay_entry = ttk.Entry(edit_dialog, textvariable=delay_var, width=20)
        delay_entry.grid(row=1, column=1, padx=10, pady=10)
        
        def save_edit():
            try:
                task['duration'] = float(duration_var.get())
                task['delay'] = float(delay_var.get())
                self._refresh_task_table()
                edit_dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "数值必须为数字", parent=edit_dialog)
        
        ttk.Button(edit_dialog, text="保存", command=save_edit).grid(row=2, column=0, columnspan=2, pady=20)
        edit_dialog.wait_window()
    
    def _move_task_up(self):
        """上移选中任务"""
        selection = self.task_tree.selection()
        if not selection:
            return
        
        index = self.task_tree.index(selection[0])
        if index > 0:
            self.config.tasks[index], self.config.tasks[index - 1] = \
                self.config.tasks[index - 1], self.config.tasks[index]
            self._refresh_task_table()
    
    def _move_task_down(self):
        """下移选中任务"""
        selection = self.task_tree.selection()
        if not selection:
            return
        
        index = self.task_tree.index(selection[0])
        if index < len(self.config.tasks) - 1:
            self.config.tasks[index], self.config.tasks[index + 1] = \
                self.config.tasks[index + 1], self.config.tasks[index]
            self._refresh_task_table()
    
    def _start_macro(self):
        """启动宏"""
        if not self.config.tasks:
            messagebox.showwarning("提示", "请先添加至少一个任务")
            return
        
        try:
            min_pause = float(self.min_pause_var.get())
            max_pause = float(self.max_pause_var.get())
            
            if min_pause < 0 or max_pause < 0:
                raise ValueError("时间不能为负数")
            if min_pause > max_pause:
                raise ValueError("最小值不能大于最大值")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            return
        
        self.engine.start(self.config.tasks, min_pause, max_pause)
        self.start_btn.config(text="运行中", state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self._update_status("运行中 - 按 F8 或点击停止按钮停止")
    
    def _stop_macro(self):
        """停止宏"""
        self.engine.stop()
        self.start_btn.config(text="启动 (F7)", state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._update_status("已停止 - 按 F7 启动")
    
    def _update_status(self, message: str):
        """更新状态文本"""
        self.status_label.config(text=message)
    
    def _register_hotkeys(self):
        """注册全局热键"""
        keyboard.add_hotkey('f7', self._on_f7_pressed, suppress=False)
        keyboard.add_hotkey('f8', self._on_f8_pressed, suppress=False)
    
    def _on_f7_pressed(self):
        """F7 热键处理 - 启动"""
        if not self.engine.is_running:
            self.root.after(0, self._start_macro)
    
    def _on_f8_pressed(self):
        """F8 热键处理 - 停止"""
        if self.engine.is_running:
            self.root.after(0, self._stop_macro)
    
    def _on_closing(self):
        """窗口关闭处理"""
        if self.engine.is_running:
            self.engine.stop()
        
        # 保存配置
        try:
            self.config.min_pause = float(self.min_pause_var.get())
            self.config.max_pause = float(self.max_pause_var.get())
            self.config.default_duration = float(self.default_duration_var.get())
            self.config.default_delay = float(self.default_delay_var.get())
        except ValueError:
            pass
        
        ConfigManager.save(self.config)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LoopKeyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
