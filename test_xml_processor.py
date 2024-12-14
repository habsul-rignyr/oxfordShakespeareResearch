from xml.etree import ElementTree as ET
from processors.xml_processor import XMLProcessor  # Adjust import based on your file structure

# Initialize the processor
processor = XMLProcessor()

# Load the XML file
tree = ET.parse('/Volumes/seagate_portable/eebo-tcp-texts/tcp/A35231.xml')  # Replace with the path to your XML file
root = tree.getroot()

# Debug: Print the root tag
print(f"Root tag: {root.tag}")

# Locate the target div to process
# Adjust the XPath to match the structure of your XML file
div = root.find('.//tei:div', processor.namespaces)

if div is None:
    print("No <div> element found!")
else:
    print(f"Processing div with tag: {div.tag}")

    # Process prose content within the located div
    prose_content = processor.process_prose_div(div)

    # Output results
    for part_type, text in prose_content:
        print(f"{part_type}: {text}")
