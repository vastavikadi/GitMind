"""
GitMind — Answer Synthesizer

Merges outputs from multiple agents into one coherent response.
Handles deduplication, conflict resolution, and Rich formatting.
"""

from __future__ import annotations

from config import get_llm


SYNTHESIS_PROMPT = """You are an answer synthesizer for GitMind.

You receive outputs from multiple specialist agents and must merge them
into one coherent, well-structured response for the user.

Rules:
1. Combine information from all agents without repetition.
2. If agents provide conflicting information, note the discrepancy.
3. Prioritize actionable insights over raw data.
4. Structure the response with clear sections if multiple topics are covered.
5. Keep the response concise but comprehensive.
6. Preserve specific details: commit hashes, PR numbers, file paths, dates.
7. Use GitHub-Flavored Markdown (GFM) formatting for readability.
8. Use ATX headings, fenced code blocks with language identifiers, inline code
   for technical terms, and Markdown tables when comparing information.
9. Do NOT output HTML, XML, or ANSI escape sequences.
10. Do NOT wrap the entire response in a code block.

Agent outputs will be provided as labeled sections."""


def synthesize(agent_outputs: dict[str, str], original_query: str) -> str:
    """
    Merge outputs from multiple agents into one coherent response.

    Args:
        agent_outputs: dict mapping agent name to its output string
        original_query: the user's original query

    Returns:
        A synthesized response string
    """
    # response - if only one agent responded
    if len(agent_outputs) == 1:
        return list(agent_outputs.values())[0]

    # response - if no agents responded
    if not agent_outputs:
        return "I wasn't able to find relevant information for your query."

    # Multiple agents — using LLM to synthesize
    context_parts = []
    for agent_name, output in agent_outputs.items():
        context_parts.append(f"--- {agent_name.upper()} AGENT OUTPUT ---\n{output}")

    context = "\n\n".join(context_parts)

    llm = get_llm(temperature=0)

    response = llm.invoke(
        f"{SYNTHESIS_PROMPT}\n\n"
        f"Original user query: {original_query}\n\n"
        f"{context}\n\n"
        f"Synthesized response:"
    )

    return response.content
