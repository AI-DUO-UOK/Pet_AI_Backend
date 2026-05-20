# Pet AI Healthcare System

An intelligent AI-powered veterinary assistant that combines large language models with computer vision to diagnose pet health issues. Ask about your pet's health concerns via a chatbot interface, and for skin/eye issues, upload images for AI-powered diagnosis.

## Features

- 🐾 **Smart Chatbot** - LangChain-based conversational AI using LLaMA 3.1 8B
- 🔬 **Computer Vision** - PyTorch models for disease detection:
  - Dog skin disease detection
  - Dog eye disease detection
  - Cat skin disease detection
- 🎯 **Intelligent Routing** - Automatically detects:
  - **Skin issues** → Asks for image → Analyzes using CV model
  - **Eye issues** → Asks for image → Analyzes using CV model
  - **General health** → Answers directly from LLM
- 💬 **Conversation Memory** - Maintains context across multi-turn conversations
- ⚡ **FastAPI Backend** - High-performance image analysis API
- 🛡️ **Error Handling** - Graceful error recovery and user guidance

## Architecture

### Components

```
Frontend (CLI) → Chatbot (LangChain) → LLM (OpenRouter)
                       ↓
                  Intent Detector
                    ↙       ↘
            Image Analysis    Direct Answer
                ↓
            Tool Call
                ↓
            FastAPI /analyze-image
                ↓
            CV Models (PyTorch)
                ↓
            Disease Prediction
```

### Project Structure

```
Pet_AI_Backend/
├── app/                           # FastAPI Computer Vision Backend
│   ├── main.py                   # FastAPI endpoints (/predict, /analyze-image)
│   ├── config.py                 # Model paths and device config
│   ├── models/                   # PyTorch model loaders
│   │   ├── dog_skin.py
│   │   ├── dog_eye.py
│   │   └── cat_skin.py
│   ├── services/
│   │   ├── router.py            # Route to correct model
│   │   └── predictor.py         # Run inference
│   └── utils/
│       └── image.py             # Image preprocessing
│
├── chatbot/                      # LangChain Chatbot System
│   ├── main.py                  # CLI entry point
│   ├── agent.py                 # LangChain agent with tools
│   ├── llm.py                   # OpenRouter LLaMA configuration
│   ├── tools.py                 # Tool to call /analyze-image endpoint
│   ├── memory.py                # Conversation memory
│   └── prompts.py               # System prompts
│
├── weights/                      # PyTorch model weights (ignored in git)
│   ├── dog_skin_model.pth
│   ├── dog_eye_model_ResNet_NEW.pth
│   └── cat_skin_model.pth
│
├── requirements.txt              # Python dependencies
├── .env                         # API keys (create this)
│
└── docs/                        # Documentation
    ├── FIXES_SUMMARY.md        # What was wrong and how it was fixed
    ├── SETUP_TESTING_GUIDE.md  # Setup and testing instructions
    └── INTEGRATION_REPORT.md   # Complete integration analysis
```

## Quick Start

### Prerequisites
- Python 3.8+
- OpenRouter API key
- Model weights files

### Installation

```bash
# Clone repository
cd Pet_AI_Backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE" > .env
```

### Running the System

```bash
# Terminal 1: Start FastAPI server
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Start chatbot
python -m chatbot.main
```

## Usage Examples

### Example 1: General Health Question

```
You: What type of pet do you have? (dog/cat): dog

You: My dog is limping. What could be wrong?

Bot: Limping can be caused by several issues...
     [Provides direct veterinary advice without using image]
```

### Example 2: Skin Disease Detection

```
You: What type of pet do you have? (dog/cat): dog

You: My dog has a scaly rash on his belly

Bot: Could you please upload an image of your dog's skin?

You: /Users/me/Pictures/dog_rash.jpg

Bot: [Analyzes image using CV model]
     
     This appears to be Dermatitis (confidence: 89%)
     
     Dermatitis is inflammation of the skin that can be caused by:
     - Allergies
     - Parasites
     - Bacterial or fungal infections
     
     Treatment options include:
     - Medicated baths
     - Anti-inflammatory medication
     - Addressing the underlying cause
     
     I recommend scheduling a vet visit soon for proper diagnosis and treatment.
```

### Example 3: Eye Disease Detection

```
You: My cat's eye is red and swollen

Bot: Could you please upload an image of your cat's eye?

You: ~/Documents/cat_eye.jpg

Bot: [Analyzes image]
     
     This appears to be Keratitis (confidence: 85%)
     
     Keratitis is inflammation of the cornea. 
     This requires prompt veterinary attention...
```

## API Endpoints

### FastAPI Endpoints

#### `/predict` (POST)
Used by external clients for image analysis.

**Parameters:**
- `file`: Image file (multipart)
- `animal`: "dog" or "cat"
- `disease_type`: "skin" or "eye"

**Response:**
```json
{
  "class": "ringworm",
  "confidence": 0.92
}
```

#### `/analyze-image` (POST)
Used by chatbot for image analysis.

**Parameters:**
- `file`: Image file (multipart)
- `disease_type`: "skin" or "eye"
- `animal`: "dog" or "cat" (default: "dog")
- `user_id`: User identifier (default: "demo")

**Response:**
```json
{
  "class": "Fungal_infections",
  "confidence": 0.87
}
```

## Supported Conditions

### Dog Skin Diseases
- Dermatitis
- Fungal infections
- Ringworm
- Demodicosis
- Hypersensitivity
- (Healthy)

### Dog Eye Diseases
- Pigmented keratitis
- Blepharitis
- Entropion
- Eyelid tumor
- Mastopathy

### Cat Skin Diseases
- Flea allergy
- Ringworm
- Scabies
- (Healthy)

## Configuration

### Environment Variables (`.env`)
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Model Configuration (`app/config.py`)
Paths to PyTorch model weights:
- `DOG_SKIN_MODEL`: weights/dog_skin_model.pth
- `DOG_EYE_MODEL`: weights/dog_eye_model_ResNet_NEW.pth
- `CAT_SKIN_MODEL`: weights/cat_skin_model.pth

Device: Automatically uses CUDA if available, falls back to CPU.

## System Design Highlights

### Intent Detection
- 30+ disease-related keywords for skin issues
- 12+ disease-related keywords for eye issues
- Automatic routing to appropriate handler

### Image Analysis Workflow
1. User describes symptom (e.g., "rash")
2. System detects it's a skin/eye issue
3. System asks for image
4. User provides image path
5. Tool calls FastAPI `/analyze-image`
6. FastAPI uses PyTorch model for inference
7. LLM explains the diagnosis

### General Health Workflow
1. User asks general question
2. System detects it's not skin/eye specific
3. LLM answers directly
4. No image required, no tool call

## Documentation

- **[FIXES_SUMMARY.md](FIXES_SUMMARY.md)** - Detailed analysis of all issues and fixes (10 critical problems solved)
- **[SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md)** - Complete setup instructions, testing scenarios, and troubleshooting
- **[INTEGRATION_REPORT.md](INTEGRATION_REPORT.md)** - Comprehensive integration analysis and architecture

## Key Technologies

- **LangChain** - Agentic framework for LLM orchestration
- **OpenRouter API** - LLaMA 3.1 8B via OpenRouter
- **FastAPI** - High-performance web framework
- **PyTorch** - Deep learning framework
- **ResNet-50** - Backbone for disease detection models

## Recent Fixes

✅ **10 Critical Issues Resolved:**
1. Endpoint routing fixed
2. Tool parameters properly passed
3. JSON response handling corrected
4. Intent detection implemented
5. Image path extraction added
6. LLM configuration enhanced
7. Memory integration fixed
8. Error handling comprehensive
9. Dependencies completed
10. Chatbot workflow implemented

See [FIXES_SUMMARY.md](FIXES_SUMMARY.md) for detailed information.

## Performance Notes

- First inference: ~10-15 seconds (model warmup)
- Subsequent inferences: ~2-3 seconds
- Recommended GPU: 4GB+ VRAM
- CPU mode: Supported but slower

## Future Enhancements

- [ ] RAG integration for medical knowledge base
- [ ] Web UI for image uploads
- [ ] Database for diagnosis history
- [ ] Multi-pet tracking
- [ ] Confidence thresholds and expert review
- [ ] Professional vet consultation booking
- [ ] Mobile app
- [ ] Breed-specific models

## Troubleshooting

### Common Issues

**"API key not found"**
```bash
# Create .env file
echo "OPENROUTER_API_KEY=your_key" > .env
```

**"Connection refused on 127.0.0.1:8000"**
```bash
# Verify FastAPI is running
python -m uvicorn app.main:app --reload --port 8000
```

**"Tool is not being called"**
- Check your question contains skin/eye-related keywords
- Try: "My dog has ringworm" instead of "My dog is sick"

**"Image not found"**
- Use absolute paths: `/Users/username/image.jpg`
- Ensure file exists: `ls -l /path/to/image.jpg`

See [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md) for more troubleshooting.

## Contributing

Contributions welcome! Areas for improvement:
- Additional disease detection models
- Extended conversation abilities
- Better error messages
- Performance optimization

## License

[Specify your license here]

## Contact

For questions or issues, please open an issue on GitHub.

---

**Status:** ✅ Fully Integrated and Ready for Testing

Last Updated: May 1, 2026

