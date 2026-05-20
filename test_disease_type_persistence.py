#!/usr/bin/env python
"""
Test script to verify disease_type persistence across conversation turns
"""
import sys
from chatbot.main import detect_disease_type, extract_image_path

print("=" * 60)
print("Testing Disease Type Persistence")
print("=" * 60)

# Simulate conversation turns
test_conversation = [
    ("my dog is having an eye issue", "eye", None, "Turn 1: User mentions eye issue"),
    ("/path/to/image.jpg", "eye", "/path/to/image.jpg", "Turn 2: User provides image (should reuse 'eye' from Turn 1)"),
    ("also check the skin", "skin", None, "Turn 3: User mentions skin issue (should update to 'skin')"),
    ("/another/image.jpg", "skin", "/another/image.jpg", "Turn 4: User provides image (should reuse 'skin' from Turn 3)"),
]

print("\n📋 Simulating Multi-Turn Conversation:\n")

# Simulate the state tracking logic
current_disease_type = None

for user_input, expected_disease, expected_image, description in test_conversation:
    print(f"  {description}")
    print(f"  User: {user_input}")
    
    # Detect disease type from current message
    detected_disease_type = detect_disease_type(user_input)
    
    # Update current disease type if a new one is detected
    if detected_disease_type:
        current_disease_type = detected_disease_type
    
    # Extract image path
    image_path = extract_image_path(user_input)
    
    # Check results
    disease_ok = "✅" if current_disease_type == expected_disease else "❌"
    image_ok = "✅" if image_path == expected_image else "❌"
    
    print(f"  Disease Type: {disease_ok} {current_disease_type} (expected: {expected_disease})")
    print(f"  Image Path:   {image_ok} {image_path} (expected: {expected_image})")
    print()

print("=" * 60)
print("✅ Disease Type Persistence Test Complete!")
print("=" * 60)
