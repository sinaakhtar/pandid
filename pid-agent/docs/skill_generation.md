# Skill Generation: pid-parsing-extraction

This document explains how the `pid-parsing-extraction` skill was generated.

## Generation Process

The skill located at `pid-parsing-extraction/SKILL.md` was generated separately using **Vertex AI** with a specific prompting strategy and context.

### Context
- **YouTube Video:** [P&ID Video Context](https://www.youtube.com/watch?v=j4EOTerfyTY)
- The video was used as the primary source of truth for understanding the nuances of P&ID parsing and extraction.

### Model
- **Gemini 3.1 Pro** (Note: This is the model version specified by the user).

### Prompting Details
- The model was asked to watch the linked video and build a skill specifically focusing on the parsing and extraction of structured data from P&IDs.
- It was explicitly prompted to fill in any missing information or gaps using its own broad knowledge base.

## Purpose of the Skill
The generated skill provides detailed instructions and guidance for the **Extractor Agent** on how to identify components, labels, lines, and connectivity in P&IDs, ensuring a structured and accurate output schema.
