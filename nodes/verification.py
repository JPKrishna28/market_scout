"""
Market Intelligence Scout — Cross-Source Verification Node (SBERT via HF InferenceClient)

Deterministic ML engine — NOT an agent.

Uses HuggingFace InferenceClient (official SDK) instead of deprecated REST URLs:
  • Automatic provider routing (no manual URL construction)
  • Zero RAM footprint (no model weights in memory)
  • Same all-MiniLM-L6-v2 model
  • Redis-cached embeddings to minimise API calls
  • Graceful fallback to local SentenceTransformer if API fails

Responsibilities:
  • Convert feature summaries → embeddings via HF API
  • Cluster semantically similar features (cosine > threshold)
  • Count cross-source mentions
  • Consolidate clusters into verified features
"""

import logging
import time
from typing import Dict, Any, List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from graph.state import GraphState
from cache.redis_client import make_cache_key, get_cache, set_cache
from app.config import settings

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# HuggingFace Inference Client (Lazy Init)
# ────────────────────────────────────────────────────────────────────

_hf_client = None


def _get_hf_client():
    """Lazy-initialise the HuggingFace InferenceClient."""
    global _hf_client
    if _hf_client is None:
        from huggingface_hub import InferenceClient
        token = settings.HF_API_TOKEN if settings.HF_API_TOKEN else None
        _hf_client = InferenceClient(token=token)
        logger.info("VERIFICATION — HF InferenceClient initialised")
    return _hf_client


def _get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Get embeddings for a batch of texts via HF InferenceClient.

    Falls back to local SentenceTransformer if API fails.
    """
    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            client = _get_hf_client()
            # feature_extraction returns embeddings directly
            result = client.feature_extraction(
                text=texts,
                model=f"sentence-transformers/{settings.SBERT_MODEL}",
            )
            # Result is a numpy array or list of lists
            if hasattr(result, 'tolist'):
                return result.tolist()
            
            # Handle nested token-level embeddings → mean pool
            processed = []
            for emb in result:
                if isinstance(emb, (list, np.ndarray)):
                    arr = np.array(emb)
                    if arr.ndim == 2:
                        # Token-level → mean pool to sentence-level
                        processed.append(np.mean(arr, axis=0).tolist())
                    else:
                        processed.append(arr.tolist() if hasattr(arr, 'tolist') else list(arr))
                else:
                    processed.append(emb)
            return processed

        except Exception as exc:
            wait = 2 ** attempt
            logger.warning(
                "VERIFICATION — HF API attempt %d/%d failed: %s — retrying in %ds",
                attempt, settings.MAX_RETRIES, exc, wait,
            )
            if attempt < settings.MAX_RETRIES:
                time.sleep(wait)

    # ── Fallback to local model ────────────────────────────────────
    logger.warning("VERIFICATION — HF API failed, falling back to local SBERT")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(settings.SBERT_MODEL)
        return model.encode(texts).tolist()
    except Exception as exc:
        logger.error("VERIFICATION — Local fallback also failed: %s", exc)
        return []


# ────────────────────────────────────────────────────────────────────
# Embedding with Cache
# ────────────────────────────────────────────────────────────────────

def _get_embeddings_cached(texts: List[str]) -> List[np.ndarray]:
    """Get embeddings for multiple texts, using cache where possible
    and batching uncached texts into a single API call."""
    embeddings = [None] * len(texts)
    uncached_indices = []
    uncached_texts = []

    # Check cache first
    for i, text in enumerate(texts):
        cache_key = make_cache_key("embedding", text)
        cached = get_cache(cache_key)
        if cached is not None:
            embeddings[i] = np.array(cached)
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    # Batch API call for uncached
    if uncached_texts:
        logger.info("VERIFICATION — Fetching %d embeddings from HF API", len(uncached_texts))
        batch_results = _get_embeddings_batch(uncached_texts)

        for idx, emb in zip(uncached_indices, batch_results):
            embeddings[idx] = np.array(emb)
            # Cache for next time
            cache_key = make_cache_key("embedding", texts[idx])
            set_cache(cache_key, emb, expire=86400)
    else:
        logger.info("VERIFICATION — All %d embeddings served from cache", len(texts))

    return embeddings


# ────────────────────────────────────────────────────────────────────
# Node Entry Point
# ────────────────────────────────────────────────────────────────────

def verification_node(state: GraphState) -> Dict[str, Any]:
    """
    Cross-Source Verification — SBERT semantic clustering via HF InferenceClient.

    Input:  state["extracted_features"]
    Output: state["verified_features"]
    """
    features = state.get("extracted_features", [])
    logger.info("VERIFICATION — Processing %d extracted features", len(features))

    if not features:
        return {"verified_features": []}

    # ── Generate embeddings (batched, cached) ──────────────────────
    summaries = [f.get("feature_summary", "") for f in features]
    embeddings = _get_embeddings_cached(summaries)

    # Handle case where embedding generation failed
    if not embeddings or any(e is None for e in embeddings):
        logger.warning("VERIFICATION — Embedding generation failed, passing features through unverified")
        return {"verified_features": [
            {**f, "source_count": 1, "primary_url": f.get("url", ""), "all_sources": [f.get("url", "")]}
            for f in features
        ]}

    embeddings_array = np.array(embeddings)

    # ── Semantic clustering ────────────────────────────────────────
    verified: List[Dict[str, Any]] = []
    clustered: set = set()

    for i in range(len(features)):
        if i in clustered:
            continue

        cluster = [features[i]]
        cluster_indices = [i]
        clustered.add(i)

        for j in range(i + 1, len(features)):
            if j in clustered:
                continue

            sim = cosine_similarity(
                embeddings_array[i].reshape(1, -1),
                embeddings_array[j].reshape(1, -1),
            )[0][0]

            if sim >= settings.SIMILARITY_THRESHOLD:
                cluster.append(features[j])
                cluster_indices.append(j)
                clustered.add(j)

        # ── Consolidate cluster ────────────────────────────────────
        best = max(cluster, key=lambda x: x.get("source_authority", 0))
        all_urls = list({f.get("url", "") for f in cluster if f.get("url")})
        all_metrics = list({m for f in cluster for m in f.get("metrics", []) if m})
        all_evidence = [f.get("evidence", "") for f in cluster if f.get("evidence")]

        verified.append({
            "feature_summary": best.get("feature_summary", ""),
            "category": best.get("category", ""),
            "metrics": all_metrics,
            "confidence": best.get("confidence", 0.0),
            "evidence": all_evidence[:3],
            "source_count": len(all_urls),
            "primary_url": best.get("url", ""),
            "all_sources": all_urls,
            "publish_date": best.get("publish_date"),
            "source_authority": best.get("source_authority", 0.5),
        })

    logger.info(
        "VERIFICATION — Consolidated %d → %d verified features",
        len(features), len(verified),
    )

    return {"verified_features": verified}