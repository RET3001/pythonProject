import xml.etree.ElementTree as ElementTree
import json
import os

def ensure_output_dir():
    os.makedirs('out', exist_ok=True)

def parse_xmi(input_file):
    tree = ElementTree.parse(input_file)
    root = tree.getroot()

    classes = {}
    aggregations = []

    for elem in root:
        if elem.tag == "Class":
            class_name = elem.attrib["name"]
            is_root = elem.attrib["isRoot"] == "true"
            documentation = elem.attrib.get("documentation", "")

            attributes = []
            for attr in elem.findall("Attribute"):
                attributes.append({
                    "name": attr.attrib["name"],
                    "type": attr.attrib["type"]
                })

            classes[class_name] = {
                "name": class_name,
                "isRoot": is_root,
                "documentation": documentation,
                "attributes": attributes,
                "children": []
            }

        elif elem.tag == "Aggregation":
            aggregations.append({
                "source": elem.attrib["source"],
                "target": elem.attrib["target"],
                "sourceMultiplicity": elem.attrib["sourceMultiplicity"],
                "targetMultiplicity": elem.attrib["targetMultiplicity"]
            })

    for agg in aggregations:
        source = agg["source"]
        target = agg["target"]

        if target in classes:
            classes[target]["children"].append({
                "class": source,
                "min": agg["targetMultiplicity"].split("..")[0],
                "max": agg["targetMultiplicity"].split("..")[-1]
            })

    return classes


def generate_config(classes):
    root_class = next((c for c in classes.values() if c["isRoot"]), None)

    def build_xml_element(class_info):
        elem = ElementTree.Element(class_info["name"])

        for attr in class_info["attributes"]:
            attr_elem = ElementTree.SubElement(elem, attr["name"])
            attr_elem.text = attr["type"]

        for child in class_info["children"]:
            child_class = classes[child["class"]]
            child_elem = build_xml_element(child_class)
            elem.append(child_elem)

        return elem

    if root_class:
        root_elem = build_xml_element(root_class)
        return ElementTree.tostring(root_elem, encoding="unicode")
    return ""


def generate_meta(classes):
    meta = []

    for class_name, class_info in classes.items():
        entry = {
            "class": class_name,
            "documentation": class_info["documentation"],
            "isRoot": class_info["isRoot"],
            "parameters": []
        }

        for attr in class_info["attributes"]:
            entry["parameters"].append({
                "name": attr["name"],
                "type": attr["type"]
            })

        for child in class_info["children"]:
            child_class = child["class"]
            entry["parameters"].append({
                "name": child_class,
                "type": "class"
            })

            child_entry = next((e for e in meta if e["class"] == child_class), None)
            if child_entry:
                child_entry["min"] = child["min"]
                child_entry["max"] = child["max"]

        meta.append(entry)

    for entry in meta:
        if "min" not in entry:
            entry["min"] = "1"
            entry["max"] = "1"

    ordered_meta = []
    processed = set()

    def add_class(class_name):
        if class_name in processed:
            return
        class_info = classes[class_name]

        for child in class_info["children"]:
            add_class(child["class"])

        entry = next(e for e in meta if e["class"] == class_name)
        ordered_meta.append(entry)
        processed.add(class_name)

    for class_name in classes:
        if not classes[class_name]["isRoot"]:
            add_class(class_name)

    root_class = next(c for c in classes.values() if c["isRoot"])
    add_class(root_class["name"])

    return json.dumps(ordered_meta, indent=4)


def main():
    input_file = "input/test_input.xml"
    classes = parse_xmi(input_file)

    ensure_output_dir()

    config_xml = generate_config(classes)
    with open("out/config.xml", "w", encoding='utf-8') as f:
        f.write(config_xml)

    meta_json = generate_meta(classes)
    with open("out/meta.json", "w", encoding='utf-8') as f:
        f.write(meta_json)

if __name__ == "__main__":
    main()
