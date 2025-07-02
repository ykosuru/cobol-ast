#!/usr/bin/env python3
"""
COBOL Business Logic Visualizer
Generates interactive HTML visualization from COBOL AST files
"""

import re
import json
import argparse
from typing import Dict, List, Tuple
from pathlib import Path
import logging

# Set up logging for better debugging and user feedback
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Color mapping for different procedure types based on their business logic
PROCEDURE_COLORS = {
    "main": "#e74c3c",      # Red for main logic
    "sql": "#8e44ad",       # Purple for SQL operations
    "data": "#e67e22",      # Orange for data manipulation
    "control": "#3498db",   # Blue for control logic
    "file": "#1abc9c",      # Teal for file operations
    "execution": "#27ae60", # Green for execution control
    "mixed": "#34495e"      # Dark gray for mixed operations
}

def parse_ast_file(file_path: str) -> Dict:
    """
    Parse the AST file and extract comprehensive program data.

    Args:
        file_path (str): Path to the AST file.

    Returns:
        Dict: Parsed AST data with program name, procedures, metadata, and statement analysis.

    Raises:
        FileNotFoundError: If the AST file does not exist.
        ValueError: If the AST file is empty or malformed.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logging.error(f"AST file '{file_path}' not found")
        raise
    except UnicodeDecodeError:
        logging.error(f"AST file '{file_path}' is not valid UTF-8")
        raise

    if not content.strip():
        logging.error("AST file is empty")
        raise ValueError("AST file is empty")

    ast_data = {
        "program": {"name": "", "procedures": []},
        "metadata": {},
        "statement_analysis": {}
    }

    # Extract program name
    program_match = re.search(r'\(ENHANCED-COBOL-ANALYSIS\s+"([^"]+)"', content)
    if program_match:
        ast_data["program"]["name"] = program_match.group(1)
    else:
        logging.warning("Program name not found in AST file")

    # Extract metadata
    metadata_match = re.search(r'\(METADATA\s+([\s\S]+?)\)\s+\(', content)
    if metadata_match:
        metadata_content = metadata_match.group(1)
        for line in metadata_content.split('\n'):
            if '(' in line and ')' in line:
                match = re.search(r'\(([^)]+)\s+"?([^")]+)"?\)', line.strip())
                if match:
                    key = match.group(1).replace('-', '_').lower()
                    value = match.group(2)
                    try:
                        ast_data["metadata"][key] = int(value)
                    except ValueError:
                        ast_data["metadata"][key] = value

    # Extract statement analysis
    stmt_analysis_match = re.search(r'\(STATEMENT-ANALYSIS\s+\(STATEMENT-DISTRIBUTION\s+([\s\S]+?)\)\s+\)', content)
    if stmt_analysis_match:
        stmt_content = stmt_analysis_match.group(1)
        stmt_matches = re.finditer(r'\(([A-Z_-]+)\s+(\d+)\)', stmt_content)
        for match in stmt_matches:
            stmt_type = match.group(1)
            try:
                count = int(match.group(2))
                ast_data["statement_analysis"][stmt_type] = count
            except ValueError:
                logging.warning(f"Invalid statement count for type '{stmt_type}'")

    # Extract procedures with detailed analysis
    procedure_matches = re.finditer(
        r'\(PROCEDURE\s+"([^"]+)"\s+\(SCORE\s+([\d.]+)\)\s+\(START-LINE\s+(\d+)\)\s+\(END-LINE\s+(\d+)\)\s+'
        r'\(REASONING\s+"([^"]+)"\)\s+\(PERFORM-REFERENCES\s+(\d+)\)\s+\(STATEMENT-DISTRIBUTION\s+([\s\S]+?)\)\s+'
        r'\(STATEMENTS\s+([\s\S]+?)\)\s+\)', 
        content
    )

    for proc_match in procedure_matches:
        proc_name = proc_match.group(1)
        try:
            score = float(proc_match.group(2))
            start_line = int(proc_match.group(3))
            end_line = int(proc_match.group(4))
            perform_refs = int(proc_match.group(6))
        except ValueError as e:
            logging.error(f"Invalid numeric data in procedure '{proc_name}': {str(e)}")
            continue
        reasoning = proc_match.group(5)

        # Parse statement distribution
        stmt_dist_content = proc_match.group(7)
        statement_distribution = {}
        stmt_dist_matches = re.finditer(r'\(([A-Z_-]+)\s+(\d+)\)', stmt_dist_content)
        for match in stmt_dist_matches:
            try:
                statement_distribution[match.group(1)] = int(match.group(2))
            except ValueError:
                logging.warning(f"Invalid distribution count for '{match.group(1)}' in procedure '{proc_name}'")

        # Parse individual statements
        statements = []
        stmt_content = proc_match.group(8)
        stmt_matches = re.finditer(r'\(([A-Z_-]+)\s+"([^"]+)"\s+(\d+)\)', stmt_content)

        for stmt_match in stmt_matches:
            stmt_type = stmt_match.group(1)
            stmt_text = stmt_match.group(2)
            try:
                stmt_line = int(stmt_match.group(3))
                statements.append({
                    "type": stmt_type,
                    "text": stmt_text,
                    "line": stmt_line
                })
            except ValueError:
                logging.warning(f"Invalid line number in statement for procedure '{proc_name}'")

        ast_data["program"]["procedures"].append({
            "name": proc_name,
            "score": score,
            "start_line": start_line,
            "end_line": end_line,
            "reasoning": reasoning,
            "perform_references": perform_refs,
            "statement_distribution": statement_distribution,
            "statements": statements
        })

    if not ast_data["program"]["procedures"]:
        logging.warning("No procedures found in AST file")

    return ast_data

def classify_procedure_type(proc: Dict) -> str:
    """
    Classify procedure based on its statement distribution and reasoning.

    Args:
        proc (Dict): Procedure data with statement distribution and reasoning.

    Returns:
        str: Classified procedure type (e.g., 'sql', 'main', 'data').
    """
    stmt_dist = proc.get("statement_distribution", {})
    reasoning = proc.get("reasoning", "").lower()

    sql_count = stmt_dist.get("EXEC_SQL", 0) + stmt_dist.get("END-EXEC", 0)
    data_count = stmt_dist.get("MOVE", 0) + stmt_dist.get("SET", 0) + stmt_dist.get("INITIALIZE", 0)
    file_count = stmt_dist.get("READ", 0) + stmt_dist.get("WRITE", 0) + stmt_dist.get("OPEN", 0) + stmt_dist.get("CLOSE", 0)
    control_count = stmt_dist.get("IF", 0) + stmt_dist.get("PERFORM", 0) + stmt_dist.get("EVALUATE", 0)

    total_operations = sql_count + data_count + file_count + control_count

    if total_operations == 0:
        return "execution"

    if sql_count / total_operations > 0.4:
        return "sql"
    elif "main" in reasoning or "main procedure pattern" in reasoning:
        return "main"
    elif file_count / total_operations > 0.4:
        return "file"
    elif data_count / total_operations > 0.6:
        return "data"
    elif control_count / total_operations > 0.4:
        return "control"
    else:
        return "mixed"

def group_statements_into_blocks(statements: List[Dict]) -> List[Dict]:
    """
    Group related statements into logical blocks (IF/END-IF, EXEC SQL/END-EXEC, etc.).

    Args:
        statements (List[Dict]): List of statement dictionaries.

    Returns:
        List[Dict]: List of grouped statement blocks.
    """
    blocks = []
    i = 0

    while i < len(statements):
        stmt = statements[i]
        stmt_type = stmt["type"]

        if stmt_type in ["STATEMENT", "RECOVERED", "END_CLAUSE"]:
            i += 1
            continue

        if stmt_type == "IF":
            end_line = stmt["line"]
            block_statements = [stmt]
            i += 1
            while i < len(statements):
                next_stmt = statements[i]
                block_statements.append(next_stmt)
                if next_stmt["type"] == "END-IF":
                    end_line = next_stmt["line"]
                    break
                i += 1

            blocks.append({
                "type": "IF_BLOCK",
                "label": "IF Condition",
                "statements": block_statements,
                "start_line": stmt["line"],
                "end_line": end_line,
                "description": f"Conditional logic: {stmt['text'][:50]}..."
            })

        elif stmt_type == "EXEC_SQL":
            end_line = stmt["line"]
            block_statements = [stmt]
            i += 1
            while i < len(statements):
                next_stmt = statements[i]
                block_statements.append(next_stmt)
                if next_stmt["type"] == "END-EXEC":
                    end_line = next_stmt["line"]
                    break
                i += 1

            sql_operation = "SQL Query"
            if "SELECT" in stmt["text"].upper():
                sql_operation = "SQL SELECT"
            elif "INSERT" in stmt["text"].upper():
                sql_operation = "SQL INSERT"
            elif "UPDATE" in stmt["text"].upper():
                sql_operation = "SQL UPDATE"
            elif "DELETE" in stmt["text"].upper():
                sql_operation = "SQL DELETE"

            blocks.append({
                "type": "SQL_BLOCK",
                "label": sql_operation,
                "statements": block_statements,
                "start_line": stmt["line"],
                "end_line": end_line,
                "description": f"Database operation: {stmt['text'][:50]}..."
            })

        elif stmt_type == "EVALUATE":
            end_line = stmt["line"]
            block_statements = [stmt]
            i += 1
            while i < len(statements):
                next_stmt = statements[i]
                block_statements.append(next_stmt)
                if next_stmt["type"] == "END-EVALUATE":
                    end_line = next_stmt["line"]
                    break
                i += 1

            blocks.append({
                "type": "EVALUATE_BLOCK",
                "label": "EVALUATE",
                "statements": block_statements,
                "start_line": stmt["line"],
                "end_line": end_line,
                "description": f"Multi-way branch: {stmt['text'][:50]}..."
            })

        else:
            if stmt_type == "PERFORM":
                label = "PERFORM Call"
                description = f"Calls: {stmt['text']}"
            elif stmt_type == "MOVE":
                label = "Data Move"
                description = f"Move: {stmt['text'][:50]}..."
            elif stmt_type == "SET":
                label = "Set Value"
                description = f"Set: {stmt['text'][:50]}..."
            elif stmt_type == "INITIALIZE":
                label = "Initialize"
                description = f"Init: {stmt['text'][:50]}..."
            elif stmt_type in ["READ", "WRITE"]:
                label = f"File {stmt_type}"
                description = f"{stmt_type}: {stmt['text'][:50]}..."
            elif stmt_type in ["OPEN", "CLOSE"]:
                label = f"File {stmt_type}"
                description = f"{stmt_type}: {stmt['text'][:50]}..."
            elif stmt_type == "ADD":
                label = "Add"
                description = f"Add: {stmt['text'][:50]}..."
            elif stmt_type == "ACCEPT":
                label = "Accept"
                description = f"Accept: {stmt['text'][:50]}..."
            elif stmt_type == "INSPECT":
                label = "Inspect"
                description = f"Inspect: {stmt['text'][:50]}..."
            elif stmt_type == "UNSTRING":
                label = "Unstring"
                description = f"Unstring: {stmt['text'][:50]}..."
            elif stmt_type == "GOBACK":
                label = "Return"
                description = "Program return"
            else:
                label = stmt_type
                description = f"{stmt_type}: {stmt['text'][:50]}..."

            blocks.append({
                "type": stmt_type,
                "label": label,
                "statements": [stmt],
                "start_line": stmt["line"],
                "end_line": stmt["line"],
                "description": description
            })

        i += 1

    return blocks

def get_block_color(block_type: str) -> str:
    """
    Get color for statement block based on its type.

    Args:
        block_type (str): Type of the statement block.

    Returns:
        str: Hex color code for the block.
    """
    if block_type in ["IF_BLOCK", "EVALUATE_BLOCK", "PERFORM"]:
        return "#3498db"  # Blue for control flow
    elif block_type == "SQL_BLOCK":
        return "#8e44ad"  # Purple for SQL
    elif block_type in ["MOVE", "SET", "INITIALIZE", "ADD", "UNSTRING"]:
        return "#e67e22"  # Orange for data operations
    elif block_type in ["READ", "WRITE", "OPEN", "CLOSE"]:
        return "#1abc9c"  # Teal for file operations
    elif block_type in ["INSPECT", "ACCEPT"]:
        return "#f39c12"  # Gold for validation/input
    elif block_type == "GOBACK":
        return "#e74c3c"  # Red for program control
    else:
        return "#95a5a6"  # Gray for other

def generate_procedure_nodes(procedures: List[Dict]) -> Tuple[List[Dict], Dict]:
    """
    Generate nodes for procedures and their statement blocks.

    Args:
        procedures (List[Dict]): List of procedure dictionaries.

    Returns:
        Tuple[List[Dict], Dict]: List of nodes and dictionary of statement blocks by procedure.
    """
    nodes = []
    statement_blocks = {}
    max_score = max(proc["score"] for proc in procedures) if procedures else 1
    min_score = min(proc["score"] for proc in procedures) if procedures else 1

    for i, proc in enumerate(procedures):
        proc_type = classify_procedure_type(proc)
        color = PROCEDURE_COLORS.get(proc_type, PROCEDURE_COLORS["mixed"])

        size_factor = (proc["score"] - min_score) / (max_score - min_score) if max_score != min_score else 0.5
        size = 30 + (size_factor * 40)

        display_name = proc["name"]
        if len(display_name) > 12:
            display_name = display_name[:9] + "..."

        total_statements = sum(proc.get("statement_distribution", {}).values())

        tooltip = f"<b>{proc['name']}</b><br/>"
        tooltip += f"Complexity Score: {proc['score']}<br/>"
        tooltip += f"Statements: {total_statements}<br/>"
        tooltip += f"Primary Type: {proc_type.upper()}<br/>"
        tooltip += f"Lines: {proc['start_line']}-{proc['end_line']}<br/>"
        tooltip += f"Business Logic: {proc['reasoning']}"

        proc_node = {
            "id": f"proc_{i}",
            "label": display_name,
            "title": tooltip,
            "size": size,
            "color": color,
            "font": {
                "color": "white",
                "size": 14,
                "face": "Arial Black"
            },
            "borderWidth": 4,
            "borderColor": "white",
            "shadow": {
                "enabled": True,
                "color": "rgba(0,0,0,0.3)",
                "size": 12
            },
            "group": "procedure",
            "level": 0
        }
        nodes.append(proc_node)

        blocks = group_statements_into_blocks(proc.get("statements", []))
        statement_blocks[f"proc_{i}"] = []

        for j, block in enumerate(blocks):
            block_id = f"stmt_{i}_{j}"
            block_color = get_block_color(block["type"])

            block_tooltip = f"<b>{block['label']}</b><br/>"
            block_tooltip += f"Lines: {block['start_line']}"
            if block['end_line'] != block['start_line']:
                block_tooltip += f"-{block['end_line']}"
            block_tooltip += f"<br/>{block['description']}<br/><br/>"

            block_tooltip += "<b>Statements:</b><br/>"
            for stmt in block["statements"][:3]:
                block_tooltip += f"• {stmt['text'][:60]}{'...' if len(stmt['text']) > 60 else ''}<br/>"
            if len(block["statements"]) > 3:
                block_tooltip += f"• ... and {len(block['statements']) - 3} more"

            statement_node = {
                "id": block_id,
                "label": block["label"],
                "title": block_tooltip,
                "size": 15 + (len(block["statements"]) * 2),
                "color": block_color,
                "font": {
                    "color": "white",
                    "size": 10,
                    "face": "Arial"
                },
                "borderWidth": 2,
                "borderColor": "white",
                "shadow": {
                    "enabled": True,
                    "color": "rgba(0,0,0,0.2)",
                    "size": 5
                },
                "group": f"statement_{i}",
                "level": 1,
                "hidden": True,
                "parent_proc": f"proc_{i}"
            }
            nodes.append(statement_node)
            statement_blocks[f"proc_{i}"].append(statement_node)

    return nodes, statement_blocks

def generate_procedure_edges(procedures: List[Dict], statement_blocks: Dict) -> List[Dict]:
    """
    Generate edges based on PERFORM relationships and statement flow.

    Args:
        procedures (List[Dict]): List of procedure dictionaries.
        statement_blocks (Dict): Dictionary of statement blocks by procedure.

    Returns:
        List[Dict]: List of edge dictionaries.
    """
    edges = []
    proc_name_to_id = {proc["name"].lower(): f"proc_{i}" for i, proc in enumerate(procedures)}
    edge_id = 0

    for i, proc in enumerate(procedures):
        for stmt in proc.get("statements", []):
            if stmt["type"] == "PERFORM":
                perform_match = re.search(r'PERFORM\s+([^\s.]+)', stmt["text"])
                if perform_match:
                    target_name = perform_match.group(1).lower()
                    if target_name in proc_name_to_id:
                        target_id = proc_name_to_id[target_name]
                        edge = {
                            "id": f"edge_{edge_id}",
                            "from": f"proc_{i}",
                            "to": target_id,
                            "arrows": {
                                "to": {
                                    "enabled": True,
                                    "scaleFactor": 1.2
                                }
                            },
                            "color": {
                                "color": "#3498db",
                                "opacity": 0.8
                            },
                            "width": 3,
                            "smooth": {
                                "type": "continuous"
                            },
                            "dashes": [8, 4],
                            "label": "PERFORM",
                            "font": {"size": 10, "color": "#2980b9"}
                        }
                        edges.append(edge)
                        edge_id += 1

    for proc_id, blocks in statement_blocks.items():
        if blocks:
            edge = {
                "id": f"edge_{edge_id}",
                "from": proc_id,
                "to": blocks[0]["id"],
                "arrows": {
                    "to": {
                        "enabled": True,
                        "scaleFactor": 0.8
                    }
                },
                "color": {
                    "color": "#7f8c8d",
                    "opacity": 0.6
                },
                "width": 2,
                "smooth": {
                    "type": "continuous"
                },
                "hidden": True,
                "group": f"flow_{proc_id}"
            }
            edges.append(edge)
            edge_id += 1

            for j in range(len(blocks) - 1):
                edge = {
                    "id": f"edge_{edge_id}",
                    "from": blocks[j]["id"],
                    "to": blocks[j + 1]["id"],
                    "arrows": {
                        "to": {
                            "enabled": True,
                            "scaleFactor": 0.8
                        }
                    },
                    "color": {
                        "color": "#bdc3c7",
                        "opacity": 0.7
                    },
                    "width": 1,
                    "smooth": {
                        "type": "continuous"
                    },
                    "hidden": True,
                    "group": f"flow_{proc_id}"
                }
                edges.append(edge)
                edge_id += 1

    return edges

def generate_html_visualization(ast_data: Dict) -> str:
    """
    Generate the complete HTML visualization with integrated JavaScript functions.

    Args:
        ast_data (Dict): Parsed AST data.

    Returns:
        str: HTML content for the visualization.
    """
    program_name = ast_data["program"]["name"] or "Unnamed Program"
    procedures = ast_data["program"]["procedures"]
    metadata = ast_data.get("metadata", {})
    stmt_analysis = ast_data.get("statement_analysis", {})

    nodes, statement_blocks = generate_procedure_nodes(procedures)
    edges = generate_procedure_edges(procedures, statement_blocks)

    total_procedures = len(procedures)
    business_logic_procs = len([p for p in procedures if "business logic" in p.get("reasoning", "").lower()])
    total_statements = metadata.get("total_statements", 0)
    sql_operations = metadata.get("sql_statements_count", 0)

    statement_stats = ""
    for stmt_type, count in sorted(stmt_analysis.items(), key=lambda x: x[1], reverse=True)[:8]:
        statement_stats += f'''
            <div class="statement-stat">
                <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 5px;">{count}</div>
                <div style="font-size: 0.9em;">{stmt_type}</div>
            </div>
        '''

    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COBOL Business Logic Visualization - {program_name}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(15px);
        }}

        .header h1 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 2.8em;
            font-weight: 800;
            text-align: center;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .subtitle {{
            text-align: center;
            font-size: 1.2em;
            color: #7f8c8d;
            margin-bottom: 25px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-top: 25px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            font-weight: 700;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
        }}

        .stat-value {{
            font-size: 2.2em;
            font-weight: 900;
            margin-bottom: 5px;
        }}

        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .main-section {{
            background: rgba(255, 255, 255, 0.95);
            margin: 30px 0;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(15px);
        }}

        .section-title {{
            font-size: 2.2em;
            color: #2c3e50;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 4px solid #3498db;
            font-weight: 800;
        }}

        .visualization-container {{
            width: 100%;
            height: 700px;
            border: 3px solid #ecf0f1;
            border-radius: 15px;
            background: linear-gradient(45deg, #f8f9fa, #ffffff);
            position: relative;
            overflow: hidden;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.1);
        }}

        .controls {{
            margin-bottom: 25px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
        }}

        .control-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 30px;
            cursor: pointer;
            font-weight: 700;
            font-size: 1.1em;
            transition: all 0.3s ease;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
        }}

        .control-btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        }}

        .legend {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 25px;
            padding: 25px;
            background: rgba(52, 152, 219, 0.1);
            border-radius: 15px;
            border: 2px solid rgba(52, 152, 219, 0.2);
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            font-weight: 600;
        }}

        .legend-color {{
            width: 25px;
            height: 25px;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }}

        .info-panel {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 20px;
            border-radius: 15px;
            max-width: 320px;
            font-size: 0.95em;
            z-index: 1000;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
        }}

        .statement-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .statement-stat {{
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            color: #2c3e50;
            font-weight: 600;
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .controls {{
                flex-direction: column;
                align-items: stretch;
            }}

            .control-btn {{
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header with Statistics -->
        <div class="header">
            <h1>🚀 COBOL Business Logic Analyzer</h1>
            <div class="subtitle">Interactive visualization of {program_name} business logic procedures and execution flow</div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{total_procedures}</div>
                    <div class="stat-label">Total Procedures</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{business_logic_procs}</div>
                    <div class="stat-label">Business Logic</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_statements}</div>
                    <div class="stat-label">Total Statements</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sql_operations}</div>
                    <div class="stat-label">SQL Operations</div>
                </div>
            </div>
        </div>

        <!-- Main Business Logic Visualization -->
        <div class="main-section">
            <h2 class="section-title">🎯 Business Logic Procedure Network</h2>

            <div class="controls">
                <button class="control-btn" onclick="resetView()">🔄 Reset View</button>
                <button class="control-btn" onclick="focusHighComplexity()">📈 Focus High Complexity</button>
                <button class="control-btn" onclick="showMainFlow()">🏗️ Show Main Flow</button>
                <button class="control-btn" onclick="toggleAllStatements()">🔍 Toggle Statement Details</button>
            </div>

            <div class="visualization-container" id="networkContainer">
                <div class="info-panel" id="infoPanel">
                    <strong>💡 Business Logic Explorer:</strong><br/>
                    • <strong>Click procedure bubbles</strong> to expand/collapse statements<br/>
                    • <strong>Click statement bubbles</strong> for detailed information<br/>
                    • <strong>Drag to pan</strong> around the network<br/>
                    • <strong>Scroll to zoom</strong> in/out<br/>
                    • <strong>Larger bubbles</strong> = higher complexity<br/>
                    • <strong>Blue arrows</strong> show PERFORM calls<br/>
                    • <strong>Gray arrows</strong> show statement flow<br/><br/>
                    <strong>🎨 Color Legend:</strong><br/>
                    🟣 SQL Operations | 🟠 Data Operations<br/>
                    🔵 Control Logic | 🟦 File Operations<br/>
                    🟡 Validation | 🔴 Program Control
                </div>
            </div>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {PROCEDURE_COLORS['sql']};"></div>
                    <span>SQL Operations</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {PROCEDURE_COLORS['data']};"></div>
                    <span>Data Manipulation</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {PROCEDURE_COLORS['control']};"></div>
                    <span>Control Logic</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {PROCEDURE_COLORS['execution']};"></div>
                    <span>Execution Control</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {PROCEDURE_COLORS['file']};"></div>
                    <span>File Operations</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {PROCEDURE_COLORS['main']};"></div>
                    <span>Main Business Logic</span>
                </div>
            </div>
        </div>

        <!-- Statement Statistics -->
        <div class="main-section">
            <h2 class="section-title">📊 Statement Distribution</h2>
            <div class="statement-stats">
                {statement_stats}
            </div>
        </div>
    </div>

    <script>
        // Business Logic Network Data
        const businessLogicData = {{
            nodes: new vis.DataSet({json.dumps(nodes, indent=2)}),
            edges: new vis.DataSet({json.dumps(edges, indent=2)})
        }};
        const statementBlocks = {json.dumps(statement_blocks, indent=2)};
        let expandedProcedures = new Set();
        let network = null;
        let isPhysicsActive = false;

        // Network configuration with improved physics settings
        const networkOptions = {{
            physics: {{
                enabled: false, // Start with physics disabled
                stabilization: {{ iterations: 200 }},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.09,
                    avoidOverlap: 0.5
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: false,
                hideNodesOnDrag: false,
                zoomView: true,
                dragView: true
            }},
            nodes: {{
                shape: 'dot',
                scaling: {{ min: 20, max: 100 }},
                font: {{ size: 14, face: 'Arial Black', color: 'white' }},
                borderWidth: 3,
                shadow: true
            }},
            edges: {{
                width: 3,
                color: {{ inherit: 'from' }},
                smooth: {{ type: 'continuous', roundness: 0.5 }},
                arrows: {{ to: {{ enabled: true, scaleFactor: 1.2 }} }},
                shadow: true
            }},
            layout: {{
                improvedLayout: true,
                clusterThreshold: 150,
                hierarchical: {{
                    enabled: false
                }}
            }}
        }};

        function initializeVisualization() {{
            const container = document.getElementById('networkContainer');
            if (!container) {{
                console.error('Network container not found');
                return;
            }}

            if (!businessLogicData.nodes || businessLogicData.nodes.length === 0) {{
                container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; font-size: 1.5em; color: #7f8c8d; text-align: center;"><div>🔍 No business logic procedures found in AST<br/><small>Check AST parsing or procedure definitions</small></div></div>';
                return;
            }}

            network = new vis.Network(container, businessLogicData, networkOptions);

            // Enable physics temporarily for initial layout
            setTimeout(() => {{
                if (network) {{
                    network.setOptions({{ physics: {{ enabled: true }} }});
                    isPhysicsActive = true;
                }}
            }}, 100);

            // Disable physics after stabilization
            network.once('stabilizationIterationsDone', function() {{
                setTimeout(() => {{
                    if (network) {{
                        network.setOptions({{ physics: {{ enabled: false }} }});
                        isPhysicsActive = false;
                        network.fit({{ animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }} }});
                    }}
                }}, 500);
            }});

            network.on('click', function(params) {{
                if (!network || !businessLogicData) return;
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const allNodes = businessLogicData.nodes.get();
                    const node = allNodes.find(n => n.id === nodeId);
                    if (node) {{
                        if (node.group === 'procedure') {{
                            toggleProcedureStatements(nodeId);
                        }} else {{
                            showNodeDetails(node);
                        }}
                    }}
                }}
            }});

            network.on('doubleClick', function(params) {{
                if (!network || !businessLogicData) return;
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const allNodes = businessLogicData.nodes.get();
                    const node = allNodes.find(n => n.id === nodeId);
                    if (node && node.group === 'procedure') {{
                        focusProcedure(nodeId);
                    }}
                }}
            }});

            network.on('hoverNode', function() {{
                document.body.style.cursor = 'pointer';
            }});

            network.on('blurNode', function() {{
                document.body.style.cursor = 'default';
            }});
        }}

        function toggleProcedureStatements(procId) {{
            if (!network || !businessLogicData) return;

            const isExpanded = expandedProcedures.has(procId);
            const allNodes = businessLogicData.nodes.get();
            const statementNodes = allNodes.filter(n => n.parent_proc === procId);
            const allEdges = businessLogicData.edges.get();
            const flowEdges = allEdges.filter(e => e.group === `flow_${{procId}}`);

            // Temporarily disable physics during node updates to prevent flickering
            if (isPhysicsActive) {{
                network.setOptions({{ physics: {{ enabled: false }} }});
            }}

            if (isExpanded) {{
                // Collapse: hide statement nodes and edges
                const nodeUpdates = statementNodes.map(node => ({{ id: node.id, hidden: true }}));
                const edgeUpdates = flowEdges.map(edge => ({{ id: edge.id, hidden: true }}));
                
                if (nodeUpdates.length > 0) businessLogicData.nodes.update(nodeUpdates);
                if (edgeUpdates.length > 0) businessLogicData.edges.update(edgeUpdates);
                expandedProcedures.delete(procId);
            }} else {{
                // Expand: show statement nodes and edges
                const nodeUpdates = statementNodes.map(node => ({{ id: node.id, hidden: false }}));
                const edgeUpdates = flowEdges.map(edge => ({{ id: edge.id, hidden: false }}));
                
                if (nodeUpdates.length > 0) businessLogicData.nodes.update(nodeUpdates);
                if (edgeUpdates.length > 0) businessLogicData.edges.update(edgeUpdates);
                expandedProcedures.add(procId);
                
                // Focus on the expanded procedure after a short delay
                setTimeout(() => {{
                    const relatedNodeIds = [procId, ...statementNodes.map(n => n.id)];
                    network.fit({{ nodes: relatedNodeIds, animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }} }});
                }}, 200);
            }}

            // Keep physics disabled to prevent flickering
            if (isPhysicsActive) {{
                setTimeout(() => {{
                    // Only re-enable physics if we were in physics mode before
                    // and only for a brief moment to adjust positions
                    network.setOptions({{ physics: {{ enabled: true }} }});
                    setTimeout(() => {{
                        network.setOptions({{ physics: {{ enabled: false }} }});
                    }}, 1000);
                }}, 300);
            }}
        }}

        function showNodeDetails(node) {{
            if (!node) return;
            let details = `<strong>${{node.label}}</strong><br/>`;
            if (node.title) {{
                details += node.title.replace(/<[^>]*>/g, '').replace(/\\n/g, '<br/>');
            }}

            let detailsPanel = document.getElementById('detailsPanel');
            if (!detailsPanel) {{
                detailsPanel = document.createElement('div');
                detailsPanel.id = 'detailsPanel';
                detailsPanel.style.cssText = `
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: linear-gradient(135deg, #2c3e50, #34495e);
                    color: white;
                    padding: 25px;
                    border-radius: 20px;
                    max-width: 450px;
                    z-index: 2000;
                    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5);
                    border: 2px solid #3498db;
                `;
                document.body.appendChild(detailsPanel);
            }}

            detailsPanel.innerHTML = `
                ${{details}}
                <br/><br/>
                <button onclick="closeDetails()" style="
                    background: linear-gradient(135deg, #3498db, #2980b9);
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 25px;
                    cursor: pointer;
                    float: right;
                    font-weight: 600;
                    transition: all 0.3s ease;
                " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    ✕ Close
                </button>
            `;
            detailsPanel.style.display = 'block';
        }}

        function closeDetails() {{
            const detailsPanel = document.getElementById('detailsPanel');
            if (detailsPanel) detailsPanel.style.display = 'none';
        }}

        function resetView() {{
            if (!network) return;
            
            // Reset all expanded procedures
            expandedProcedures.forEach(procId => {{
                toggleProcedureStatements(procId);
            }});
            
            setTimeout(() => {{
                network.fit({{ animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }} }});
            }}, 300);
        }}

        function focusHighComplexity() {{
            if (!network || !businessLogicData) return;
            const allNodes = businessLogicData.nodes.get();
            const highComplexityNodes = allNodes.filter(node => node.size > 50).map(node => node.id);
            if (highComplexityNodes.length > 0) {{
                network.focus(highComplexityNodes[0], {{
                    scale: 1.5,
                    animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }}
                }});
                network.selectNodes(highComplexityNodes);
            }}
        }}

        function showMainFlow() {{
            if (!network || !businessLogicData) return;
            const allNodes = businessLogicData.nodes.get();
            const mainNodes = allNodes.filter(node => node.color === '{PROCEDURE_COLORS["main"]}').map(node => node.id);
            if (mainNodes.length > 0) {{
                network.focus(mainNodes[0], {{
                    scale: 1.2,
                    animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }}
                }});
                network.selectNodes(mainNodes);
            }}
        }}

        function toggleAllStatements() {{
            if (!network || !businessLogicData) return;
            const allNodes = businessLogicData.nodes.get();
            const allProcedures = allNodes.filter(n => n.group === 'procedure');
            const shouldExpand = expandedProcedures.size < allProcedures.length;

            // Disable physics completely during bulk operations
            network.setOptions({{ physics: {{ enabled: false }} }});

            allProcedures.forEach((proc, index) => {{
                setTimeout(() => {{
                    if (shouldExpand && !expandedProcedures.has(proc.id)) {{
                        toggleProcedureStatements(proc.id);
                    }} else if (!shouldExpand && expandedProcedures.has(proc.id)) {{
                        toggleProcedureStatements(proc.id);
                    }}
                }}, index * 50); // Stagger the toggles to reduce visual chaos
            }});
        }}

        function focusProcedure(procId) {{
            if (!network || !businessLogicData) return;
            if (!expandedProcedures.has(procId)) {{
                toggleProcedureStatements(procId);
            }}

            setTimeout(() => {{
                const allNodes = businessLogicData.nodes.get();
                const relatedNodes = [procId, ...allNodes.filter(n => n.parent_proc === procId).map(n => n.id)];
                network.focus(procId, {{
                    scale: 1.5,
                    animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }}
                }});
                network.selectNodes(relatedNodes);
            }}, 200);
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            initializeVisualization();
        }});

        window.addEventListener('resize', function() {{
            if (network) network.redraw();
        }});

        document.addEventListener('click', function(event) {{
            const detailsPanel = document.getElementById('detailsPanel');
            if (detailsPanel && detailsPanel.style.display === 'block' && !detailsPanel.contains(event.target)) {{
                closeDetails();
            }}
        }});
    </script>
</body>
</html>
'''

    return html_template

def main():
    """
    Main function to process AST file and generate HTML visualization.

    Parses command-line arguments, reads the AST file, generates the visualization,
    and saves it to an HTML file.
    """
    parser = argparse.ArgumentParser(description="Generate COBOL Business Logic Visualization from AST file")
    parser.add_argument("ast_file", help="Path to the AST file")
    parser.add_argument("-o", "--output", help="Output HTML file (default: auto-generated)")

    args = parser.parse_args()

    try:
        logging.info("Parsing AST file...")
        ast_data = parse_ast_file(args.ast_file)
        program_name = ast_data["program"]["name"]

        if not program_name:
            logging.error("Could not extract program name from AST file")
            return

        output_file = args.output if args.output else f"{program_name}_business_logic_visualization.html"

        logging.info("Generating business logic visualization...")
        html_content = generate_html_visualization(ast_data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"Business Logic Visualization generated: '{output_file}'")
        logging.info("Program Analysis Summary:")
        logging.info(f"  Program: {program_name}")
        logging.info(f"  Total Procedures: {len(ast_data['program']['procedures'])}")
        logging.info(f"  Total Statements: {ast_data.get('metadata', {}).get('total_statements', 'N/A')}")
        logging.info(f"  SQL Operations: {ast_data.get('metadata', {}).get('sql_statements_count', 'N/A')}")

        procedures = ast_data["program"]["procedures"]
        if procedures:
            type_counts = {}
            for proc in procedures:
                proc_type = classify_procedure_type(proc)
                type_counts[proc_type] = type_counts.get(proc_type, 0) + 1

            logging.info("Procedure Types:")
            for proc_type, count in sorted(type_counts.items()):
                logging.info(f"  {proc_type.title()}: {count}")

        logging.info("Usage:")
        logging.info(f"  Open '{output_file}' in a modern web browser")
        logging.info("  Click procedure bubbles to expand/collapse statement details")
        logging.info("  Click statement bubbles for detailed information")
        logging.info("  Use control buttons to focus on specific aspects")
        logging.info("  Drag and zoom to explore the network")
        logging.info("  Double-click procedures to auto-focus and expand")

    except FileNotFoundError:
        logging.error(f"AST file '{args.ast_file}' not found")
    except ValueError as e:
        logging.error(f"Error processing AST file: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
