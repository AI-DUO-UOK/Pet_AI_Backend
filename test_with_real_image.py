#!/usr/bin/env python
"""
Test complete workflow with actual image file from sample_images
"""
import os
from pathlib import Path

# Get an actual test image
sample_images = list(Path("/Users/akilafernando/Documents/GitHub/Pet_AI_Backend/sample_images").glob("*.jpg"))

if not sample_images:
    print("❌ No sample images found")
    exit(1)

test_image_path = str(sample_images[0])
print(f"📸 Using test image: {os.path.basename(test_image_path)}")

from chatbot.main import detect_disease_type, extract_image_path

# Simulate multi-turn conversation
print("\n" + "=" * 70)
print("Simulating Complete Chatbot Workflow")
print("=" * 70)

current_disease_type = None

conversation_turns = [
    ("My dog has an eye problem", "Should detect 'eye'"),
    (f"{test_image_path}", "Should keep 'eye' and extract image path"),
]

for turn, (user_input, expected_behavior) in enumerate(conversation_turns, 1):
    print(f"\n📝 Turn {turn}: {expected_behavior}")
    print(f"   User Input: {user_input[:60]}{'...' if len(user_input) > 60 else ''}")
    
    # Detect disease type
    detected = detect_disease_type(user_input)
    if detected:
        current_disease_type = detected
    
    # Extract image path
    image_path = extract_image_path(user_input)
    
    print(f"   → Disease Type: {current_disease_type}")
    print(f"   → Image Path: {image_path if image_path else 'None'}")
    
    if turn == 1:
        expected_disease = "eye"
        expected_image = None
    else:
        expected_disease = "eye"
        expected_image = test_image_path
    
    disease_ok = current_disease_type == expected_disease
    image_ok = image_path == expected_image
    
    if disease_ok and image_ok:
        print(f"   ✅ PASS")
    else:
        print(f"   ❌ FAIL")
        if not disease_ok:
            print(f"      Expected disease_type={expected_disease}, got {current_disease_type}")
        if not image_ok:
            print(f"      Expected image={expected_image}, got {image_path}")

print("\n" + "=" * 70)
print("✅ Workflow simulation complete!")
print("=" * 70)
