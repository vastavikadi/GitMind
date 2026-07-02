"""
GitMind — Vector Store (LlamaIndex + ChromaDB)

Embeds commit messages, PR descriptions, and issue descriptions
for semantic search. Agents can query the vector store to find
relevant context when answering user questions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain.tools import tool

from config import CHROMA_PATH, get_embeddings


class GitMindVectorStore:
    """
    Persistent vector store using ChromaDB for semantic search
    over repository metadata (commits, PRs, issues, docs).
    """

    def __init__(self, collection_name: str = "gitmind", persist_dir: Optional[Path] = None):
        import chromadb
        from chromadb.api.shared_system_client import SharedSystemClient

        self._persist_dir = str(Path(persist_dir or CHROMA_PATH).resolve())
        self._collection_name = collection_name

        # Ensure the persist directory exists before ChromaDB tries to use it
        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)

        # Creating persistent ChromaDB client with retry for stale cache
        try:
            self._chroma_client = chromadb.PersistentClient(path=self._persist_dir)
        except KeyError:
            # ChromaDB's SharedSystemClient cache is stale — clear and retry
            SharedSystemClient._identifier_to_system.pop(self._persist_dir, None)
            self._chroma_client = chromadb.PersistentClient(path=self._persist_dir)

        self._collection = self._chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # LangChain embeddings model
        self._embeddings = None

    # get embeddings
    def _get_embeddings(self):
        """Lazy-load the embeddings model."""
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    # Indexing

    def index_commits(self, commits: list[dict], repo_id: str = "default"):
        """
        Embed and store commit messages for semantic search.

        Args:
            commits: list of dicts with keys: hash, message, author, date
            repo_id: identifier for the repository
        """
        if not commits:
            return

        documents = []
        ids = []
        metadatas = []

        for commit in commits:
            doc_id = f"{repo_id}:commit:{commit['hash']}"
            text = f"Commit by {commit.get('author', 'unknown')}: {commit.get('message', '')}"

            documents.append(text)
            ids.append(doc_id)
            metadatas.append({
                "type": "commit",
                "hash": commit.get("hash", ""),
                "author": commit.get("author", ""),
                "date": str(commit.get("date", "")),
                "repo_id": repo_id,
            })

        # Embed in batches
        embeddings_model = self._get_embeddings()
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]

            embeddings = embeddings_model.embed_documents(batch_docs)

            self._collection.upsert(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_docs,
                metadatas=batch_meta,
            )

    def index_prs(self, prs: list[dict], repo_id: str = "default"):
        """
        Embed and store PR descriptions for semantic search.

        Args:
            prs: list of dicts with keys: number, title, body, author
        """
        if not prs:
            return

        documents = []
        ids = []
        metadatas = []

        for pr in prs:
            doc_id = f"{repo_id}:pr:{pr['number']}"
            text = f"PR #{pr['number']}: {pr.get('title', '')}. {pr.get('body', '')[:500]}"

            documents.append(text)
            ids.append(doc_id)
            metadatas.append({
                "type": "pr",
                "number": str(pr.get("number", "")),
                "author": pr.get("author", ""),
                "state": pr.get("state", ""),
                "repo_id": repo_id,
            })

        embeddings_model = self._get_embeddings()
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]

            embeddings = embeddings_model.embed_documents(batch_docs)

            self._collection.upsert(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_docs,
                metadatas=batch_meta,
            )

    def index_issues(self, issues: list[dict], repo_id: str = "default"):
        """
        Embed and store issue descriptions for semantic search.

        Args:
            issues: list of dicts with keys: number, title, body, author
        """
        if not issues:
            return

        documents = []
        ids = []
        metadatas = []

        for issue in issues:
            doc_id = f"{repo_id}:issue:{issue['number']}"
            text = f"Issue #{issue['number']}: {issue.get('title', '')}. {issue.get('body', '')[:500]}"

            documents.append(text)
            ids.append(doc_id)
            metadatas.append({
                "type": "issue",
                "number": str(issue.get("number", "")),
                "author": issue.get("author", ""),
                "state": issue.get("state", ""),
                "repo_id": repo_id,
            })

        embeddings_model = self._get_embeddings()
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]

            embeddings = embeddings_model.embed_documents(batch_docs)

            self._collection.upsert(
                ids=batch_ids,
                embeddings=embeddings,
                documents=batch_docs,
                metadatas=batch_meta,
            )

    # search

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_type: Optional[str] = None,
        repo_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Semantic search across all indexed documents.

        Args:
            query: natural language query
            top_k: number of results to return
            filter_type: optional filter — 'commit', 'pr', 'issue'
            repo_id: optional repo filter
        """
        embeddings_model = self._get_embeddings()
        query_embedding = embeddings_model.embed_query(query)

        where_filter = {}
        if filter_type:
            where_filter["type"] = filter_type
        if repo_id:
            where_filter["repo_id"] = repo_id

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None,
        )
        
        formatted = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                entry = {
                    "text": doc,
                    "score": 1 - results["distances"][0][i] if results["distances"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                }
                formatted.append(entry)

        return formatted

    # stats

    def count(self) -> int:
        """Total number of indexed documents."""
        return self._collection.count()

    def clear(self):
        """Remove all documents from the collection."""
        import chromadb

        self._chroma_client.delete_collection(self._collection_name)
        self._collection = self._chroma_client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )


#  LANGCHAIN TOOLS

# Singleton vector store
_vector_store: Optional[GitMindVectorStore] = None


def _get_vector_store() -> GitMindVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = GitMindVectorStore()
    return _vector_store


@tool
def semantic_search(query: str, top_k: int = 5, filter_type: str = "") -> str:
    """
    Search the GitMind knowledge base for commits, PRs, and issues
    semantically related to the query. Use this when keyword search
    is insufficient — it understands meaning, not just exact words.

    filter_type can be: 'commit', 'pr', 'issue', or '' for all.
    """
    store = _get_vector_store()

    if store.count() == 0:
        return "Vector store is empty. Run indexing first with 'gitmind index'."

    results = store.search(
        query=query,
        top_k=top_k,
        filter_type=filter_type if filter_type else None,
    )

    if not results:
        return "No semantically similar results found."

    return str(results)


EMBEDDING_TOOLS = [semantic_search]
