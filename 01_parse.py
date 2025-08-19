#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "openai>=1.0.0",
#     "tiktoken>=0.5.0"
# ]
# ///

import json
import os
import openai
import tiktoken
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BibTeXConverter:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text to estimate API costs"""
        return len(self.encoding.encode(text))

    def create_bibtex_prompt(self, paper_data: Dict[str, Any]) -> str:
        """Create a prompt for converting paper data to BibLaTeX format"""
        return f"""Convert the following academic paper information to a proper BibLaTeX entry.

Paper data:
- URL: {paper_data['url']}
- Volume: {paper_data['volume_id']}
- Paper ID: {paper_data['paper_id']}
- Content: {paper_data['raw_text'][:2000]}...

Please create a BibLaTeX entry with the following requirements:
1. Use @article as the entry type
2. Generate a unique citation key based on the authors and year
3. Extract the title, authors, journal, volume, number, pages, year, and DOI if available
4. Include the URL field
5. Use proper BibLaTeX formatting with curly braces for proper capitalization
6. If information is missing, make reasonable inferences or mark as [n.d.] for year

Return ONLY the BibLaTeX entry, no explanations or additional text."""

    def convert_to_bibtex(self, paper_data: Dict[str, Any]) -> str:
        """Convert a single paper to BibLaTeX format using OpenAI API"""
        try:
            prompt = self.create_bibtex_prompt(paper_data)
            token_count = self.count_tokens(prompt)
            logger.info(
                f"Converting paper {paper_data['volume_id']}/{paper_data['paper_id']} (tokens: {token_count})"
            )

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a bibliographic expert who converts academic paper information to BibLaTeX format. Always return only the BibLaTeX entry, no explanations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            bibtex_entry = response.choices[0].message.content.strip()
            logger.info(
                f"Successfully converted paper {paper_data['volume_id']}/{paper_data['paper_id']}"
            )
            return bibtex_entry

        except Exception as e:
            logger.error(
                f"Failed to convert paper {paper_data['volume_id']}/{paper_data['paper_id']}: {e}"
            )
            # Return a basic fallback entry
            return f"""@article{{{paper_data['volume_id']}_{paper_data['paper_id']},
  title = {{Paper from TAC Volume {paper_data['volume_id']}, Number {paper_data['paper_id']}}},
  journal = {{Theory and Applications of Categories}},
  volume = {{{paper_data['volume_id']}}},
  number = {{{paper_data['paper_id']}}},
  year = {{[n.d.]}},
  url = {{{paper_data['url']}}}
}}"""

    def process_papers(
        self, papers: List[Dict[str, Any]], limit: int = None
    ) -> List[str]:
        """Process all papers and convert them to BibLaTeX format"""
        if limit:
            papers = papers[:limit]
            logger.info(f"Processing first {limit} papers")

        bibtex_entries = []
        total_papers = len(papers)

        for i, paper in enumerate(papers, 1):
            logger.info(f"Processing paper {i}/{total_papers}")
            bibtex_entry = self.convert_to_bibtex(paper)
            bibtex_entries.append(bibtex_entry)

            # Add a small delay to be respectful to the API
            if i < total_papers:
                import time

                time.sleep(0.5)

        return bibtex_entries

    def save_bibtex(self, entries: List[str], filename: str = "tac.bib"):
        """Save BibLaTeX entries to a .bib file"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write("% TAC Papers converted to BibLaTeX format\n")
            f.write("% Generated automatically from web scraping data\n\n")

            for entry in entries:
                f.write(entry + "\n\n")

        logger.info(f"Saved {len(entries)} BibLaTeX entries to {filename}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert TAC papers to BibLaTeX format"
    )
    parser.add_argument(
        "--input", "-i", default="tac.json", help="Input JSON file (default: tac.json)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="tac.bib",
        help="Output BibTeX file (default: tac.bib)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit number of papers to process (default: all papers)",
    )
    parser.add_argument(
        "--dev", action="store_true", help="Development mode: limit to 5 papers"
    )

    args = parser.parse_args()

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        return

    # Set default limit for development mode
    if args.dev:
        limit = 5
        print("Development mode: limiting to 5 papers")
    else:
        limit = args.limit

    # Load papers from JSON
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            papers = json.load(f)
        logger.info(f"Loaded {len(papers)} papers from {args.input}")
    except FileNotFoundError:
        logger.error(f"Input file {args.input} not found")
        return
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {args.input}")
        return

    # Initialize converter
    converter = BibTeXConverter(api_key)

    # Process papers
    logger.info("Starting conversion to BibLaTeX format...")
    bibtex_entries = converter.process_papers(papers, limit)

    # Save results
    converter.save_bibtex(bibtex_entries, args.output)

    print(f"\nConversion completed successfully!")
    print(f"Processed {len(bibtex_entries)} papers")
    print(f"Output saved to {args.output}")

    # Show sample entry
    if bibtex_entries:
        print(f"\nSample BibLaTeX entry:")
        print(bibtex_entries[0][:200] + "...")


if __name__ == "__main__":
    main()
