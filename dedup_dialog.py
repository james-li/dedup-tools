import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from dedup_utils import dedup_files_in_directory, get_file_info
from file_preview_utils import file_preview
from PIL import Image, ImageTk


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.preview_label = None
        self.previews = {}
        self.treeview = None
        self.window = None
        self.directory_var = None
        self.last_select_item = None
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        # 输入框
        self.window = self.master
        self.window.title("Duplicate Files Finder")
        self.window.geometry("800x600")

        # input frame
        input_frame = ttk.Frame(self.window, padding=10)
        input_frame.pack(side=tk.TOP, fill=tk.X)

        self.directory_var = tk.StringVar()
        directory_entry = ttk.Entry(input_frame, textvariable=self.directory_var)
        directory_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_button = ttk.Button(input_frame, text="Browse", command=self.browse_directory)
        browse_button.pack(side=tk.LEFT, padx=(10, 0))

        scan_button = ttk.Button(input_frame, text="Scan", command=self.scan_directory)
        scan_button.pack(side=tk.LEFT, padx=(10, 0))

        # result frame
        result_frame = ttk.Frame(self.window, padding=10)
        result_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # treeview
        self.treeview = ttk.Treeview(result_frame, columns=("size", "created"))
        self.treeview.heading("#0", text="Filename")
        self.treeview.heading("size", text="Size")
        self.treeview.heading("created", text="Created")
        self.treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.treeview.bind("<<TreeviewSelect>>", self.show_preview)

        # preview frame
        preview_frame = ttk.Frame(result_frame, padding=10)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(preview_frame, textvariable="preview", font=("TkDefaultFont", 12), anchor="w")
        self.preview_label.pack(side=tk.TOP, fill=tk.X)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_var.set(directory)

    def scan_directory(self):
        directory = self.directory_var.get()
        if directory:
            self.previews = {}
            self.last_select_item = None
            self.preview_label.configure(text=None, image=None)
            file_lists = dedup_files_in_directory(directory)
            self.treeview.delete(*self.treeview.get_children())
            for files in file_lists:
                parent_node = self.treeview.insert("", tk.END,
                                                   text=os.path.relpath(files[0], directory),
                                                   values=get_file_info(files[0]))
                for file in files[1:]:
                    self.treeview.insert(parent_node, tk.END,
                                         text=os.path.relpath(file, directory),
                                         values=get_file_info(file))

    def show_preview(self, event):
        selected_item = self.treeview.parent(self.treeview.selection()[0])
        if not selected_item:
            selected_item = self.treeview.selection()[0]
        if selected_item == self.last_select_item:
            return
        self.last_select_item = selected_item
        if not self.previews.get(selected_item):
            preview_content = file_preview(
                os.path.join(self.directory_var.get(), self.treeview.item(selected_item, "text")))
            self.previews[selected_item] = preview_content
        else:
            preview_content = self.previews[selected_item]
        if isinstance(preview_content, str):
            self.preview_label.configure(text=preview_content, image=None)
        elif preview_content:
            # isinstance(preview_content, Image):
            image = preview_content.resize((100, 100))
            photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=photo, text=None)


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()
