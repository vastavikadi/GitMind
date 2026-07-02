"""
GitMind — CLI

The main command-line interface for GitMind. Provides 6 commands:

    gitmind story     — Narrative of repo history
    gitmind ask       — Ask questions about your repo
    gitmind recover   — Reflog analysis + recovery suggestions
    gitmind suggest   — Proactive suggestions
    gitmind explain   — Explain a commit, file, or feature
    gitmind project   — Understand the current project / repository

Usage:
    gitmind story --days 7 --detailed
    gitmind ask "why was this function added?"
    gitmind ask --chat
    gitmind recover
    gitmind suggest
    gitmind explain abc1234
    gitmind explain src/main.py
"""

from __future__ import annotations

from typing import Optional

# need to remove this before publishing
import traceback

import typer
from rich.console import Console

# Load configuration first (loads .env)
import config

from utils.banner import print_banner
from utils.output import (
    print_response,
    print_error,
    print_info,
    print_warning,
    spinner,
    console as rich_console,
    get_chat_input,
    print_chat_response,
)

app = typer.Typer(
    name="gitmind",
    help="Understand your repository's past, present, and future.",
    add_completion=False,
    no_args_is_help=True,
)

# gitmind story

@app.command()
def story(
    days: int = typer.Option(7, "--days", "-d", help="Number of days of history to analyze."),
    detailed: bool = typer.Option(False, "--detailed", help="Include file-level changes."),
    quickoverview: bool = typer.Option(False, "--quickoverview", "-q", help="Quick topic-based overview (no AI)."),
    by: str = typer.Option("date", "--by", "-b", help="Group commits by: date, author."),
    ai: bool = typer.Option(True, "--ai/--no-ai", help="Use AI for narrative generation."),
):
    """
    📖 Generate a narrative story of your repository's history.

    Uses AI to analyze commits, group them by feature/theme,
    and tell the story of what was built and why.
    """
    print_banner("GitMind Story")

    if quickoverview or not ai:
        # Using the non-AI story generator
        from tools.story.get_commits import get_recent_commits
        from tools.story.quick_overview import OverviewGenerator
        from tools.story.story_generator import StoryGenerator

        commits = get_recent_commits(days=days)

        if not commits:
            print_warning("No commits found in the specified time range.")
            return

        if quickoverview:
            generator = OverviewGenerator(commits)
            overview = generator.overview()
            rich_console.print(overview)
        else:
            generator = StoryGenerator(commits)
            narrative = generator.generate(detailed=detailed, by=by)
            rich_console.print(narrative)
    else:
        # Using the AI-powered story pipeline
        from workflows.orchestrator import run_story

        with spinner(f"Analyzing {days} days of commit history..."):
            result = run_story(days=days, detailed=detailed)

        print_response(result, title="Repository Story")


#  gitmind ask

@app.command()
def ask(
    question: Optional[str] = typer.Argument(None, help="Your question about the repository."),
    chat: bool = typer.Option(False, "--chat", "-c", help="Start a multi-turn chat session."),
):
    """
    💬 Ask questions about your repository.

    Single-shot mode (default):
        gitmind ask "why was this function added?"

    Multi-turn chat mode:
        gitmind ask --chat
    """
    print_banner("GitMind Ask")

    from workflows.orchestrator import run_query

    if chat:
        # Multi-turn conversation mode
        print_info("Chat mode active. Type 'exit' to quit.\n")

        while True:
            user_input = get_chat_input()
            if user_input is None:
                print_info("Goodbye!")
                break

            if not user_input:
                continue

            with spinner("Thinking..."):
                result = run_query(user_input, command="ask") #check this one

            print_chat_response(result)

    else:
        # Single-shot mode
        if not question:
            print_error("Please provide a question or use --chat for interactive mode.")
            print_info('Usage: gitmind ask "your question here"')
            raise typer.Exit(1)

        with spinner("Analyzing..."):
            result = run_query(question, command="ask")

        print_response(result, title="Answer")


#  gitmind recover

@app.command()
def recover():
    """
    🔧 Analyze reflog and suggest recovery steps.

    Scans the reflog and git fsck to find lost commits, deleted
    branches, and forgotten stashes. Provides step-by-step
    recovery commands.
    """
    print_banner("GitMind Recover")

    from workflows.orchestrator import run_recover

    with spinner("Scanning reflog and checking for dangling objects..."):
        result = run_recover()

    print_response(result, title="Recovery Plan")


#  gitmind suggest

@app.command()
def suggest():
    """
    💡 Get proactive suggestions for your repository.

    Analyzes the current state and provides actionable
    recommendations without you asking a specific question.
    """
    print_banner("GitMind Suggest")

    from workflows.orchestrator import run_suggest

    with spinner("Analyzing repository state..."):
        result = run_suggest()

    print_response(result, title="Suggestions")


#  gitmind explain

@app.command()
def explain(
    target: str = typer.Argument(..., help="Commit hash, file path, or feature name to explain."),
):
    """
    🔍 Explain a commit, file, or feature.

    Traces the history and provides context from commits,
    PRs, and issues.

    Examples:
        gitmind explain abc1234        # explain a commit
        gitmind explain src/main.py    # explain a file's history
        gitmind explain "auth system"  # explain a feature
    """
    print_banner("GitMind Explain")

    from workflows.orchestrator import run_explain

    with spinner(f"Investigating '{target}'..."):
        result = run_explain(target) # Check this one

    print_response(result, title=f"Explanation: {target}")


#  gitmind project

@app.command()
def project(
    question: Optional[str] = typer.Argument(None, help="Optional question about the project (default: full overview)."),
):
    """
    🏗️ Understand the current project / repository.

    Analyzes README, docs, package metadata, and repository
    structure to explain what the project is, its architecture,
    technologies, and how to get started.

    Examples:
        gitmind project                          # full overview
        gitmind project "what does this do?"     # specific question
        gitmind project "how do I set this up?"  # setup instructions
    """
    print_banner("GitMind Project")

    from workflows.orchestrator import run_project

    with spinner("Analyzing project documentation and structure..."):
        result = run_project(query=question or "")

    print_response(result, title="Project Overview")


#  gitmind index (utility command for vector store)

@app.command()
def index(
    days: int = typer.Option(90, "--days", "-d", help="Number of days of history to index."),
):
    """
    📇 Index repository data into the vector store for semantic search.

    Embeds commit messages, PR descriptions, and issue descriptions
    into ChromaDB for semantic search capabilities.
    """
    print_banner("GitMind Index")

    from tools.story.get_commits import get_recent_commits
    from embeddings.vector_store import GitMindVectorStore

    print_info(f"Indexing commits from the last {days} days...")

    with spinner("Fetching commits..."):
        commits = get_recent_commits(days=days)

    if not commits:
        print_warning("No commits found to index.")
        return

    print_info(f"Found {len(commits)} commits. Embedding...")

    with spinner(f"Embedding {len(commits)} commits..."):
        store = GitMindVectorStore()
        store.index_commits(commits)

    # Try indexing GitHub data if token is available
    if config.has_github_token():
        try:
            from github_integration.github_client import GitHubClient

            print_info("Indexing GitHub PRs and issues...")

            with spinner("Fetching from GitHub..."):
                client = GitHubClient(token=config.GITHUB_TOKEN)
                prs = client.get_prs(limit=50)
                issues = client.get_issues(limit=50)

            with spinner(f"Embedding {len(prs)} PRs and {len(issues)} issues..."):
                store.index_prs(prs)
                store.index_issues(issues)

            print_info(f"Indexed {len(prs)} PRs and {len(issues)} issues.")
        except Exception as e:
            # traceback.print_exc() # use for debugging
            print_warning(f"Could not index GitHub data: {e}")

    from utils.output import print_success
    total = store.count() if store else len(commits)
    print_success(f"Indexed {total} documents into the vector store.")


if __name__ == "__main__":
    app()