"""
GitMind — Orchestrator

Main LangGraph workflow that ties everything together:
    User Query → Router → [Agent(s)] → Synthesizer → Response

This is the central entry point that the CLI calls.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import HumanMessage

from workflows.router import route_query, AgentType
from workflows.synthesizer import synthesize


# Agent Registry

def _invoke_agent(agent_type: AgentType, query: str) -> str:
    """Invoke a specific agent and return its response."""
    messages = [HumanMessage(content=query)]

    try:
        if agent_type == AgentType.HISTORY:
            from agents.history.history_agent import history_agent
            return history_agent.invoke(messages)

        elif agent_type == AgentType.RECOVERY:
            from agents.recovery.recovery_agent import recovery_agent
            return recovery_agent.invoke(messages)

        elif agent_type == AgentType.CODE:
            from agents.code.code_agent import code_agent
            return code_agent.invoke(messages)

        elif agent_type == AgentType.GITHUB:
            from agents.github.github_agent import github_agent
            return github_agent.invoke(messages)

        elif agent_type == AgentType.SUGGEST:
            from agents.suggest.suggest_agent import suggest_agent
            return suggest_agent.invoke(messages)

        elif agent_type == AgentType.DOCS:
            from agents.docs.docs_agent import docs_agent
            return docs_agent.invoke(messages)

        elif agent_type == AgentType.PROJECT:
            from agents.project.project_agent import project_agent
            return project_agent.invoke(messages)

        else:
            return f"Unknown agent type: {agent_type}"

    except Exception as e:
        return f"Error from {agent_type.value} agent: {e}"


# Main Orchestration


def run_query(query: str, command: Optional[str] = None) -> str:
    """
    Main orchestration function.

    Routes the query to appropriate agent(s), collects responses,
    and synthesizes a final answer.

    Args:
        query: User's natural language query
        command: Optional CLI command for fast-path routing

    Returns:
        Final synthesized response string
    """
    # Route is the first step
    routing = route_query(query, command=command)

    # Invoke agents - this is where my code invokes the agent
    agent_outputs: dict[str, str] = {}

    # Primary agent
    primary_result = _invoke_agent(routing.primary_agent, routing.rewritten_query)
    agent_outputs[routing.primary_agent.value] = primary_result

    # Secondary agents (if any)
    for secondary in routing.secondary_agents:
        try:
            secondary_result = _invoke_agent(secondary, routing.rewritten_query)
            agent_outputs[secondary.value] = secondary_result
        except Exception:
            pass  # Secondary agents failing shouldn't break the flow

    # Finally, Synthesize
    final_response = synthesize(agent_outputs, query)
    print(f"The final response from the 'run_query' in orchestrator.py function is: {final_response}")

    return final_response


def run_suggest() -> str:
    """
    Run the suggest agent directly (no routing needed).
    Used by `gitmind suggest` command.
    """
    return _invoke_agent(
        AgentType.SUGGEST,
        "Analyze the current state of this repository and provide proactive suggestions. "
        "Check for unpushed commits, uncommitted changes, rebase/merge state, "
        "force push risks, stale branches, and any potential issues."
    )


def run_recover() -> str:
    """
    Run the recovery agent directly (no routing needed).
    Used by `gitmind recover` command.
    """
    return _invoke_agent(
        AgentType.RECOVERY,
        "Analyze the reflog and git fsck output to find any recoverable work. "
        "Look for dangling commits, deleted branches, lost stashes, and recent "
        "destructive operations. Provide a complete recovery plan if anything is found."
    )


def run_story(days: int = 7, detailed: bool = False) -> str:
    """
    Run the history agent for storytelling.
    Used by `gitmind story` command (when using AI mode).
    """
    detail_note = "Include file-level changes for each commit." if detailed else ""
    return _invoke_agent(
        AgentType.HISTORY,
        f"Generate a narrative story of this repository's evolution over the last {days} days. "
        f"Group commits by feature/theme, identify major changes, and tell the story of "
        f"what was built and why. {detail_note}"
    )


def run_explain(target: str) -> str:
    """
    Explain a specific commit, file, or feature.
    Used by `gitmind explain` command.
    """
    query = (
        f"Explain '{target}' in the context of this repository. "
        f"If it's a commit hash, explain what the commit did and why. "
        f"If it's a file path, explain its history and evolution. "
        f"If it's a feature name, trace its development through commits. "
        f"Provide context from PRs and issues if available."
    )

    routing = route_query(query, command="explain")
    agent_outputs: dict[str, str] = {}

    primary_result = _invoke_agent(routing.primary_agent, query)
    agent_outputs[routing.primary_agent.value] = primary_result

    for secondary in routing.secondary_agents:
        try:
            secondary_result = _invoke_agent(secondary, query)
            agent_outputs[secondary.value] = secondary_result
        except Exception:
            pass

    return synthesize(agent_outputs, query)


def run_project(query: str = "") -> str:
    """
    Run the project agent directly (no routing needed).
    Used by `gitmind project` command.
    """
    if not query:
        query = (
            "Analyze this repository and provide a comprehensive overview. "
            "Explain what the project is, the problem it solves, the technologies "
            "used, the architecture, key components, and how to set it up."
        )
    return _invoke_agent(AgentType.PROJECT, query)
