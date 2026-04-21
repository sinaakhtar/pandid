# Pandid - P&ID Analysis Agent

This project contains an ADK-based agent designed to parse Piping and Instrumentation Diagrams (P&IDs) and load the extracted structured data into BigQuery.

## Project Structure

- `pid-agent`: The core agent application, built with the Google Cloud Agent Starter Pack.
- `pid-parsing-extraction`: Contains the custom skill and assets used by the agent to interpret P&IDs.

## What the Agent Does

The agent is designed to automate the extraction of network data (nodes and edges) from P&ID diagrams. It uses a hierarchical multi-agent system:

1.  **Extractor Agent**: Parses the P&ID using a specialized skill to identify nodes (devices, instruments) and edges (pipelines, connections). It can delegate tasks to a **Zoomer Agent** to crop and focus on specific dense regions of the diagram for better accuracy.
2.  **Reviewer Agent**: Validates the extracted data against P&ID standards. If the data is satisfactory, it uses a BigQuery tool to persist the data. If not, it provides feedback to the Extractor for another iteration.
3.  **Refinement Loop**: Orchestrates the interaction between the Extractor and Reviewer up to a maximum number of iterations to ensure high-quality output.

Extracted data is stored in BigQuery in two tables: `nodes` and `edges`, with constraints to ensure data integrity.

## How to Trigger and Try It

### Prerequisites

- **uv**: Fast Python package installer and resolver. [Install uv](https://docs.astral.sh/uv/getting-started/installation/).
- **Google Cloud SDK**: For authentication and accessing BigQuery. [Install Google Cloud SDK](https://cloud.google.com/sdk/docs/install).
- **Make**: Usually pre-installed on macOS/Linux.

### Setup and Run

1.  **Navigate to the agent directory**:
    ```bash
    cd pid-agent
    ```

2.  **Install dependencies**:
    ```bash
    make install
    ```

3.  **Set up environment variables**:
    Copy `.env.example` to `.env` and fill in the required values, such as `GOOGLE_CLOUD_PROJECT` and `BIGQUERY_DATASET_ID`.
    ```bash
    cp .env.example .env
    ```

4.  **Launch the local playground**:
    ```bash
    make playground
    ```

5.  **Try it**:
    Once the playground is running, you can interact with the agent. Upload a P&ID image or PDF and ask the agent to "Extract nodes and edges from this diagram".

## Pushing changes to GitHub

To push changes to the repository, use the following command to specify the correct SSH key if needed:
```bash
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_nutrihelp" git push -u origin main
```
