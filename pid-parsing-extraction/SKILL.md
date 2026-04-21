---
name: pid-parsing-extraction
description: Parses Piping and Instrumentation Diagrams (P&IDs) to extract equipment, instruments, and connections into a structured node-and-edge format suitable for database ingestion and graph querying. Use when digitizing P&IDs, mapping process flows, or generating digital twins from schematic data.
---

# P&ID Parsing and Extraction

> A systematic skill for interpreting visual or textual representations of Piping and Instrumentation Diagrams (P&IDs) and converting them into strict, queryable structured data (Nodes and Edges).

## Overview

Process engineering relies heavily on P&IDs to document how pipelines, equipment, instrumentation, and control systems interact. This skill enables the AI to read these schematics, decode the standard identification codes, and map the physical and electrical topologies into a structured graph format (JSON) that can be ingested into a graph database (e.g., BigQuery,Neo4j) or a relational database.

## When to Use

- When provided with an image, SVG, or text-based representation of a P&ID and asked to extract its components.
- When migrating legacy PDF/Image P&IDs into a digital database.
- When asked to trace a specific process flow, control loop, or electrical connection through a system.
- When generating bills of materials (BOM) or instrument lists from a diagram.

**When NOT to use:**
- When parsing simple Process Flow Diagrams (PFDs) that lack instrument-level detail (do not hallucinate instrument tags).
- When asked to design a control system from scratch (this skill is for *extraction*, not *engineering design*).

## The Five Principles of P&ID Extraction

### 1. Nodes are Entities; Edges are Connections
Every symbol on the diagram is a **Node** (Equipment, Valve, Instrument). Every line connecting them is an **Edge** (Pipe, Electrical wire, Data link). You must strictly separate the components from the mediums that connect them.

### 2. Decode the Tag (The Identifier)
Process equipment and instruments are identified by standard codes (e.g., `TT-01`, `FV-01`). 
- **First Letter:** The measured/controlled parameter (e.g., `T` = Temperature, `F` = Flow, `P` = Pressure, `L` = Level).
- **Subsequent Letters:** The type of device/function (e.g., `T` = Transmitter, `V` = Valve, `C` = Controller, `I` = Indicator).
- **Numbers:** The logical numerator or control loop ID (e.g., `01`, `105`).

**Fallback for Non-Tagged Items:** If an item does not have a standard ISA tag, use the text label associated with it on the diagram as its ID (e.g., `66KL21`). Do not add prefixes or suffixes like 'Valve_' or size unless they are part of the label. This ensures consistency and avoids creating overly long IDs.

**Manual Valves and In-Line Components:** Manual valves, strainers, and reducers often have labels like `66KL21` or `73KH12` instead of standard tags. Ensure you extract them as distinct nodes, even if they don't have a circle or square enclosure. Look for text labels near the valve/component symbols.

### 3. Determine Physical Location from Symbol Enclosures
The visual enclosure of an instrument tag dictates its location in the plant:
- **Circle with NO dividing line:** Field-mounted (physically located on the pipe/equipment in the plant).
- **Circle with a SOLID dividing line:** Main control room / panel-mounted (accessible to the operator).
*(Note: Always extract this property as the `location` attribute).*

### 4. Differentiate Connection Types (Edges)
Lines represent the transfer of fluids or signals. You must classify the edge type based on line styling:
- **Solid Line:** Primary interconnection via pipework (fluid/gas process flow).
- **Dashed/Dotted Line:** Electrical connection or signal.
- **Line with slashes/marks:** (If present) Pneumatic or data links.

### 5. Capture Contextual Decorators
Do not ignore diagram text that indicates external routing. Text like "To Transfer Pump" or "From Feed Tank" must be captured as special "Off-Page Connector" nodes. Vent and drain valves must also be captured as distinct nodes connected to the main process line.

---

## The Extraction Process

### Step 1: Node Identification and Tag Parsing
Scan the diagram and identify every unique instrument, valve, and piece of equipment. Create a node for each.

```json
// Example: Parsing "FV-01" enclosed in a plain circle
{
  "node_id": "FV-01",
  "type": "Instrument",
  "parameter": "Flow",
  "function": "Valve",
  "loop_number": "01",
  "location": "Field",
  "symbol_type": "Circle_No_Line"
}
```

### Step 2: Main Equipment Extraction
Identify larger equipment (Tanks, Reactors, Compressors). These usually have distinct visual symbols and different tagging conventions (e.g., `CT-105` for a Cooling Tower, or a generic "Rotary Compressor").

```json
{
  "node_id": "Rotary_Compressor_1",
  "type": "Equipment",
  "equipment_class": "Compressor",
  "description": "Rotary Compressor"
}
```

### Step 3: Edge Mapping (Topology)
Trace the lines between the extracted nodes. Define the source, target, and the nature of the connection. If arrows dictate flow, apply directionality.

```json
// Example: An electrical signal from a Flow Transmitter (FT-01) to a Flow Valve (FV-01)
{
  "edge_id": "e_FT01_FV01",
  "source": "FT-01",
  "target": "FV-01",
  "connection_type": "Electrical",
  "line_style": "Dotted"
}
```

### Step 4: Validate Control Loops
Group instruments sharing the same numerical ID (e.g., `FT-01`, `FC-01`, `FV-01`) together. Verify that the edges connect them logically (Sensor -> Controller -> Actuator/Valve).

---

## Required Output Schema

When instructed to parse a P&ID, produce two separate JSON outputs: one for Nodes and one for Edges, to allow loading into separate database tables.

### Output 1: Nodes
```json
{
  "diagram_id": "string",
  "nodes": [
    {
      "id": "string (The Tag name, e.g., 'TT-01')",
      "category": "string (Equipment | Instrument | Valve | OffPage)",
      "parameter": "string (e.g., 'Temperature', null if Equipment)",
      "device_type": "string (e.g., 'Transmitter', null if Equipment)",
      "loop_id": "string (e.g., '01')",
      "location": "string (Field | Control_Room | Unknown)",
      "description": "string (Any accompanying text)"
    }
  ]
}
```

### Output 2: Edges
```json
{
  "diagram_id": "string",
  "edges": [
    {
      "source_id": "string (ID of origin node)",
      "target_id": "string (ID of destination node)",
      "medium": "string (Piping | Electrical | Pneumatic | Software)",
      "flow_direction": "string (Forward | Bidirectional | None)",
      "description": "string (e.g., 'Sample line', 'Vent')"
    }
  ]
}
```

---

## Domain-Specific Guidance Dictionary

Use the following lookup table to resolve common abbreviations found in P&IDs. 

**First Letter (Parameter):**
*   **F**: Flow
*   **T**: Temperature
*   **P**: Pressure
*   **L**: Level
*   **V**: Vibration
*   **H**: Hand (Manual operation)

**Subsequent Letters (Function):**
*   **T**: Transmitter (Sends a signal)
*   **V**: Valve (Controls the flow)
*   **C**: Controller (Processes signal and dictates action)
*   **I**: Indicator (Local gauge/readout)
*   **E**: Element (Primary sensor)
*   **S**: Switch (Changes state)

**Line Styles:**
*   **Solid thick/thin line:** `Piping` (Process connection)
*   **Dashed line (- - -):** `Electrical` (Signal)
*   **Line with crosshatches (//):** `Pneumatic` (Air signal)

---

## Red Flags (Failure Modes to Avoid)

- **Hallucinating Missing Links:** Do not invent connections that are not explicitly drawn. If a transmitter `TT-01` is floating near a pipe but not physically connected by a line, log the node, but do not create a piping edge.
- **Misidentifying Line Types:** Treating a dotted electrical line as a process pipe will corrupt the database. Fluid cannot flow through an electrical connection.
- **Ignoring Flow Arrows:** Process flow direction is critical. Always check lines for directional arrowheads and assign `source_id` and `target_id` accordingly. If no arrow is present, default to `flow_direction: "Unknown"`.
- **Merging Duplicate Tags:** If a diagram has two distinct elements labeled "Gate Valve" with no unique tag, append a logical numerator (e.g., `Gate_Valve_A`, `Gate_Valve_B`) to ensure database primary keys are unique.

## Verification Checklist

Before outputting the final JSON payloads, run this internal check:

- [ ] Every symbol on the P&ID has a corresponding entry in the `nodes` array.
- [ ] Every line on the P&ID has a corresponding entry in the `edges` array.
- [ ] All `source_id` and `target_id` references in the `edges` array strictly match an `id` present in the `nodes` array (No orphaned edges/Foreign Key violations).
- [ ] Instrument tags have been properly split into `parameter`, `device_type`, and `loop_id`.
- [ ] Line styles (solid vs. dotted) have been correctly mapped to `Piping` vs. `Electrical` mediums.