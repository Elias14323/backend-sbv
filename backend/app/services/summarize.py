"""Service for generating AI-powered summaries and bias analysis for clusters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.mistral import get_mistral_client

if TYPE_CHECKING:
    from app.models.article import Article

logger = logging.getLogger(__name__)


def build_summary_prompt(articles: list[Article]) -> str:
    """
    Build a detailed prompt for Mistral to generate summary, bias analysis, and timeline.
    
    Args:
        articles: List of Article objects from the same cluster
        
    Returns:
        Formatted prompt string ready for Mistral chat completion
    """
    # Build context from articles
    article_contexts = []
    for idx, article in enumerate(articles, 1):
        # Extract first ~1000 chars to avoid token overflow
        content_preview = (article.text_content or "")[:1000]
        
        context = f"""---
Article {idx}:
Titre: {article.title or "N/A"}
Source: {article.source.name if article.source else "N/A"}
Date: {article.published_at.isoformat() if article.published_at else "N/A"}
Contenu: {content_preview}
---"""
        article_contexts.append(context)
    
    articles_text = "\n\n".join(article_contexts)
    
    prompt = f"""Voici {len(articles)} articles sur un même sujet :

{articles_text}

Produis un dossier structuré en Markdown avec les sections suivantes :

## Résumé Factuel
- Synthèse neutre et objective des faits rapportés (200-300 mots)
- Structure: Qui, quoi, quand, où, pourquoi
- Reste factuel sans interpréter ni donner d'opinion

## Analyse des Angles et Biais
- Identifier les différentes perspectives et angles éditoriaux présentés par chaque source
- Noter les éventuels biais (omission, emphase, cadrage, choix lexical)
- Comparer les couvertures entre sources
- Signaler les points de convergence et divergence

## Chronologie
- Timeline des événements datés mentionnés dans les articles
- Format: `YYYY-MM-DD HH:MM - Événement` (si heure disponible, sinon juste la date)
- Ordre chronologique strict

Consignes importantes :
- Reste factuel et cite les sources quand pertinent
- Si les articles sont en conflit, note les désaccords sans trancher
- Format Markdown propre et structuré
- Utilise des listes à puces quand approprié"""
    
    return prompt


async def generate_cluster_summary(articles: list[Article]) -> dict[str, str]:
    """
    Generate summary, bias analysis, and timeline for a cluster using Mistral.
    
    Args:
        articles: List of Article objects from the same cluster
        
    Returns:
        Dictionary with keys: 'summary_md', 'bias_analysis_md', 'timeline_md'
        
    Raises:
        RuntimeError: If Mistral API call fails
    """
    if not articles:
        raise ValueError("Cannot generate summary for empty article list")
    
    logger.info(f"Generating summary for cluster with {len(articles)} articles")
    
    # Build prompt
    prompt = build_summary_prompt(articles)
    
    # Call Mistral chat completion
    client = get_mistral_client()
    
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un analyste de presse expert. Ton rôle est d'analyser plusieurs articles sur un même sujet et produire une synthèse objective et structurée.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.3,  # More deterministic, less creative
            max_tokens=2000,  # Sufficient for summary + analysis + timeline
        )
        
        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("Empty response from Mistral API")
        
        full_response = response.choices[0].message.content
        logger.info(f"Received summary response ({len(full_response)} chars)")
        
        # Parse the Markdown response into sections
        sections = parse_summary_response(full_response)
        
        return sections
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise RuntimeError(f"Mistral API error: {e}") from e


def parse_summary_response(markdown_text: str) -> dict[str, str]:
    """
    Parse the Markdown response from Mistral into separate sections.
    
    Args:
        markdown_text: Full Markdown text from Mistral
        
    Returns:
        Dictionary with keys: 'summary_md', 'bias_analysis_md', 'timeline_md'
    """
    sections = {
        "summary_md": "",
        "bias_analysis_md": "",
        "timeline_md": "",
    }
    
    # Split by main headers (##)
    lines = markdown_text.split("\n")
    current_section = None
    current_content = []
    
    for line in lines:
        # Check for section headers
        if line.strip().startswith("## Résumé Factuel"):
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "summary_md"
            current_content = []
        elif line.strip().startswith("## Analyse des Angles et Biais"):
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "bias_analysis_md"
            current_content = []
        elif line.strip().startswith("## Chronologie"):
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = "timeline_md"
            current_content = []
        elif current_section:
            # Add line to current section
            current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content).strip()
    
    # If parsing failed, put everything in summary
    if not any(sections.values()):
        logger.warning("Failed to parse sections, storing full response in summary_md")
        sections["summary_md"] = markdown_text.strip()
    
    return sections


__all__ = ["build_summary_prompt", "generate_cluster_summary", "parse_summary_response"]
