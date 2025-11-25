"""
GUI implementation for NikiVibes Image Processor.
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path
from typing import Callable, Optional
import logging


class NikiVibesGUI:
    """Main GUI application for NikiVibes Image Processor."""
    
    def __init__(self, config, process_callback: Callable):
        """
        Initialize the GUI.
        
        Args:
            config: Application configuration
            process_callback: Function to call when processing starts
        """
        self.config = config
        self.process_callback = process_callback
        self.root = tk.Tk()
        self.root.title("NikiVibes Image Processor")
        self.root.geometry("800x600")
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure('TButton', padding=5)
        self.style.configure('TLabel', padding=5)
        
        # Create main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection frame
        self.create_file_selection_frame()
        
        # Log display
        self.create_log_display()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.update_status("Готов")
        
        # Configure logging to display in the GUI
        self.setup_logging_handler()
    
    def create_file_selection_frame(self):
        """Create the file selection frame."""
        frame = ttk.LabelFrame(self.main_frame, text="Избор на файлове", padding="10")
        frame.pack(fill=tk.X, pady=5)
        
        # Input file
        ttk.Label(frame, text="Входен файл:").grid(row=0, column=0, sticky=tk.W)
        self.input_file_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.input_file_var, width=60).grid(
            row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(
            frame, 
            text="Избери...", 
            command=self.browse_input_file
        ).grid(row=0, column=2, padx=5)
        
        # Media export file
        ttk.Label(frame, text="Файл с медии:").grid(row=1, column=0, sticky=tk.W)
        self.media_file_var = tk.StringVar(value=str(self.config.media_export_path))
        ttk.Entry(frame, textvariable=self.media_file_var, width=60).grid(
            row=1, column=1, padx=5, sticky=tk.EW)
        ttk.Button(
            frame, 
            text="Избери...", 
            command=self.browse_media_file
        ).grid(row=1, column=2, padx=5)
        
        # Process button
        self.process_btn = ttk.Button(
            frame,
            text="Обработка",
            command=self.start_processing,
            state=tk.DISABLED
        )
        self.process_btn.grid(row=2, column=0, columnspan=3, pady=10)
        
        # Configure grid weights
        frame.columnconfigure(1, weight=1)
    
    def create_log_display(self):
        """Create the log display area."""
        frame = ttk.LabelFrame(self.main_frame, text="Дневник на събитията", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=('Consolas', 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text colors for different log levels
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("INFO", foreground="black")
    
    def setup_logging_handler(self):
        """Set up logging to display in the GUI."""
        class GuiLogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                try:
                    # Skip if widget is gone or app is closing
                    if self.text_widget is None:
                        return
                    if not self.text_widget.winfo_exists():
                        return
                    msg = self.format(record)
                    self.text_widget.configure(state='normal')
                    self.text_widget.insert(tk.END, msg + '\n', record.levelname)
                    self.text_widget.see(tk.END)
                    self.text_widget.configure(state='disabled')
                except tk.TclError:
                    # Widget is destroyed; ignore further logs to GUI
                    pass
        
        # Add the handler to the root logger
        handler = GuiLogHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def browse_input_file(self):
        """Open a file dialog to select the input file."""
        file_path = filedialog.askopenfilename(
            title="Изберете входен файл",
            filetypes=[("Excel файлове", "*.xlsx *.xls"), ("Всички файлове", "*.*")]
        )
        if file_path:
            self.input_file_var.set(file_path)
            self.update_process_button_state()
    
    def browse_media_file(self):
        """Open a file dialog to select the media export file."""
        file_path = filedialog.askopenfilename(
            title="Изберете файл с медии",
            filetypes=[("Excel файлове", "*.xlsx *.xls"), ("Всички файлове", "*.*")],
            initialdir=str(self.config.media_export_path.parent)
        )
        if file_path:
            self.media_file_var.set(file_path)
    
    def update_process_button_state(self):
        """Update the state of the process button based on input file selection."""
        if self.input_file_var.get():
            self.process_btn.config(state=tk.NORMAL)
        else:
            self.process_btn.config(state=tk.DISABLED)
    
    def start_processing(self):
        """Start the processing of the selected files."""
        from pathlib import Path
        input_file = Path(self.input_file_var.get())
        media_file = Path(self.media_file_var.get())
        
        if not input_file.exists():
            self.log_error(f"Файлът не е намерен: {input_file}")
            return
        
        if not media_file.exists():
            self.log_error(f"Файлът с медии не е намерен: {media_file}")
            return
        
        # Disable the process button during processing
        self.process_btn.config(state=tk.DISABLED)
        self.update_status("Обработване...")
        
        try:
            # Call the processing function in a separate thread
            import threading
            thread = threading.Thread(
                target=self.process_files,
                args=(input_file, media_file),
                daemon=True
            )
            thread.start()
        except Exception as e:
            self.log_error(f"Грешка при стартиране на обработката: {str(e)}")
            self.process_btn.config(state=tk.NORMAL)
            self.update_status("Грешка")
    
    def process_files(self, input_file: Path, media_file: Path):
        """Process the files (to be called in a separate thread)."""
        try:
            # Update config with selected files
            self.config.input_file_path = input_file
            self.config.media_export_path = media_file
            
            # Call the processing callback
            self.process_callback(self.config)
            
            # Update UI on success
            self.root.after(0, self.on_processing_complete, None)
        except Exception as e:
            self.root.after(0, self.on_processing_complete, str(e))
    
    def on_processing_complete(self, error: Optional[str] = None):
        """Called when processing is complete."""
        if error:
            self.log_error(f"Грешка при обработка: {error}")
            self.update_status("Грешка")
        else:
            self.log_info("Обработката завърши успешно!")
            self.update_status("Готово")
        
        # Re-enable the process button
        self.process_btn.config(state=tk.NORMAL)
    
    def log_info(self, message: str):
        """Log an info message."""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"{message}\n", "INFO")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
    
    def log_error(self, message: str):
        """Log an error message."""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"ГРЕШКА: {message}\n", "ERROR")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        logging.error(message)
    
    def update_status(self, message: str):
        """Update the status bar."""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def run(self):
        """Run the main application loop."""
        self.root.mainloop()
