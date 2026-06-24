import typer
from rich_pyfiglet import RichFiglet
from rich.console import Console

from tools.story.get_commits import get_recent_commits
from tools.story.quick_overview import OverviewGenerator
from tools.story.story_generator import StoryGenerator

app = typer.Typer()
console = Console(markup=False)

@app.command()
def story(days: int = 7):
    commits = get_recent_commits(days=days)

    if not commits:
        print("[red]No commits found[/red]")
        return

    generator = StoryGenerator(commits)
    narrative = generator.generate(detailed=True, RichFiglet=RichFiglet, console=console)
    console.print(narrative)


if __name__ == "__main__":
    app()