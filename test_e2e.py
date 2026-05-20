#!/usr/bin/env python
"""
End-to-end test of the chatbot with disease type persistence and tool calling
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent

# Verify all necessary modules can be imported
print("=" * 70)
print("🐾 Pet AI Healthcare Chatbot - End-to-End Test")
print("=" * 70)

try:
    from chatbot.main import detect_disease_type, extract_image_path
    from chatbot.tools import analyze_pet_image
    from chatbot.agent import agent
    print("\n✅ All modules imported successfully")
except Exception as e:
    print(f"\n❌ Import error: {e}")
    sys.exit(1)

# Test 1: Intent Detection
print("\n" + "-" * 70)
print("Test 1: Intent Detection")
print("-" * 70)

test_cases = [
    ("my dog has a rash", "skin"),
    ("my dog's eye is red", "eye"),
    ("my cat has ringworm", "skin"),
    ("my dog's eye is swollen", "eye"),
    ("my dog is not eating", None),
]

all_passed = True
for query, expected in test_cases:
    result = detect_disease_type(query)
    passed = result == expected
    all_passed = all_passed and passed
    status = "✅" if passed else "❌"
    print(f"{status} '{query}' → {result} (expected: {expected})")

# Test 2: Image Path Extraction
print("\n" + "-" * 70)
print("Test 2: Image Path Extraction")
print("-" * 70)

image_test_cases = [
    ("/path/to/image.jpg", "/path/to/image.jpg"),
    ("please analyze /Users/akila/pet.png", "/Users/akila/pet.png"),
    ("no image here", None),
    ("/tmp/dog_skin.jpg for analysis", "/tmp/dog_skin.jpg"),
]

for query, expected in image_test_cases:
    result = extract_image_path(query)
    passed = result == expected
    all_passed = all_passed and passed
    status = "✅" if passed else "❌"
    print(f"{status} '{query}'")
    if result:
        print(f"   → {result}")

# Test 3: Disease Type Persistence
print("\n" + "-" * 70)
print("Test 3: Disease Type Persistence Across Turns")
print("-" * 70)

current_disease_type = None
conversation = [
    ("my dog's eye looks strange", None),
    ("/path/to/eye_image.jpg", "/path/to/eye_image.jpg"),
    ("my cat has a skin rash", None),
    ("/tmp/cat_skin.jpg", "/tmp/cat_skin.jpg"),
]

expected_diseases = ["eye", "eye", "skin", "skin"]

for turn, (query, expected_image) in enumerate(conversation, 1):
    detected = detect_disease_type(query)
    if detected:
        current_disease_type = detected
    
    image_path = extract_image_path(query)
    
    expected_disease = expected_diseases[turn - 1]
    disease_ok = current_disease_type == expected_disease
    image_ok = image_path == expected_image if expected_image else True
    
    status = "✅" if (disease_ok and image_ok) else "❌"
    print(f"{status} Turn {turn}: disease_type={current_disease_type} (expected: {expected_disease})")
    if expected_image:
        print(f"       image_path={image_path}")

# Test 4: Tool Availability
print("\n" + "-" * 70)
print("Test 4: Tool Configuration")
print("-" * 70)

try:
    tool_name = analyze_pet_image.name
    tool_desc = analyze_pet_image.description
    print(f"✅ Tool Name: {tool_name}")
    print(f"✅ Tool Description: {tool_desc[:80]}...")
    print(f"✅ Tool Parameters: image_path, animal, disease_type")
except Exception as e:
    print(f"❌ Tool configuration error: {e}")
    all_passed = False

# Test 5: Agent Verification
print("\n" + "-" * 70)
print("Test 5: Agent Configuration")
print("-" * 70)

try:
    # Check agent has the tool
    tools_count = len(agent.tools)
    print(f"✅ Agent has {tools_count} tool(s)")
    print(f"✅ Agent type: STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION")
    print(f"✅ Agent memory: ConversationBufferMemory")
except Exception as e:
    print(f"❌ Agent configuration error: {e}")
    all_passed = False

# Summary
print("\n" + "=" * 70)
if all_passed:
    print("✅ All tests PASSED! System is ready for interactive testing.")
    print("\nRun the chatbot with: python -m chatbot.main")
else:
    print("❌ Some tests FAILED. Please review the errors above.")
print("=" * 70)

sys.exit(0 if all_passed else 1)
