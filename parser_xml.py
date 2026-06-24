#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd
import argparse
import csv
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_namespace(root: ET.Element) -> Dict[str, str]:
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0].strip("{")
        return {"p": ns_uri}
    return {"p": ""}


def q(tag: str, ns: Dict[str, str]) -> str:
    uri = ns.get("p", "")
    return f"{{{uri}}}{tag}" if uri else tag


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def safe_findall(elem: ET.Element, path: str, ns: Dict[str, str]) -> List[ET.Element]:
    try:
        return elem.findall(path, ns)
    except SyntaxError:
        return elem.findall(path.replace("p:", ""))


def safe_find(elem: ET.Element, path: str, ns: Dict[str, str]) -> Optional[ET.Element]:
    try:
        return elem.find(path, ns)
    except SyntaxError:
        return elem.find(path.replace("p:", ""))


def parse_bool_like(value: Optional[str]) -> int:
    return 1 if value and value.lower() == "true" else 0


def count_regex(pattern: str, text: str, flags: int = 0) -> int:
    return len(re.findall(pattern, text, flags))


def extract_st_text(root: ET.Element, ns: Dict[str, str]) -> str:
    texts: List[str] = []
    for st_elem in safe_findall(root, ".//p:ST", ns):
        for child in st_elem.iter():
            if child.text:
                texts.append(child.text)
    return "\n".join(texts)


def extract_structure_features(root: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
    pous = safe_findall(root, ".//p:pou", ns)
    programs = [p for p in pous if p.attrib.get("pouType") == "program"]
    function_blocks = [p for p in pous if p.attrib.get("pouType") == "functionBlock"]
    tasks = safe_findall(root, ".//p:task", ns)

    return {
        "n_pous": len(pous),
        "n_programs": len(programs),
        "n_function_blocks": len(function_blocks),
        "n_tasks": len(tasks),
        "task_intervals": ";".join(t.attrib.get("interval", "") for t in tasks if t.attrib.get("interval")),
        "task_priorities": ";".join(t.attrib.get("priority", "") for t in tasks if t.attrib.get("priority")),
        "has_ld": int(len(safe_findall(root, ".//p:LD", ns)) > 0),
        "has_st": int(len(safe_findall(root, ".//p:ST", ns)) > 0),
        "has_fbd": int(len(safe_findall(root, ".//p:FBD", ns)) > 0),
        "has_sfc": int(len(safe_findall(root, ".//p:SFC", ns)) > 0),
        "pou_names": ";".join(sorted([p.attrib.get("name", "") for p in pous if p.attrib.get("name")])),
        "function_block_names": ";".join(sorted([p.attrib.get("name", "") for p in function_blocks if p.attrib.get("name")])),
    }


def extract_declared_variables(root: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
    input_vars = safe_findall(root, ".//p:inputVars/p:variable", ns)
    output_vars = safe_findall(root, ".//p:outputVars/p:variable", ns)
    local_vars = safe_findall(root, ".//p:localVars/p:variable", ns)

    bool_inputs = 0
    bool_outputs = 0
    int_inputs = 0
    int_outputs = 0
    physical_inputs = 0
    physical_outputs = 0
    derived_local_vars = 0

    input_names, output_names, local_names = [], [], []

    for var in input_vars:
        input_names.append(var.attrib.get("name", ""))
        if var.attrib.get("address", "").startswith("%IX"):
            physical_inputs += 1
        if safe_find(var, "./p:type/p:BOOL", ns) is not None:
            bool_inputs += 1
        if safe_find(var, "./p:type/p:INT", ns) is not None:
            int_inputs += 1

    for var in output_vars:
        output_names.append(var.attrib.get("name", ""))
        if var.attrib.get("address", "").startswith("%QX"):
            physical_outputs += 1
        if safe_find(var, "./p:type/p:BOOL", ns) is not None:
            bool_outputs += 1
        if safe_find(var, "./p:type/p:INT", ns) is not None:
            int_outputs += 1

    for var in local_vars:
        local_names.append(var.attrib.get("name", ""))
        if safe_find(var, "./p:type/p:derived", ns) is not None:
            derived_local_vars += 1

    return {
        "n_inputs": len(input_vars),
        "n_outputs": len(output_vars),
        "n_local_vars": len(local_vars),
        "n_variables_total": len(input_vars) + len(output_vars) + len(local_vars),
        "n_bool_inputs": bool_inputs,
        "n_bool_outputs": bool_outputs,
        "n_int_inputs": int_inputs,
        "n_int_outputs": int_outputs,
        "n_physical_inputs": physical_inputs,
        "n_physical_outputs": physical_outputs,
        "n_derived_local_vars": derived_local_vars,
        "input_var_names": ";".join(sorted([x for x in input_names if x])),
        "output_var_names": ";".join(sorted([x for x in output_names if x])),
        "local_var_names": ";".join(sorted([x for x in local_names if x])),
    }


def extract_ld_features(root: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
    contacts = safe_findall(root, ".//p:contact", ns)
    coils = safe_findall(root, ".//p:coil", ns)
    blocks = safe_findall(root, ".//p:block", ns)
    in_vars = safe_findall(root, ".//p:inVariable", ns)
    out_vars = safe_findall(root, ".//p:outVariable", ns)

    block_types = [b.attrib.get("typeName", "") for b in blocks if b.attrib.get("typeName")]
    block_counter = Counter(block_types)

    out_exprs = []
    for ov in out_vars:
        expr = safe_find(ov, "./p:expression", ns)
        if expr is not None and expr.text:
            out_exprs.append(expr.text.strip())

    coil_vars = []
    for coil in coils:
        var_elem = safe_find(coil, "./p:variable", ns)
        if var_elem is not None and var_elem.text:
            coil_vars.append(var_elem.text.strip())

    all_written_outputs = out_exprs + coil_vars

    contact_vars = []
    for c in contacts:
        var_elem = safe_find(c, "./p:variable", ns)
        if var_elem is not None and var_elem.text:
            contact_vars.append(var_elem.text.strip())

    path_lengths = []
    for conn in safe_findall(root, ".//p:connection", ns):
        positions = safe_findall(conn, "./p:position", ns)
        path_lengths.append(len(positions))

    features = {
        "n_contacts": len(contacts),
        "n_contacts_negated": sum(parse_bool_like(c.attrib.get("negated")) for c in contacts),
        "n_coils": len(coils),
        "n_coils_negated": sum(parse_bool_like(c.attrib.get("negated")) for c in coils),
        "n_blocks": len(blocks),
        "n_inVariables": len(in_vars),
        "n_outVariables": len(out_vars),
        "n_unique_blocks": len(block_counter),
        "block_types": ";".join(f"{k}:{v}" for k, v in sorted(block_counter.items())),
        "has_custom_blocks": int(any(bt not in {
            "ADD", "SUB", "MUL", "DIV", "LT", "LE", "GT", "GE", "EQ", "NE",
            "TON", "TOF", "CTU", "CTD", "AND", "OR", "NOT", "MOVE", "SEL"
        } for bt in block_counter)),
        "n_outputs_written": len(set(all_written_outputs)),
        "outputs_multi_write": len(all_written_outputs) - len(set(all_written_outputs)),
        "written_output_names": ";".join(sorted(set(all_written_outputs))),
        "has_feedback_loop": int(len(set(contact_vars).intersection(set(all_written_outputs))) > 0),
        "logic_depth_approx": max(path_lengths) if path_lengths else 0,
    }

    for op in ["ADD", "SUB", "MUL", "DIV", "LT", "LE", "GT", "GE", "EQ", "NE", "TON", "TOF", "CTU", "CTD"]:
        features[f"block_{op.lower()}_count"] = block_counter.get(op, 0)

    return features


def extract_graph_like_stats(root: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
    local_ids = set()
    for elem in root.iter():
        if "localId" in elem.attrib:
            local_ids.add(elem.attrib["localId"])

    out_deg = Counter()
    in_deg = Counter()
    edge_list = []

    for elem in root.iter():
        src = elem.attrib.get("localId")
        for conn in elem.findall(".//" + q("connection", ns)):
            dst = conn.attrib.get("refLocalId")
            if src and dst:
                edge_list.append((src, dst))
                out_deg[src] += 1
                in_deg[dst] += 1

    if local_ids:
        degrees = [(out_deg.get(lid, 0) + in_deg.get(lid, 0)) for lid in local_ids]
        avg_degree = round(statistics.mean(degrees), 4) if degrees else 0.0
        max_degree = max(degrees) if degrees else 0
        fan_in_max = max(in_deg.values()) if in_deg else 0
        fan_out_max = max(out_deg.values()) if out_deg else 0
        n_isolated_nodes = sum(1 for lid in local_ids if (out_deg.get(lid, 0) + in_deg.get(lid, 0)) == 0)
    else:
        avg_degree = 0.0
        max_degree = 0
        fan_in_max = 0
        fan_out_max = 0
        n_isolated_nodes = 0

    return {
        "n_local_ids": len(local_ids),
        "n_connections": len(edge_list),
        "avg_degree": avg_degree,
        "max_degree": max_degree,
        "fan_in_max": fan_in_max,
        "fan_out_max": fan_out_max,
        "n_isolated_nodes": n_isolated_nodes,
        "n_left_power_rails": len(safe_findall(root, ".//p:leftPowerRail", ns)),
        "n_right_power_rails": len(safe_findall(root, ".//p:rightPowerRail", ns)),
    }


def extract_st_features(root: ET.Element, ns: Dict[str, str]) -> Dict[str, Any]:
    st_text = extract_st_text(root, ns)
    st_lower = st_text.lower()
    assigned_vars = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:=", st_text)

    return {
        "st_text_length": len(st_text),
        "n_if": count_regex(r"\bif\b", st_lower),
        "n_then": count_regex(r"\bthen\b", st_lower),
        "n_end_if": count_regex(r"\bend_if\b", st_lower),
        "n_while": count_regex(r"\bwhile\b", st_lower),
        "n_end_while": count_regex(r"\bend_while\b", st_lower),
        "n_assignments": st_text.count(":="),
        "n_comparisons": count_regex(r"(<=|>=|<>|=|<|>)", st_text),
        "n_constants": count_regex(r"\b\d+\b", st_text),
        "has_arithmetic": int(any(op in st_text for op in [" + ", " - ", " * ", " / "])),
        "has_threshold_logic": int(any(op in st_text for op in ["<=", ">=", "<", ">"])),
        "n_true_literals": count_regex(r"\btrue\b", st_lower),
        "n_false_literals": count_regex(r"\bfalse\b", st_lower),
        "has_loop_construct": int(count_regex(r"\bwhile\b", st_lower) > 0),
        "n_conditionals_total": count_regex(r"\bif\b", st_lower) + count_regex(r"\bwhile\b", st_lower),
        "n_unique_assigned_vars_st": len(set(assigned_vars)),
        "assigned_vars_st": ";".join(sorted(set(assigned_vars))),
    }


def reconstruct_il_like_sequence(root: ET.Element, ns: Dict[str, str]) -> str:
    instructions: List[str] = []

    for elem in root.iter():
        name = local_name(elem.tag)

        if name == "contact":
            var = safe_find(elem, "./p:variable", ns)
            operand = var.text.strip() if var is not None and var.text else "UNKNOWN"
            opcode = "LDN" if parse_bool_like(elem.attrib.get("negated")) else "LD"
            instructions.append(f"{opcode} {operand}")

        elif name == "coil":
            var = safe_find(elem, "./p:variable", ns)
            operand = var.text.strip() if var is not None and var.text else "UNKNOWN"
            opcode = "OUTN" if parse_bool_like(elem.attrib.get("negated")) else "OUT"
            instructions.append(f"{opcode} {operand}")

        elif name == "inVariable":
            expr = safe_find(elem, "./p:expression", ns)
            operand = expr.text.strip() if expr is not None and expr.text else "UNKNOWN"
            instructions.append(f"IN {operand}")

        elif name == "outVariable":
            expr = safe_find(elem, "./p:expression", ns)
            operand = expr.text.strip() if expr is not None and expr.text else "UNKNOWN"
            instructions.append(f"OUTVAR {operand}")

        elif name == "block":
            type_name = elem.attrib.get("typeName", "BLOCK")
            instance_name = elem.attrib.get("instanceName", "")
            head = type_name if not instance_name else f"{type_name}:{instance_name}"
            instructions.append(f"CALL {head}")

            for var in safe_findall(elem, "./p:inputVariables/p:variable", ns):
                fp = var.attrib.get("formalParameter", "")
                if fp:
                    instructions.append(f"ARG {fp}")

            for var in safe_findall(elem, "./p:outputVariables/p:variable", ns):
                fp = var.attrib.get("formalParameter", "")
                if fp:
                    instructions.append(f"RET {fp}")

    return "\n".join(instructions)


def extract_sequence_features(il_like_sequence: str) -> Dict[str, Any]:
    lines = [line.strip() for line in il_like_sequence.splitlines() if line.strip()]
    opcodes = []
    operands = []

    for line in lines:
        parts = line.split(maxsplit=1)
        opcodes.append(parts[0])
        if len(parts) > 1:
            operands.append(parts[1])

    opcode_counter = Counter(opcodes)

    return {
        "seq_n_lines": len(lines),
        "seq_n_unique_opcodes": len(opcode_counter),
        "seq_opcode_vocab": ";".join(f"{k}:{v}" for k, v in sorted(opcode_counter.items())),
        "seq_n_unique_operands": len(set(operands)),
        "seq_has_ld": int("LD" in opcode_counter),
        "seq_has_ldn": int("LDN" in opcode_counter),
        "seq_has_out": int("OUT" in opcode_counter),
        "seq_has_call": int("CALL" in opcode_counter),
    }


def infer_label_from_path(path: Path) -> str:
    lower = str(path).lower()
    if any(x in lower for x in ["mal", "llb", "attack", "anomal", "susp"]):
        return "suspicious"
    if any(x in lower for x in ["benign", "normal", "legit"]):
        return "benign"
    return ""


def extract_all_features(xml_path: Path, fixed_label: Optional[str] = None) -> Dict[str, Any]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = get_namespace(root)

    row: Dict[str, Any] = {
        "file_name": xml_path.name,
        "file_path": str(xml_path),
        "label": fixed_label if fixed_label is not None else infer_label_from_path(xml_path),
    }

    row.update(extract_structure_features(root, ns))
    row.update(extract_declared_variables(root, ns))
    row.update(extract_ld_features(root, ns))
    row.update(extract_graph_like_stats(root, ns))
    row.update(extract_st_features(root, ns))

    il_like_sequence = reconstruct_il_like_sequence(root, ns)
    row["il_like_sequence"] = il_like_sequence
    row.update(extract_sequence_features(il_like_sequence))

    return row


def find_xml_files(input_dir: Path, recursive: bool = False) -> List[Path]:
    pattern = "**/*.xml" if recursive else "*.xml"
    return sorted([p for p in input_dir.glob(pattern) if p.is_file()])


def write_csv(rows: List[Dict[str, Any]], output_path: Path) -> None:
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: List[Dict[str, Any]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def clean_and_transpose_csv_like_script(rows: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Aplica exatamente a mesma limpeza do script externo:
    - remove il_like_sequence e file_path;
    - usa file_name como índice;
    - transpõe o dataset;
    - salva o CSV final.
    """

    df = pd.DataFrame(rows)

    # Garante que existe file_name
    if "file_name" not in df.columns:
        raise ValueError("A coluna 'file_name' não foi encontrada no CSV.")

    # Coloca file_name como índice e transpõe
    df_t = df.set_index("file_name").T.reset_index()
    df_t = df_t.rename(columns={"index": "feature"})

    # Salva em CSV
    df_t.to_csv(output_path, index=False, encoding="utf-8-sig")

def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai features de arquivos PLCopen XML.")
    parser.add_argument("--input", required=True, help="Pasta contendo os XMLs.")
    parser.add_argument("--output", required=True, help="Arquivo CSV de saída.")
    parser.add_argument("--json-output", default=None, help="Arquivo JSON opcional.")
    parser.add_argument("--recursive", action="store_true", help="Busca XML recursivamente.")
    parser.add_argument("--label", default=None, help="Rótulo fixo, ex.: benign ou suspicious.")
    parser.add_argument("--pretty", action="store_true", help="Imprime resumo")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Pasta inválida: {input_dir}", file=sys.stderr)
        return 1

    xml_files = find_xml_files(input_dir, recursive=args.recursive)
    if not xml_files:
        print(f"Nenhum XML encontrado em {input_dir}", file=sys.stderr)
        return 1

    rows: List[Dict[str, Any]] = []
    failures: List[Tuple[str, str]] = []

    for xml_file in xml_files:
        try:
            rows.append(extract_all_features(xml_file, fixed_label=args.label))
        except Exception as e:
            failures.append((str(xml_file), str(e)))

    if not rows:
        print("Nenhum XML foi processado com sucesso.", file=sys.stderr)
        return 1

    output_csv = Path(args.output)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_and_transpose_csv_like_script(rows, output_csv)

    if args.json_output:
        output_json = Path(args.json_output)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        write_json(rows, output_json)

    if args.pretty:
        print(f"Arquivos processados: {len(rows)}")
        print(f"Falhas: {len(failures)}")
        print(f"CSV: {output_csv}")
        if args.json_output:
            print(f"JSON: {args.json_output}")
        sample = rows[0].copy()
        seq = sample.pop("il_like_sequence", "")
        print("\nExemplo do primeiro arquivo:")
        for k in sorted(sample.keys()):
            print(f"  {k}: {sample[k]}")
        if seq:
            print("\nPrimeiras linhas da sequência IL-like:")
            for line in seq.splitlines()[:12]:
                print(f"  {line}")

    if failures:
        print("\nArquivos com erro:", file=sys.stderr)
        for fpath, err in failures:
            print(f"- {fpath}: {err}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
