# HR & Recruitment Chatbot Prototype

A fully functional HR & Recruitment Chatbot web prototype built with Python (Flask) and SQLite, following strict Object-Oriented Programming (OOP) principles.

## Features
- **Dual Mode**: Switch between **Candidate** and **Employee** modes to see role-specific responses.
- **Intent Classification**: Rule-based NLP using TF-IDF style keyword matching.
- **Rich Responses**: Supports text, cards (for job listings), and quick-reply buttons.
- **Premium UI**: Teal-themed modern interface with:
    - Glassmorphism effects.
    - Light/Dark mode toggle.
    - Typing indicators.
    - Fully mobile responsive design (375px+).
- **SQLite Database**: Pre-seeded with job listings, applications, and HR policies.

## OOP Architecture
- `HRChatBot`: Main controller orchestrating the components.
- `NLUProcessor` (Abstract Base) → `IntentClassifier`, `EntityExtractor`.
- `ResponseGenerator`: Polymorphic methods for different UI response types.
- `Person` (Abstract Base) → `Candidate`, `Employee` (using private fields and encapsulation).
- `DialogManager`: Tracks session state and active mode.
- `HRDatabase`: Interface for data persistence and queries.

## Setup & Run

### Prerequisites
- Python 3.10+

### Installation
1. Navigate to the project directory:
   ```bash
   cd hr-chatbot
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install flask
   ```
3. Initialize the database (if not already done):
   ```bash
   python3 seed_db.py
   ```

### Running the App
1. Start the Flask server:
   ```bash
   python3 app.py
   ```
2. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

## Pre-seeded Data
- **Job Listings**: 10 sample roles (Software Engineer, HR Specialist, etc.)
- **Applications**: 5 samples. Check status by typing "check status of 1" (ID range 1-5).
- **FAQs**: Coverage for leave policy, joining documents, and more.
