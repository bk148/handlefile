from rich.console import Console
from rich.table import Table
from rich.progress import Progress

class View:
    def __init__(self):
        self.console = Console()

    def display_message(self, message, style="green"):
        self.console.print(f"[{style}]{message}[/{style}]")

    def display_error(self, error_message):
        self.console.print(f"[red]{error_message}[/red]")

    def display_table(self, data, title="Data Table"):
        table = Table(title=title)

        # Assuming data is a list of dictionaries
        if data and isinstance(data, list) and isinstance(data[0], dict):
            for key in data[0].keys():
                table.add_column(key)

            for item in data:
                table.add_row(*[str(item[key]) for key in item.keys()])

            self.console.print(table)
        else:
            self.display_error("Invalid data format for table display.")

    def display_progress(self, total, description="Processing..."):
        with Progress() as progress:
            task = progress.add_task(description, total=total)
            while not progress.finished:
                progress.update(task, advance=1)
                time.sleep(0.1)  # Simulate work being done

    def get_user_input(self, prompt):
        return self.console.input(f"[cyan]{prompt}[/cyan] ")