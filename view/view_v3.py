from rich.console import Console

class ConsoleView:
    def __init__(self):
        self.console = Console()

    def show_message(self, message):
        self.console.print(f"[blue]{message}[/blue]")

    def show_success(self, message):
        self.console.print(f"[green]{message}[/green]")

    def show_error(self, message):
        self.console.print(f"[red]{message}[/red]")