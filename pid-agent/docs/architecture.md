# P&ID Agent Architecture

This document describes the architecture and flow of the P&ID Analysis Agent.

## Overview

The P&ID Analysis system uses a multi-agent architecture to handle complex parsing, verification, and visual analysis of Piping and Instrumentation Diagrams (P&IDs). It is built using the ADK (Agent Development Kit) framework.

## Agent Hierarchy

The system consists of a root agent and a set of specialized sub-agents organized in a refinement loop.

```mermaid
graph TD
    User([User]) -->|Provides P&ID| Root[Root Agent]
    Root -->|Starts| Loop["Refinement Loop (LoopAgent)"]
    
    subgraph Loop [Refinement Loop]
        Extractor[Extractor Agent]
        Zoomer[Zoomer Agent]
        Reviewer[Reviewer Agent]
        
        Extractor -->|Request Zoom| Zoomer
        Zoomer -->|Return Cropped Image| Extractor
        Extractor -->|Send JSON| Reviewer
        Reviewer -->|Feedback (Invalid)| Extractor
    end
    
    Reviewer -->|Valid & Loaded| BQ[(BigQuery)]
    
    style Loop fill:#f9f,stroke:#333,stroke-width:2px
```

## Agent Roles

### 1. Root Agent (`root_agent`)
- **Role:** The entry point for the system.
- **Function:** Receives the P&ID file (Image or PDF) from the user and delegates the extraction task to the **Refinement Loop**.

### 2. Refinement Loop (`refinement_loop`)
- **Role:** Orchestrator for iterative refinement.
- **Function:** A `LoopAgent` that coordinates the **Extractor** and **Reviewer** agents. It runs for up to 3 iterations to ensure high-quality extraction based on feedback.

### 3. Extractor Agent (`extractor_agent`)
- **Role:** The primary parser.
- **Function:** Extracts nodes (components) and edges (piping/connections) from the diagram.
- **Tools:**
    - Uses the `pid-parsing-extraction` skill.
    - Uses `save_file_as_artifact` to save zoomed images.
- **Sub-Agents:** Can delegate to the **Zoomer Agent** for detailed analysis of dense or blurry regions.

### 4. Zoomer Agent (`zoomer_agent`)
- **Role:** Visual assistant.
- **Function:** Crops specific regions of the diagram based on coordinates provided by the Extractor.
- **Capabilities:** Uses `BuiltInCodeExecutor` to run Python code with `PIL` (for images) and `fitz` (PyMuPDF for PDFs).

### 5. Reviewer Agent (`reviewer_agent`)
- **Role:** Quality control.
- **Function:** Reviews the extracted data against P&ID standards.
- **Actions:**
    - If the data is valid, it calls `load_to_bigquery` and then `exit_loop` to complete the process.
    - If the data is invalid or incomplete, it provides feedback to the Extractor for the next iteration.

## Data Flow

1.  **User** uploads a P&ID to the **Root Agent**.
2.  **Root Agent** triggers the **Refinement Loop**.
3.  **Extractor Agent** attempts to extract data. If it encounters a complex area, it asks the **Zoomer Agent** to crop that area.
4.  **Zoomer Agent** returns the cropped image, and the **Extractor** continues.
5.  The **Extractor Agent** produces a JSON output and passes it to the **Reviewer Agent**.
6.  The **Reviewer Agent** checks the output:
    - **Pass:** Loads data to **BigQuery** and ends the loop.
    - **Fail:** Sends feedback back to the **Extractor Agent** to try again.
