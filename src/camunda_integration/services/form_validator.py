
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"
BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS = {"bpmn": BPMN_NS, "camunda": CAMUNDA_NS}


@dataclass
class FormField:
    id: str
    label: Optional[str]
    type: str
    required: bool = False
    minlength: Optional[int] = None
    maxlength: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[str]] = None


def _parse_form_fields_from_start_event(bpmn_path: Path) -> List[FormField]:
    tree = ET.parse(bpmn_path)
    root = tree.getroot()
    start = root.find(".//bpmn:startEvent", NS)
    if start is None:
        return []
    ext = start.find("bpmn:extensionElements", NS)
    if ext is None:
        return []
    form_data = ext.find("camunda:formData", NS)
    if form_data is None:
        return []
    fields: List[FormField] = []
    for ff in form_data.findall("camunda:formField", NS):
        fid = ff.get("id")
        label = ff.get("label")
        ftype = ff.get("type", "string")
        required = False
        minlength = maxlength = None
        pattern = None
        enum_vals: Optional[List[str]] = None
        # validations
        val = ff.find("camunda:validation", NS)
        if val is not None:
            for c in val.findall("camunda:constraint", NS):
                name = c.get("name")
                if name == "required":
                    required = True
                elif name == "minlength":
                    try:
                        minlength = int(c.get("config"))
                    except Exception:
                        pass
                elif name == "maxlength":
                    try:
                        maxlength = int(c.get("config"))
                    except Exception:
                        pass
                elif name == "pattern":
                    pattern = c.get("config")
        # enum
        enum_elems = ff.findall("camunda:value", NS)
        if enum_elems:
            enum_vals = [e.get("id") or e.get("name") or e.get("value") for e in enum_elems]
            enum_vals = [x for x in enum_vals if x]
        fields.append(
            FormField(
                id=fid or "",
                label=label,
                type=ftype,
                required=required,
                minlength=minlength,
                maxlength=maxlength,
                pattern=pattern,
                enum_values=enum_vals,
            )
        )
    return fields


def load_required_fields_from_bpmn(bpmn_path: Path) -> List[Dict[str, Any]]:
    fields = _parse_form_fields_from_start_event(bpmn_path)
    result: List[Dict[str, Any]] = []
    for f in fields:
        entry = {
            "id": f.id,
            "label": f.label,
            "type": f.type,
            "required": f.required,
            "minlength": f.minlength,
            "maxlength": f.maxlength,
            "pattern": f.pattern,
            "enum": f.enum_values,
        }
        result.append(entry)
    return result


def validate_start_variables(bpmn_path: Path, variables: Dict[str, Any]) -> Tuple[bool, str, List[Dict[str, Any]]]:
    fields = _parse_form_fields_from_start_event(bpmn_path)
    missing: List[Dict[str, Any]] = []
    msgs: List[str] = []

    for f in fields:
        val = variables.get(f.id)
        # required
        if f.required and (val is None or (isinstance(val, str) and val.strip() == "")):
            missing.append({"id": f.id, "label": f.label or f.id, "reason": "required"})
            continue
        if val is None:
            continue
        # minlength/maxlength for strings
        if isinstance(val, str):
            if f.minlength is not None and len(val) < f.minlength:
                msgs.append(f"{f.label or f.id} must be at least {f.minlength} characters")
            if f.maxlength is not None and len(val) > f.maxlength:
                msgs.append(f"{f.label or f.id} must be at most {f.maxlength} characters")
            if f.pattern is not None:
                try:
                    if re.fullmatch(f.pattern, val) is None:
                        msgs.append(f"{f.label or f.id} does not match pattern {f.pattern}")
                except re.error:
                    msgs.append(f"Invalid pattern for {f.label or f.id}")
        # enum
        if f.enum_values is not None and val is not None:
            if str(val) not in [str(x) for x in f.enum_values]:
                msgs.append(f"{f.label or f.id} must be one of {f.enum_values}")

    ok = len(missing) == 0 and len(msgs) == 0
    message = "; ".join(msgs) if msgs else ("OK" if ok else "Missing required fields")
    return ok, message, missing
