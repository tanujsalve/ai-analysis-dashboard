# Unified Flask + Firebase + AI Dashboard System

This is a complete Flask web application that integrates Firebase authentication with an AI-powered data analysis dashboard for college data.

## Features

### 🔐 Firebase Authentication
- User registration and login
- Secure session management
- User dashboard with profile management

### 🤖 AI-Powered Data Analysis
- Natural language queries about college data
- Interactive chat interface
- Dynamic SQL query generation
- Real-time data visualization
- College database analysis (students, courses, faculty, enrollment)

### 📊 Data Visualization
- Bar charts, pie charts, line graphs
- Interactive Chart.js visualizations
- Real-time data exploration
- Statistical analysis and insights

## Project Structure

```
├── app.py                          # Main Flask application (unified)
├── ai_agent.py                     # AI Agent for natural language processing
├── entity_extractor.py             # Extracts entities from user queries
├── query_builder.py                # Builds SQL queries dynamically
├── visualization_builder.py        # Creates data visualizations
├── intent_detector.py              # Detects user intent from queries
├── college.db                      # SQLite database with college data
├── templates/
│   └── ai_dashboard.html           # AI Dashboard interface
├── user_dashboard.html             # User dashboard page
├── login.html                      # Login page
├── register.html                   # Registration page
├── index.html                      # Main landing page
├── style.css                       # Styling
├── firebase-config.js              # Firebase configuration
├── firebase-config.json            # Firebase service account
├── requirements.txt                # Python dependencies
└── venv/                          # Virtual environment
```

## Database Schema

The `college.db` SQLite database contains:

- **students**: Student information (ID, name, branch, CGPA, admission year, etc.)
- **courses**: Course details (ID, name, branch, credits, semester, type)
- **faculty**: Faculty information (ID, name, branch, designation, experience)
- **enrollment**: Student-course enrollment data (enrollment ID, student ID, course ID, grade, attendance)

## Installation & Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate.bat  # Windows
# or
source venv/bin/activate   # Linux/Mac
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Firebase Configuration
- Ensure `firebase-config.json` is present with your Firebase service account credentials
- Update `firebase-config.js` with your Firebase project configuration

### 4. Environment Variables
Create a `.env` file with:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

## Running the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Available Routes

### Main Routes
- `/` - Landing page
- `/login` - Login page
- `/register` - Registration page
- `/user_dashboard` - User dashboard
- `/ai_dashboard` - AI-powered data analysis dashboard

### API Endpoints
- `/api/ai/query` - AI chat queries (POST)
- `/api/ai/visualize` - Data visualization requests (POST)
- `/register` - User registration (POST)
- `/upload` - File upload (POST)
- `/analyze` - Data analysis (POST)

## Usage

### 1. User Authentication
- Register a new account or login with existing credentials
- Access the user dashboard for profile management

### 2. AI Dashboard
- Click "AI Dashboard" in the user dashboard navigation
- Ask natural language questions about the college data:
  - "How many students are in Computer Science?"
  - "Show me students by city"
  - "Create a pie chart of branches"
  - "What courses are available?"
  - "List all faculty members"

### 3. Data Exploration
- The AI agent processes your queries and generates appropriate SQL
- Results are displayed as tables and interactive charts
- Get insights and suggestions for further exploration

## AI Agent Capabilities

The AI Agent can:
- **Understand natural language queries** about college data
- **Generate SQL queries** dynamically based on user intent
- **Create visualizations** (bar charts, pie charts, line graphs)
- **Provide insights** and statistical analysis
- **Suggest follow-up questions** for deeper exploration

## Technical Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (college.db)
- **Authentication**: Firebase Auth
- **AI**: Google Gemini API
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **Data Processing**: Pandas, NumPy, SciPy

## Key Features

### 🔄 Unified System
- Single Flask application handling both Firebase auth and AI features
- Seamless integration between user management and data analysis
- Consistent user experience across all features

### 🧠 Intelligent Query Processing
- Natural language understanding
- Dynamic SQL generation
- Context-aware responses
- Multi-step reasoning

### 📈 Interactive Visualizations
- Real-time chart generation
- Multiple chart types (bar, pie, line, scatter)
- Responsive design
- Export capabilities

### 🔒 Security
- Firebase authentication
- Secure API endpoints
- Input validation
- SQL injection protection

## Development Notes

- The AI Agent uses a modular architecture with separate components for intent detection, entity extraction, query building, and visualization
- Firebase integration provides scalable authentication and data storage
- The system gracefully handles missing dependencies and provides fallback functionality
- All Unicode characters have been replaced with ASCII equivalents for Windows compatibility

## Troubleshooting

### Common Issues
1. **Unicode errors**: Ensure all print statements use ASCII characters
2. **Template not found**: Make sure templates are in the `templates/` folder
3. **Database errors**: Verify `college.db` exists and is accessible
4. **Firebase errors**: Check `firebase-config.json` credentials

### Debug Mode
Run with debug mode enabled:
```bash
python app.py
```

## Future Enhancements

- Add more visualization types (heatmaps, scatter plots, etc.)
- Implement user-specific data filtering
- Add data export functionality
- Enhance AI agent with more sophisticated reasoning
- Add real-time collaboration features
- Implement advanced analytics and machine learning insights

## License

This project is for educational and demonstration purposes.
