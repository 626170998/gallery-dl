import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import subprocess
import threading
import os
import sys
import re
import shlex


class GalleryDLGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gallery-DL GUI")
        self.root.geometry("1000x800")

        # 设置样式
        self.style = ttk.Style()
        self.style.configure('TButton', padding=5)
        self.style.configure('TFrame', padding=5)

        # 创建界面组件
        self.create_widgets()

        # 启动时自动获取帮助信息
        self.get_help()

        # 进程引用
        self.process = None

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题标签
        title_label = tk.Label(
            main_frame,
            text="Gallery-DL GUI Interface",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)

        # 命令输入框架
        cmd_frame = ttk.LabelFrame(main_frame, text="Command Input")
        cmd_frame.pack(fill=tk.X, pady=5)

        # 命令输入框和标签
        cmd_label = tk.Label(cmd_frame,
                             text="Enter gallery-dl command (you can include 'gallery-dl' prefix):")
        cmd_label.pack(anchor=tk.W, padx=5, pady=2)

        self.cmd_var = tk.StringVar()
        self.cmd_entry = ttk.Entry(cmd_frame, textvariable=self.cmd_var,
                                   width=80)
        self.cmd_entry.pack(fill=tk.X, padx=5, pady=5)
        self.cmd_entry.bind('<Return>',
                            lambda e: self.execute_command())  # 按回车执行命令

        # 常用命令按钮框架
        common_cmd_frame = ttk.Frame(cmd_frame)
        common_cmd_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(common_cmd_frame, text="--help",
                   command=lambda: self.cmd_var.set("--help")).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(common_cmd_frame, text="--version",
                   command=lambda: self.cmd_var.set("--version")).pack(
            side=tk.LEFT, padx=2)
        ttk.Button(common_cmd_frame, text="Clear",
                   command=lambda: self.cmd_var.set("")).pack(side=tk.LEFT,
                                                              padx=2)

        # 选项框架
        options_frame = ttk.Frame(cmd_frame)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        # 输出目录选择
        ttk.Label(options_frame, text="Output Directory:").pack(side=tk.LEFT,
                                                                padx=5)
        self.output_dir_var = tk.StringVar()
        output_dir_entry = ttk.Entry(options_frame,
                                     textvariable=self.output_dir_var,
                                     width=40)
        output_dir_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(options_frame, text="Browse",
                   command=self.select_output_dir).pack(side=tk.LEFT, padx=5)

        # 执行按钮框架
        button_frame = ttk.Frame(cmd_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="Execute Command",
                   command=self.execute_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Get Help",
                   command=self.get_help).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop Command",
                   command=self.stop_command).pack(side=tk.LEFT, padx=5)

        # 输出显示框架
        output_frame = ttk.LabelFrame(main_frame, text="Command Output")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 输出文本区域
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var,
                               relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=5)

    def select_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def execute_command(self):
        command = self.cmd_var.get().strip()
        if not command:
            messagebox.showwarning("Input Error", "Please enter a command")
            return

        # 在后台线程中执行命令，避免界面冻结
        threading.Thread(target=self.run_gallery_dl_command, args=(command,),
                         daemon=True).start()

    def stop_command(self):
        if self.process:
            try:
                self.process.terminate()
                self.append_output("\nCommand stopped by user.\n")
                self.update_status("Command stopped")
            except:
                self.append_output("\nFailed to stop command.\n")

    def get_help(self):
        self.cmd_var.set("--help")
        self.execute_command()

    def parse_command(self, command):
        """
        解析用户输入的命令，移除不必要的"gallery-dl"前缀
        并正确处理带引号的参数
        """
        # 使用shlex分割命令，正确处理带引号的参数
        try:
            parts = shlex.split(command)
        except ValueError as e:
            raise ValueError(f"Invalid command syntax: {e}")

        # 如果命令以"gallery-dl"开头，移除它
        if parts and (parts[0].lower() == "gallery-dl" or
                      parts[0].endswith("gallery-dl") or
                      parts[0].endswith("gallery-dl.exe")):
            parts = parts[1:]

        return parts

    def run_gallery_dl_command(self, command):
        # 更新状态
        self.root.after(0, self.update_status, f"Parsing command: {command}")

        # 清空文本区域并显示正在执行的消息
        self.root.after(0, self.clear_output)
        self.root.after(0, self.append_output, f"> {command}\n")
        self.root.after(0, self.append_output,
                        "Parsing and executing command...\n\n")

        try:
            # 解析命令
            parsed_args = self.parse_command(command)

            # 构建完整的命令
            full_command = ["gallery-dl"]

            # 如果有输出目录，添加到命令中
            output_dir = self.output_dir_var.get().strip()
            if output_dir:
                full_command.extend(["-o", f"base-directory={output_dir}"])

            # 添加用户解析后的命令参数
            full_command.extend(parsed_args)

            # 显示实际执行的命令
            self.root.after(0, self.append_output,
                            f"Executing: {' '.join(full_command)}\n\n")

            # 执行 gallery-dl 命令
            self.process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # 实时读取输出
            while True:
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    self.root.after(0, self.append_output, output)

            # 获取剩余输出和错误信息
            stdout, stderr = self.process.communicate()

            if stdout:
                self.root.after(0, self.append_output, stdout)
            if stderr:
                self.root.after(0, self.append_output, f"\nErrors:\n{stderr}")

            return_code = self.process.poll()
            self.root.after(0, self.append_output,
                            f"\nCommand completed with return code: {return_code}")
            self.root.after(0, self.update_status,
                            f"Command completed (return code: {return_code})")

        except ValueError as e:
            error_msg = f"Command parsing error: {str(e)}"
            self.root.after(0, self.append_output, error_msg)
            self.root.after(0, self.update_status,
                            "Error: Invalid command syntax")
        except FileNotFoundError:
            error_msg = "Error: gallery-dl not found. Please make sure it is installed and available in your PATH."
            self.root.after(0, self.append_output, error_msg)
            self.root.after(0, self.update_status,
                            "Error: gallery-dl not found")
        except Exception as e:
            error_msg = f"\nUnexpected error: {str(e)}"
            self.root.after(0, self.append_output, error_msg)
            self.root.after(0, self.update_status, f"Error: {str(e)}")
        finally:
            self.process = None

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)

    def append_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)  # 自动滚动到底部

    def update_status(self, text):
        self.status_var.set(text)


def main():
    # 创建主窗口
    root = tk.Tk()

    # 创建应用程序实例
    app = GalleryDLGUI(root)

    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
