from rich.console import Console
import logging

class View:
    def show_message(self, message):
        raise NotImplementedError("Subclasses must implement show_message")

    def show_success(self, message):
        raise NotImplementedError("Subclasses must implement show_success")

    def show_error(self, message):
        raise NotImplementedError("Subclasses must implement show_error")

class ConsoleView(View):
    def __init__(self):
        self.console = Console()

    def show_message(self, message):
        self.console.print(f"[blue]{message}[/blue]")

    def show_success(self, message):
        self.console.print(f"[green]{message}[/green]")

    def show_error(self, message):
        self.console.print(f"[red]{message}[/red]")

class FileView(View):
    def __init__(self, log_file="transfer_log.txt"):
        self.log_file = log_file

    def show_message(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"[INFO] {message}\n")

    def show_success(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"[SUCCESS] {message}\n")

    def show_error(self, message):
        with open(self.log_file, "a") as f:
            f.write(f"[ERROR] {message}\n")