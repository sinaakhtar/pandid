# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import pathlib
from zoneinfo import ZoneInfo

import google.auth
from google.adk.agents import Agent, LoopAgent, LlmAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset, exit_loop
from google.adk.tools.tool_context import ToolContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.cloud import bigquery
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

try:
    _, project_id = google.auth.default()
except Exception:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "donuts-dev")

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

AGENT_MODEL = os.environ.get("AGENT_MODEL", "gemini-3-flash-preview")


def ensure_tables_exist():
    """Ensures that the necessary BigQuery tables exist with constraints."""
    try:
        client = bigquery.Client()
        dataset_id = os.environ.get("BIGQUERY_DATASET_ID", "pandid")
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "donuts-dev")

        dataset_ref = client.dataset(dataset_id, project=project_id)

        # Create dataset if not exists
        try:
            client.get_dataset(dataset_ref)
        except Exception:
            print(f"Creating dataset {dataset_id}...")
            client.create_dataset(dataset_ref)

        nodes_table_id = f"{project_id}.{dataset_id}.nodes"
        edges_table_id = f"{project_id}.{dataset_id}.edges"

        # DDL for Nodes table
        nodes_ddl = f"""
        CREATE TABLE IF NOT EXISTS `{nodes_table_id}` (
          diagram_id STRING,
          id STRING,
          category STRING,
          parameter STRING,
          device_type STRING,
          loop_id STRING,
          location STRING,
          description STRING,
          PRIMARY KEY (diagram_id, id) NOT ENFORCED
        )
        """

        # DDL for Edges table with Foreign Keys referencing Nodes
        edges_ddl = f"""
        CREATE TABLE IF NOT EXISTS `{edges_table_id}` (
          diagram_id STRING,
          source_id STRING,
          target_id STRING,
          medium STRING,
          flow_direction STRING,
          description STRING,
          PRIMARY KEY (diagram_id, source_id, target_id) NOT ENFORCED,
          FOREIGN KEY (diagram_id, source_id) REFERENCES `{nodes_table_id}`(diagram_id, id) NOT ENFORCED,
          FOREIGN KEY (diagram_id, target_id) REFERENCES `{nodes_table_id}`(diagram_id, id) NOT ENFORCED
        )
        """

        print("Ensuring tables exist with constraints...")
        client.query(nodes_ddl).result()
        client.query(edges_ddl).result()
        print("Tables ensured successfully.")

    except Exception as e:
        print(f"Warning: Could not ensure tables exist: {e}")


def load_to_bigquery(nodes_json: str, edges_json: str) -> str:
    """Loads extracted P&ID data into separate Nodes and Edges tables in BigQuery, avoiding duplicates.

    Args:
        nodes_json: A JSON string containing the extracted nodes. Expected
          schema: { "diagram_id": "string", "nodes": [...] }
        edges_json: A JSON string containing the extracted edges. Expected
          schema: { "diagram_id": "string", "edges": [...] }

    Returns:
        A string confirming success or failure.
    """
    try:
        client = bigquery.Client()
        nodes_data = json.loads(nodes_json)
        edges_data = json.loads(edges_json)

        dataset_id = os.environ.get("BIGQUERY_DATASET_ID", "pandid")
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "donuts-dev")

        diagram_id = nodes_data.get("diagram_id") or edges_data.get(
            "diagram_id"
        )

        # Deduplicate nodes in Python
        seen_nodes = set()
        unique_nodes = []
        for node in nodes_data.get("nodes", []):
            node["diagram_id"] = diagram_id
            node_id = node.get("id")
            key = (diagram_id, node_id)
            if key not in seen_nodes:
                seen_nodes.add(key)
                unique_nodes.append(node)

        # Deduplicate edges in Python
        seen_edges = set()
        unique_edges = []
        for edge in edges_data.get("edges", []):
            edge["diagram_id"] = diagram_id
            src = edge.get("source_id")
            tgt = edge.get("target_id")
            key = (diagram_id, src, tgt)
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(edge)

        if unique_nodes:
            nodes_table_id = f"{project_id}.{dataset_id}.nodes"
            # Use MERGE to avoid duplicates
            nodes_merge_query = f"""
            MERGE `{nodes_table_id}` T
            USING (
              SELECT
                JSON_VALUE(val, '$.diagram_id') as diagram_id,
                JSON_VALUE(val, '$.id') as id,
                JSON_VALUE(val, '$.category') as category,
                JSON_VALUE(val, '$.parameter') as parameter,
                JSON_VALUE(val, '$.device_type') as device_type,
                JSON_VALUE(val, '$.loop_id') as loop_id,
                JSON_VALUE(val, '$.location') as location,
                JSON_VALUE(val, '$.description') as description
              FROM UNNEST(JSON_EXTRACT_ARRAY(@json_data)) val
            ) S
            ON T.diagram_id = S.diagram_id AND T.id = S.id
            WHEN NOT MATCHED THEN
              INSERT (diagram_id, id, category, parameter, device_type, loop_id, location, description)
              VALUES (S.diagram_id, S.id, S.category, S.parameter, S.device_type, S.loop_id, S.location, S.description)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("json_data", "STRING", json.dumps(unique_nodes))
                ]
            )
            client.query(nodes_merge_query, job_config=job_config).result()

        if unique_edges:
            edges_table_id = f"{project_id}.{dataset_id}.edges"
            # Use MERGE to avoid duplicates
            edges_merge_query = f"""
            MERGE `{edges_table_id}` T
            USING (
              SELECT
                JSON_VALUE(val, '$.diagram_id') as diagram_id,
                JSON_VALUE(val, '$.source_id') as source_id,
                JSON_VALUE(val, '$.target_id') as target_id,
                JSON_VALUE(val, '$.medium') as medium,
                JSON_VALUE(val, '$.flow_direction') as flow_direction,
                JSON_VALUE(val, '$.description') as description
              FROM UNNEST(JSON_EXTRACT_ARRAY(@json_data)) val
            ) S
            ON T.diagram_id = S.diagram_id AND T.source_id = S.source_id AND T.target_id = S.target_id
            WHEN NOT MATCHED THEN
              INSERT (diagram_id, source_id, target_id, medium, flow_direction, description)
              VALUES (S.diagram_id, S.source_id, S.target_id, S.medium, S.flow_direction, S.description)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("json_data", "STRING", json.dumps(unique_edges))
                ]
            )
            client.query(edges_merge_query, job_config=job_config).result()

        return f"Successfully processed nodes and edges for diagram {diagram_id} in BigQuery."
    except Exception as e:
        return f"Error loading to BigQuery: {e}"


async def save_file_as_artifact(filepath: str, artifact_name: str, context: ToolContext) -> str:
    """Reads a local file and saves it as an ADK artifact.
    
    Args:
        filepath: Path to the local file.
        artifact_name: Name to give to the artifact.
    """
    try:
        if not os.path.exists(filepath):
            return f"Error: File not found at {filepath}"
            
        with open(filepath, "rb") as f:
            data = f.read()
            
        mime_type = "image/png" # Default
        if filepath.endswith(".pdf"):
            mime_type = "application/pdf"
        elif filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
            mime_type = "image/jpeg"
            
        artifact = types.Part.from_bytes(data=data, mime_type=mime_type)
        version = await context.save_artifact(filename=artifact_name, artifact=artifact)
        return f"Successfully saved file {filepath} as artifact {artifact_name} version {version}."
    except Exception as e:
        return f"Error saving file as artifact: {e}"


# Initialize tables
ensure_tables_exist()


# Load the skill from the directory provided by the user
skill_dir = pathlib.Path(
    "/Users/sinanek/Documents/code/pandid/pid-parsing-extraction"
)
pid_skill = load_skill_from_dir(skill_dir)
pid_skill_toolset = skill_toolset.SkillToolset(skills=[pid_skill])

# Define the zoomer agent
zoomer_agent = LlmAgent(
    name="zoomer_agent",
    model=Gemini(
        model=AGENT_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=BuiltInCodeExecutor(),
    instruction=(
        "You are a specialized agent for zooming in on regions of a P&ID (image or PDF). "
        "When given a file path and bounding box coordinates, "
        "write and execute Python code to crop that region. "
        "You have access to `PIL` (Pillow) and `fitz` (PyMuPDF) libraries. "
        "If the file is a PDF, use `fitz` to extract the region and save it as an image. "
        "If the file is an image, use `PIL` to crop it. "
        "Save the resulting cropped image to a file and return the file path as your final answer."
    ),
    description="Executes Python code to crop and zoom in on parts of P&IDs.",
)

# Define the extractor sub-agent
extractor_agent = LlmAgent(
    name="extractor_agent",
    model=Gemini(
        model=AGENT_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a specialized agent for parsing and extracting information from P&IDs. "
        "Use the provided skill to extract nodes and edges from the provided image/PDF. "
        "If you need to zoom in on a specific region to accurately find information, "
        "delegate that task to the `zoomer_agent` by providing the file path and coordinates. "
        "The `zoomer_agent` will return a file path to the cropped image. "
        "Use the `save_file_as_artifact` tool to save this file as an artifact. "
        "Then use the zoomed image to complete your extraction. "
        "If feedback is provided in {feedback?}, use it to correct and complete the extraction. "
        "Output the result as a JSON string containing both 'nodes' and 'edges' keys."
    ),
    tools=[pid_skill_toolset, save_file_as_artifact],
    sub_agents=[zoomer_agent],
    output_key="extracted_data"
)

# Define the reviewer sub-agent
reviewer_agent = LlmAgent(
    name="reviewer_agent",
    model=Gemini(
        model=AGENT_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a meticulous reviewer of P&ID extractions. "
        "Read the extracted data from {extracted_data}. "
        "Verify if all entries are complete and valid according to P&ID standards. "
        "If satisfactory, use the load_to_bigquery tool to save the data, and then use the exit_loop tool to finish. "
        "If NOT satisfactory, provide specific feedback on what is missing or invalid."
    ),
    tools=[load_to_bigquery, exit_loop],
    output_key="feedback"
)

# Define the loop agent
refinement_loop = LoopAgent(
    name="refinement_loop",
    description="Iteratively refines P&ID extraction until valid.",
    max_iterations=3,
    sub_agents=[extractor_agent, reviewer_agent]
)

# Define the root agent
root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=AGENT_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a helpful AI assistant designed to analyze P&IDs. "
        "When a user provides a P&ID (image or PDF), delegate the extraction task to the refinement_loop."
    ),
    sub_agents=[refinement_loop],
)

app = App(
    root_agent=root_agent,
    name="app",
)
