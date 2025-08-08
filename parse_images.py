import cv2
import pytesseract
import numpy as np
import json
from collections import defaultdict

# Helper function to detect dominant color in a region
def get_dominant_color(image, x, y, w, h):
    roi = image[y:y+h, x:x+w]
    # Convert to HSV for better color clustering
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Calculate histogram and find dominant color
    hist = cv2.calcHist([hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
    dominant_h, dominant_s = np.unravel_index(hist.argmax(), hist.shape)
    # Map to approximate color name (simplified)
    if 0 <= dominant_h < 30:  # Red hues
        return "Red"
    elif 30 <= dominant_h < 60:  # Green hues
        return "Green"
    elif 60 <= dominant_h < 120:  # Blue hues
        return "Blue"
    return "Unknown"

# Load and preprocess image
image = cv2.imread("diagram.png")
if image is None:
    raise ValueError("Failed to load image")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)

# Detect shapes (rectangles for participants/boxes, lines for arrows)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
participants = []
arrows = []
legend = {}

# Segment legend (assume it's in a corner, e.g., bottom-right)
legend_region = image[int(image.shape[0]*0.8):, int(image.shape[1]*0.8):]
legend_text = pytesseract.image_to_string(legend_region, config='--psm 6').strip()
# Simplified legend parsing: map colors to roles (e.g., "Blue: System", "Green: Database")
for line in legend_text.split('\n'):
    if ':' in line:
        color, role = line.split(':', 1)
        legend[color.strip().capitalize()] = role.strip()

# Detect participants and arrows
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    if w > 50 and h < 50:  # Heuristic for participant rectangles
        color = get_dominant_color(image, x, y, w, h)
        participants.append({"x": x, "y": y, "w": w, "h": h, "color": color})
    elif w > 10 and h > 10:  # Heuristic for arrows or lines
        arrows.append({"x": x, "y": y, "w": w, "h": h})

# Extract text and assign to participants
for participant in participants:
    roi = image[participant["y"]:participant["y"]+participant["h"], participant["x"]:participant["x"]+participant["w"]]
    text = pytesseract.image_to_string(roi, config='--psm 6').strip()
    participant["name"] = text
    # Assign group based on color and legend
    participant["group"] = legend.get(participant["color"], "Unknown")

# Sort participants by x-coordinate for left-to-right ordering
participants.sort(key=lambda p: p["x"])

# Analyze arrows and extract steps
steps = []
for i, arrow in enumerate(arrows):
    # Extract text near arrow
    roi = image[arrow["y"]-10:arrow["y"]+arrow["h"]+10, arrow["x"]-10:arrow["x"]+arrow["w"]+10]
    message = pytesseract.image_to_string(roi, config='--psm 6').strip()
    
    # Determine direction (left-to-right if ambiguous)
    source = min(participants, key=lambda p: abs(p["x"] - arrow["x"]))
    target = min(participants, key=lambda p: abs(p["x"] - (arrow["x"] + arrow["w"])))
    
    # Check for arrowhead (simplified: assume wider end is target)
    direction = "->"
    if arrow["x"] > arrow["x"] + arrow["w"]:  # If arrow points left
        direction = "<--"
        source, target = target, source  # Swap for leftward flow
    elif arrow["x"] == arrow["x"] + arrow["w"]:  # Ambiguous direction
        # Default to left-to-right
        if source["x"] > target["x"]:
            source, target = target, source
            direction = "->"
    
    steps.append({
        "step": i + 1,
        "source": source["name"],
        "target": target["name"],
        "direction": direction,
        "message": message,
        "source_group": source["group"],
        "target_group": target["group"]
    })

# Sort steps by y-coordinate (time flows downward in sequence diagrams)
steps.sort(key=lambda s: arrows[s["step"]-1]["y"])

# Output structured steps
with open("parsed_diagram.json", "w") as f:
    json.dump(steps, f, indent=2)

# Generate Mermaid output
mermaid_output = "sequenceDiagram\n"
for step in steps:
    mermaid_output += f"    {step['source']}{step['direction']}{step['target']}: {step['message']}\n"
    if step["source_group"] != "Unknown":
        mermaid_output += f"    Note over {step['source']}: Group: {step['source_group']}\n"
    if step["target_group"] != "Unknown":
        mermaid_output += f"    Note over {step['target']}: Group: {step['target_group']}\n"

with open("parsed_diagram.mmd", "w") as f:
    f.write(mermaid_output)

print("Parsed steps saved to parsed_diagram.json")
print("Mermaid output saved to parsed_diagram.mmd")
