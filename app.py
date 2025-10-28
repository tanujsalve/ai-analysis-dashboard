import os
import re
import pandas as pd
import numpy as np
import json
import io
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import scipy.stats as stats

# --- Firebase Setup ---
FIREBASE_AVAILABLE = False
firebase_admin = None
credentials = None
firestore = None
auth = None
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth
    FIREBASE_AVAILABLE = True
except ImportError:
    print("⚠️ Firebase not installed")

# --- AI SETUP ---
AI_AVAILABLE = False  # Temporarily disabled for stability
model = None
try:
    import google.generativeai as genai
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        # AI_AVAILABLE = True  # Commented out to disable AI
        print("WARNING: Gemini AI available but disabled for stability")
    else:
        print("WARNING: No API key")
except ImportError:
    print("WARNING: Google AI not installed")

# --- AI AGENT SETUP ---
try:
    from ai_agent import AIAnalystAgent
    ai_agent = AIAnalystAgent(db_path="college.db")
    print("SUCCESS: AI Agent initialized successfully")
except ImportError as e:
    print(f"WARNING: AI Agent not available: {e}")
    ai_agent = None

# --- GENERALIZED ANALYTICS AGENT SETUP ---
try:
    from generalized_analytics_agent import GeneralizedAnalyticsAgent
    analytics_agent = GeneralizedAnalyticsAgent()
    print("SUCCESS: Generalized Analytics Agent initialized successfully")
except ImportError as e:
    print(f"WARNING: Generalized Analytics Agent not available: {e}")
    analytics_agent = None

# Initialize Firebase
db_firestore = None
if FIREBASE_AVAILABLE:
    try:
        # Initialize Firebase with service account
        cred = credentials.Certificate('firebase-config.json')
        firebase_admin.initialize_app(cred)
        db_firestore = firestore.client()
        print("SUCCESS: Firebase initialized successfully")
    except Exception as e:
        print(f"ERROR: Firebase initialization failed: {e}")
        print("WARNING: Falling back to local storage")
        db_firestore = None
else:
    print("WARNING: Firebase not available, using local storage")

app = Flask(__name__)
CORS(app)

# Store uploaded data in memory (for demo purposes) - keeping for backward compatibility
uploaded_data = {}

def detect_user_intent(prompt: str) -> Dict[str, Any]:
    """Understand what user wants."""
    prompt_lower = prompt.lower()

    intent = {
        "action": "query",
        "wants_visualization": False,
        "visualization_type": None,
        "needs_aggregation": False
    }

    # Explicit visualization requests
    viz_keywords = {
        'bar': ['bar chart', 'bar graph', 'bars'],
        'line': ['line chart', 'line graph', 'trend', 'over time'],
        'scatter': ['scatter plot', 'scatter', 'correlation', 'relationship'],
        'pie': ['pie chart', 'pie', 'distribution', 'breakdown'],
        'heatmap': ['heatmap', 'heat map', 'correlation matrix'],
        'histogram': ['histogram', 'frequency']
    }

    for viz_type, keywords in viz_keywords.items():
        if any(kw in prompt_lower for kw in keywords):
            intent['wants_visualization'] = True
            intent['visualization_type'] = viz_type
            break

    # General visualization words
    if any(word in prompt_lower for word in ['visualize', 'plot', 'graph', 'chart', 'show me']):
        intent['wants_visualization'] = True

    # Aggregation indicators
    if any(word in prompt_lower for word in ['total', 'sum', 'average', 'count', 'group by', 'by', 'per']):
        intent['needs_aggregation'] = True

    return intent


def intelligent_sql_generation(prompt: str, schema: str, source_type: str) -> Optional[str]:
    """Generate smart SQL that understands context."""

    if not AI_AVAILABLE:
        return fallback_sql(prompt, schema, source_type)

    try:
        system_prompt = f"""You are an expert SQL analyst. Your job is to understand the user's question and generate the PERFECT SQL query.

**CRITICAL INTELLIGENCE RULES:**
1. **Table Selection**: Analyze which table(s) the question is about. Don't always use the first table.
2. **Column Selection**: Only SELECT columns that are relevant to the question.
3. **Aggregation**: If question asks for totals, averages, counts - use GROUP BY with aggregation.
4. **Joins**: If question involves multiple tables, use proper JOINs.
5. **Filtering**: Add WHERE clauses if question mentions specific conditions.
6. **Sorting**: Use ORDER BY if question asks for "top", "best", "highest", "lowest".
7. **Limits**: Add LIMIT for large result sets unless user wants everything.

**Schema:**
{schema}

**Source Type:** {'DataFrame (use table name df)' if source_type == 'file' else 'Database (use actual table names)'}

**User Question:** "{prompt}"

**Think step by step:**
1. What table(s) does this question relate to?
2. What columns are needed?
3. Does this need GROUP BY? (for aggregations)
4. Does this need JOIN? (for multiple tables)
5. Does this need WHERE? (for filtering)
6. Does this need ORDER BY? (for sorting)

Generate ONLY the SQL query. No explanations, no markdown, just SQL.

SQL Query:"""

        response = model.generate_content(system_prompt)
        sql = response.text.strip()
        sql = re.sub(r'```sql\s*|\s*```', '', sql).strip()

        if 'SELECT' in sql.upper():
            print(f"🤖 AI Generated SQL: {sql}")
            return sql

    except Exception as e:
        print(f"AI SQL error: {e}")

    return fallback_sql(prompt, schema, source_type)


def fallback_sql(prompt: str, schema: str, source_type: str) -> str:
    """Smart fallback when AI isn't available."""
    prompt_lower = prompt.lower()

    if source_type == 'file':
        table_name = 'df'
    else:
        # Try to extract table name from schema
        tables = re.findall(r'Table `(\w+)`', schema)

        # Try to match table name in question
        table_name = None
        for table in tables:
            if table.lower() in prompt_lower:
                table_name = table
                break

        if not table_name:
            table_name = tables[0] if tables else 'sales'

    # Build intelligent query
    if 'count' in prompt_lower or 'how many' in prompt_lower:
        return f"SELECT COUNT(*) as count FROM {table_name}"
    elif any(word in prompt_lower for word in ['group', 'by', 'category', 'per']):
        return f"SELECT * FROM {table_name} LIMIT 50"
    elif 'total' in prompt_lower or 'sum' in prompt_lower:
        return f"SELECT * FROM {table_name} LIMIT 50"
    else:
        return f"SELECT * FROM {table_name} LIMIT 100"


def generate_sql(prompt: str, schema: str, history: list, source_type: str) -> Optional[str]:
    """Main SQL generation with intelligence."""
    return intelligent_sql_generation(prompt, schema, source_type)


def analyze_dataframe_intelligence(df: pd.DataFrame) -> Dict[str, Any]:
    """Deep analysis of dataframe structure."""

    if df.empty:
        return {"error": "Empty dataframe"}

    analysis = {
        "row_count": len(df),
        "col_count": len(df.columns),
        "columns": {},
        "recommended_visualizations": []
    }

    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "unique_count": df[col].nunique(),
            "null_count": df[col].isnull().sum(),
            "is_numeric": pd.api.types.is_numeric_dtype(df[col]),
            "is_categorical": pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]),
            "is_datetime": pd.api.types.is_datetime64_any_dtype(df[col]),
            "is_id": 'id' in col.lower() or col.lower().endswith('_id'),
            "sample_values": df[col].dropna().head(3).tolist() if not df[col].empty else []
        }

        # Calculate visualization suitability score
        score = 0
        if col_info['is_id']:
            score = -100  # Never visualize IDs
        elif col_info['is_numeric'] and not col_info['is_id']:
            if col_info['unique_count'] > 20:
                score = 90  # Great for continuous viz
            else:
                score = 70  # Good for discrete viz
        elif col_info['is_categorical']:
            if 2 <= col_info['unique_count'] <= 20:
                score = 95  # Perfect for categorical viz
            elif col_info['unique_count'] > 50:
                score = 20  # Too many categories
            else:
                score = 60

        col_info['viz_score'] = score
        analysis['columns'][col] = col_info

    return analysis


def recommend_visualizations(df: pd.DataFrame, prompt: str, intent: Dict) -> List[Dict[str, Any]]:
    """Intelligently recommend visualizations based on data structure."""

    analysis = analyze_dataframe_intelligence(df)

    # Get high-value columns
    sorted_cols = sorted(analysis['columns'].items(), key=lambda x: x[1]['viz_score'], reverse=True)

    numeric_cols = [col for col, info in sorted_cols if info['is_numeric'] and not info['is_id']]
    categorical_cols = [col for col, info in sorted_cols if info['is_categorical'] and not info['is_id']]

    print(f"\n📊 Data Analysis:")
    print(f"   Numeric columns: {numeric_cols[:3]}")
    print(f"   Categorical columns: {categorical_cols[:3]}")

    recommendations = []

    # Rule 1: If user specified chart type, prioritize that
    if intent.get('visualization_type'):
        viz_type = intent['visualization_type']
        if viz_type == 'scatter' and len(numeric_cols) >= 2:
            recommendations.append({
                "type": "scatter",
                "x": numeric_cols[0],
                "y": numeric_cols[1],
                "reason": "User requested scatter plot"
            })
        elif viz_type == 'line' and categorical_cols and numeric_cols:
            recommendations.append({
                "type": "line",
                "x": categorical_cols[0],
                "y": numeric_cols[0],
                "reason": "User requested line chart"
            })
        elif viz_type == 'pie' and categorical_cols:
            recommendations.append({
                "type": "pie",
                "x": categorical_cols[0],
                "y": "count",
                "reason": "User requested pie chart"
            })

    # Rule 2: Categorical + Numeric = Bar Chart (most common and useful)
    if categorical_cols and numeric_cols:
        # Don't repeat if already added
        if not any(r['type'] == 'bar' and r['x'] == categorical_cols[0] for r in recommendations):
            recommendations.append({
                "type": "bar",
                "x": categorical_cols[0],
                "y": numeric_cols[0],
                "reason": f"Comparing {numeric_cols[0]} across {categorical_cols[0]}"
            })

    # Rule 3: Two numeric columns = Scatter Plot (shows correlation)
    if len(numeric_cols) >= 2:
        if not any(r['type'] == 'scatter' for r in recommendations):
            recommendations.append({
                "type": "scatter",
                "x": numeric_cols[0],
                "y": numeric_cols[1],
                "reason": f"Relationship between {numeric_cols[0]} and {numeric_cols[1]}"
            })

    # Rule 4: Single categorical = Pie/Doughnut (shows distribution)
    if categorical_cols:
        cat_col = categorical_cols[0]
        unique_count = analysis['columns'][cat_col]['unique_count']

        if 2 <= unique_count <= 10:  # Good for pie charts
            if not any(r['type'] == 'pie' and r['x'] == cat_col for r in recommendations):
                recommendations.append({
                    "type": "pie",
                    "x": cat_col,
                    "y": "count",
                    "reason": f"Distribution of {cat_col}"
                })

    # Rule 5: Multiple categoricals = Grouped bar chart
    if len(categorical_cols) >= 2 and numeric_cols:
        if not any(r['type'] == 'bar' and r['x'] == categorical_cols[1] for r in recommendations):
            recommendations.append({
                "type": "bar",
                "x": categorical_cols[1],
                "y": numeric_cols[0],
                "reason": f"Alternative view: {numeric_cols[0]} by {categorical_cols[1]}"
            })

    print(f"   Recommendations: {len(recommendations)} visualizations")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec['type'].upper()}: {rec['reason']}")

    return recommendations[:4]  # Limit to 4 charts


def create_chart_config(chart_type: str, title: str, x_col: str, y_col: str) -> Dict[str, Any]:
    """Create Chart.js configuration."""

    colors = {
        'bar': ['#2ECC71', '#3498DB', '#E74C3C', '#9B59B6', '#F39C12', '#1ABC9C'],
        'scatter': '#E74C3C',
        'line': '#3498DB',
        'pie': ['#2ECC71', '#3498DB', '#E74C3C', '#9B59B6', '#F39C12', '#1ABC9C', '#E67E22', '#16A085'],
    }

    config = {
        "type": chart_type,
        "data": {
            "labels": [x_col],
            "datasets": [{
                "label": title,
                "data": [y_col],
                "backgroundColor": colors.get(chart_type, colors['bar']),
                "borderColor": "#FFFFFF" if chart_type in ['pie'] else colors.get(chart_type, '#3498DB'),
                "borderWidth": 2 if chart_type in ['pie'] else 1
            }]
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": chart_type in ['pie', 'line']},
                "title": {"display": True, "text": title, "font": {"size": 14, "weight": "bold"}}
            }
        }
    }

    if chart_type in ['bar', 'line', 'scatter']:
        config["options"]["scales"] = {
            "y": {"beginAtZero": True},
            "x": {"display": True}
        }

    if chart_type == 'scatter':
        config["data"]["datasets"][0]["showLine"] = False
        config["data"]["datasets"][0]["pointRadius"] = 6
        config["data"]["datasets"][0]["pointBackgroundColor"] = '#E74C3C'

    return config


def generate_natural_response(prompt: str, df: pd.DataFrame, intent: Dict) -> str:
    """Generate conversational response."""

    if df.empty:
        return "I didn't find any data matching that query."

    row_count = len(df)

    if False:  # Temporarily disable AI for stability
        try:
            sample = df.head(5).to_string()
            response_prompt = f"""User asked: "{prompt}"

Result: {row_count} rows

Sample:
{sample}

Provide a brief, natural answer (1-2 sentences) about what this data shows.
Be conversational and don't use robotic phrases like "the data shows"."""
            response = model.generate_content(response_prompt)
            return response.text.strip()
        except:
            pass

    # Fallback
    cols = ', '.join(df.columns.tolist()[:3])
    return f"Found {row_count} records with columns: {cols}{'...' if len(df.columns) > 3 else ''}."


def analyze_data(prompt: str, df: pd.DataFrame) -> Dict[str, Any]:
    """Main intelligence function."""

    intent = detect_user_intent(prompt)

    print(f"\n🎯 Intent: {intent}")

    # Generate natural response
    summary = generate_natural_response(prompt, df, intent)

    # Decide on visualizations
    charts = []
    if intent['wants_visualization'] or len(df) <= 50:
        print("🎨 Generating visualizations...")
        recommendations = recommend_visualizations(df, prompt, intent)

        for rec in recommendations:
            title = f"{rec['y']} by {rec['x']}" if rec['y'] != 'count' else f"{rec['x']} Distribution"
            charts.append({
                "title": title,
                "config": create_chart_config(rec['type'], title, rec['x'], rec['y']),
                "recommendation": rec
            })

    return {
        "summary": summary,
        "charts": charts,
        "intent": intent
    }


@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    print("Upload endpoint called")
    if 'file' not in request.files:
        print("No file in request.files")
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    print(f"File received: {file.filename}")
    if file.filename == '':
        print("File filename is empty")
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Read the file based on extension
        filename = file.filename.lower()
        print(f"File extension: {filename}")
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
            print(f"CSV loaded, shape: {df.shape}")
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
            print(f"Excel loaded, shape: {df.shape}")
        else:
            print("Unsupported file format")
            return jsonify({'error': 'Unsupported file format'}), 400

        if db_firestore:
            try:
                # Save to Firestore
                doc_ref = db_firestore.collection('uploaded_files').document()
                doc_ref.set({
                    'filename': file.filename,
                    'data': df.to_json(orient='records'),
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                print(f"File saved to Firestore with id: {doc_ref.id}")
                file_id = doc_ref.id
            except Exception as e:
                print(f"❌ Firestore save failed: {e}")
                print("⚠️ Falling back to local storage")
                # Fallback to local storage
                file_id = str(len(uploaded_data) + 1)
                uploaded_data[file_id] = {
                    'filename': file.filename,
                    'data': df.to_json(orient='records'),
                    'created_at': pd.Timestamp.now()
                }
                print(f"File saved to local storage with id: {file_id}")
        else:
            # Save to local storage
            file_id = str(len(uploaded_data) + 1)
            uploaded_data[file_id] = {
                'filename': file.filename,
                'data': df.to_json(orient='records'),
                'created_at': pd.Timestamp.now()
            }
            print(f"File saved to local storage with id: {file_id}")

        return jsonify({
            'file_id': file_id,
            'filename': file.filename,
            'row_count': len(df),
            'columns': df.columns.tolist()
        })

    except Exception as e:
        print(f"Error in upload: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/analyze', methods=['POST'])
def analyze_uploaded_data():
    """Analyze uploaded data using the generalized analytics agent"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'File ID required'}), 400
        
        # Get the uploaded data
        df_data = None
        filename = None
        
        if db_firestore:
            try:
                doc = db_firestore.collection('uploaded_files').document(file_id).get()
                if doc.exists:
                    file_data = doc.to_dict()
                    df_data = pd.read_json(io.StringIO(file_data['data']))
                    filename = file_data['filename']
            except Exception as e:
                print(f"Error retrieving from Firestore: {e}")
        
        if df_data is None and file_id in uploaded_data:
            file_data = uploaded_data[file_id]
            df_data = pd.read_json(io.StringIO(file_data['data']))
            filename = file_data['filename']
        
        if df_data is None:
            return jsonify({'error': 'File not found'}), 404
        
        # Analyze using generalized analytics agent
        if analytics_agent:
            analysis_result = analytics_agent.analyze_data(df_data, filename)
            return jsonify(analysis_result)
        else:
            return jsonify({'error': 'Analytics agent not available'}), 500
            
    except Exception as e:
        print(f"Error in analytics analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/visualize', methods=['POST'])
def create_visualization():
    """Create visualization for uploaded data"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        chart_type = data.get('chart_type')
        columns = data.get('columns', [])
        
        if not file_id or not chart_type or not columns:
            return jsonify({'error': 'File ID, chart type, and columns required'}), 400
        
        # Get the uploaded data
        df_data = None
        
        if db_firestore:
            try:
                doc = db_firestore.collection('uploaded_files').document(file_id).get()
                if doc.exists:
                    file_data = doc.to_dict()
                    df_data = pd.read_json(io.StringIO(file_data['data']))
            except Exception as e:
                print(f"Error retrieving from Firestore: {e}")
        
        if df_data is None and file_id in uploaded_data:
            file_data = uploaded_data[file_id]
            df_data = pd.read_json(io.StringIO(file_data['data']))
        
        if df_data is None:
            return jsonify({'error': 'File not found'}), 404
        
        # Generate chart data
        if analytics_agent:
            chart_data = analytics_agent.generate_chart_data(df_data, chart_type, columns)
            return jsonify(chart_data)
        else:
            return jsonify({'error': 'Analytics agent not available'}), 500
            
    except Exception as e:
        print(f"Error in visualization: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/suggestions', methods=['POST'])
def get_analytics_suggestions():
    """Get analytics suggestions for uploaded data"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'File ID required'}), 400
        
        # Get the uploaded data
        df_data = None
        
        if db_firestore:
            try:
                doc = db_firestore.collection('uploaded_files').document(file_id).get()
                if doc.exists:
                    file_data = doc.to_dict()
                    df_data = pd.read_json(io.StringIO(file_data['data']))
            except Exception as e:
                print(f"Error retrieving from Firestore: {e}")
        
        if df_data is None and file_id in uploaded_data:
            file_data = uploaded_data[file_id]
            df_data = pd.read_json(io.StringIO(file_data['data']))
        
        if df_data is None:
            return jsonify({'error': 'File not found'}), 404
        
        # Get suggestions
        if analytics_agent:
            suggestions = analytics_agent._get_visualization_suggestions(df_data)
            return jsonify({'suggestions': suggestions})
        else:
            return jsonify({'error': 'Analytics agent not available'}), 500
            
    except Exception as e:
        print(f"Error in suggestions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process-pas', methods=['POST'])
def process_paste():
    print("Process paste endpoint called")
    pasted_data = request.get_data(as_text=True).strip()
    filename = request.args.get('filename', 'Pasted-Data.csv')

    if not pasted_data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        # Parse pasted CSV data
        from io import StringIO
        df = pd.read_csv(StringIO(pasted_data))
        print(f"Pasted CSV loaded, shape: {df.shape}")

        if db_firestore:
            try:
                # Save to Firestore
                doc_ref = db_firestore.collection('uploaded_files').document()
                doc_ref.set({
                    'filename': filename,
                    'data': df.to_json(orient='records'),
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                print(f"Pasted data saved to Firestore with id: {doc_ref.id}")
                file_id = doc_ref.id
            except Exception as e:
                print(f"❌ Firestore save failed: {e}")
                print("⚠️ Falling back to local storage")
                # Fallback to local storage
                file_id = str(len(uploaded_data) + 1)
                uploaded_data[file_id] = {
                    'filename': filename,
                    'data': df.to_json(orient='records'),
                    'created_at': pd.Timestamp.now()
                }
                print(f"Pasted data saved to local storage with id: {file_id}")
        else:
            # Save to local storage
            file_id = str(len(uploaded_data) + 1)
            uploaded_data[file_id] = {
                'filename': filename,
                'data': df.to_json(orient='records'),
                'created_at': pd.Timestamp.now()
            }
            print(f"Pasted data saved to local storage with id: {file_id}")

        return jsonify({
            'file_id': file_id,
            'filename': filename,
            'row_count': len(df),
            'columns': df.columns.tolist()
        })

    except Exception as e:
        print(f"Error processing pasted data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    file_id = data.get('file_id')
    prompt = data.get('prompt', '')

    try:
        if db_firestore:
            # Get data from Firestore
            doc_ref = db_firestore.collection('uploaded_files').document(file_id)
            doc = doc_ref.get()
            if not doc.exists:
                return jsonify({'error': 'File not found'}), 404
            file_data = doc.to_dict()
        else:
            # Get data from local storage
            if file_id not in uploaded_data:
                return jsonify({'error': 'File not found'}), 404
            file_data = uploaded_data[file_id]

        df = pd.read_json(file_data['data'], orient='records')

        result = analyze_data(prompt, df)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-dashboard', methods=['POST'])
def generate_dashboard():
    data = request.get_json()
    file_id = data.get('file_id')
    filename = data.get('filename', 'Dataset')

    try:
        file_data = None

        # Try Firestore first if available
        if db_firestore:
            try:
                doc_ref = db_firestore.collection('uploaded_files').document(file_id)
                doc = doc_ref.get()
                if doc.exists:
                    file_data = doc.to_dict()
            except Exception as e:
                print(f"Firestore access failed: {e}")

        # Fallback to local storage
        if file_data is None:
            if file_id not in uploaded_data:
                return jsonify({'error': 'File not found'}), 404
            file_data = uploaded_data[file_id]

        df = pd.read_json(file_data['data'], orient='records')

        # Analyze the dataframe to generate appropriate dashboard
        analysis = analyze_dataframe_intelligence(df)

        # Generate dashboard content based on data
        dashboard_data = generate_dashboard_content(df, filename, analysis)

        return jsonify(dashboard_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/load-sample', methods=['GET'])
def load_sample():
    """Load and analyze the sample.csv file automatically."""
    try:
        # Read the sample.csv file
        df = pd.read_csv('sample.csv')
        print(f"Sample CSV loaded, shape: {df.shape}")

        # Analyze the dataframe
        analysis = analyze_dataframe_intelligence(df)

        # Generate comprehensive dashboard for the sample data
        dashboard_data = generate_comprehensive_dashboard(df, analysis, request_type='comprehensive')

        # Store in Firestore for consistency
        if db_firestore:
            try:
                doc_ref = db_firestore.collection('uploaded_files').document('sample_data')
                doc_ref.set({
                    'filename': 'sample.csv',
                    'data': df.to_json(orient='records'),
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                print("Sample data stored in Firestore")
            except Exception as e:
                print(f"Firestore save failed: {e}")

        # Save to local storage if not using Firestore
        if not db_firestore:
            uploaded_data['sample_data'] = {
                'filename': 'sample.csv',
                'data': df.to_json(orient='records'),
                'created_at': pd.Timestamp.now()
            }
            print(f"Sample data saved to local storage with id: sample_data")

        return jsonify({
            'file_id': 'sample_data',
            'filename': 'sample.csv',
            'row_count': len(df),
            'columns': df.columns.tolist(),
            'dashboard_data': dashboard_data
        })

    except Exception as e:
        print(f"Error loading sample data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ai_dashboard')
def ai_dashboard():
    """AI Dashboard page"""
    return render_template('ai_dashboard.html')

@app.route('/api/ai/query', methods=['POST'])
def ai_query():
    """Handle AI chat queries using the AI Agent"""
    try:
        data = request.get_json()
        user_question = data.get('question', '').strip()

        if not user_question:
            return jsonify({
                "success": False,
                "error": "No question provided"
            })

        if not ai_agent:
            return jsonify({
                "success": False,
                "error": "AI Agent not available"
            })

        # Use AI Agent to process the request
        agent_response = ai_agent.process_user_input(user_question)

        # Extract data for frontend
        query_results = agent_response.get('data', [])
        chart_data = agent_response.get('visualization')
        explanation = agent_response.get('explanation', '')

        # Generate summary using Gemini for natural language
        summary = explanation or "Analysis completed successfully."
        if model and query_results:
            try:
                summary_prompt = f"""
                Based on this user question: {user_question}
                And these results: {str(query_results[:3])}

                Provide a brief, natural summary of what the user asked and what was found.
                Keep it conversational and helpful.
                """
                summary_response = model.generate_content(summary_prompt)
                summary = summary_response.text
            except Exception as e:
                print(f"AI summary error: {e}")

        return jsonify({
            "success": True,
            "explanation": explanation,
            "summary": summary,
            "data": query_results,
            "chart_data": chart_data,
            "agent_reasoning": agent_response.get('agent_reasoning', ''),
            "suggestions": agent_response.get('suggestions', []),
            "context": agent_response.get('context', {})
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/ai/visualize', methods=['POST'])
def ai_visualize():
    """Handle visualization requests"""
    try:
        data = request.get_json()
        chart_type = data.get('chart_type', 'bar')
        chart_data = data.get('chart_data', {})

        # Return chart configuration for frontend
        return jsonify({
            "success": True,
            "chart_config": chart_data
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/register', methods=['POST'])
def register():
    # Registration is handled entirely by the frontend Firebase Auth
    # This endpoint is kept for potential future backend validation or additional processing
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')

    if not email or not name:
        return jsonify({'error': 'Missing required fields'}), 400

    # Save user data to Firestore if available
    if db_firestore:
        try:
            # Check if user already exists
            users_ref = db_firestore.collection('users')
            existing_user = users_ref.where('email', '==', email).limit(1).get()

            if not existing_user.empty:
                return jsonify({'error': 'User already exists'}), 409

            # Create new user document
            user_doc = {
                'email': email,
                'name': name,
                'role': 'user',
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_login': firestore.SERVER_TIMESTAMP,
                'profile_complete': False
            }

            # Use sanitized email as document ID (replace @ and . with _)
            safe_email = email.replace('@', '_').replace('.', '_')
            doc_ref = users_ref.document(safe_email)
            doc_ref.set(user_doc)
            print(f"User registered in Firestore with ID: {doc_ref.id}")

            return jsonify({
                'message': 'Registration processed successfully',
                'email': email,
                'name': name,
                'user_id': doc_ref.id
            })

        except Exception as e:
            print(f"Firestore registration error: {e}")
            return jsonify({'error': f'Failed to save user data: {str(e)}'}), 500
    else:
        # Fallback to local storage (for demo purposes)
        print("⚠️ Firestore not available, registration data not persisted")
        if not hasattr(app, 'local_users'):
            app.local_users = {}
        safe_email = email.replace('@', '_').replace('.', '_')
        if safe_email in app.local_users:
            return jsonify({'error': 'User already exists'}), 409

        app.local_users[safe_email] = {
            'email': email,
            'name': name,
            'role': 'user',
            'created_at': pd.Timestamp.now(),
            'last_login': pd.Timestamp.now(),
            'profile_complete': False
        }

        return jsonify({
            'message': 'Registration processed successfully (local storage)',
            'email': email,
            'name': name,
            'user_id': safe_email
        })

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    file_id = data.get('file_id')

    if not message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        if db_firestore:
            # Get data from Firestore
            doc_ref = db_firestore.collection('uploaded_files').document(file_id)
            doc = doc_ref.get()
            if not doc.exists:
                return jsonify({'error': 'File not found'}), 404
            file_data = doc.to_dict()
        else:
            # Get data from local storage
            if file_id not in uploaded_data:
                return jsonify({'error': 'File not found'}), 404
            file_data = uploaded_data[file_id]

        df = pd.read_json(file_data['data'], orient='records')

        # Check for specific analysis requests
        message_lower = message.lower()

        # General bar chart request
        if 'bar chart' in message_lower or 'bar graph' in message_lower:
            analysis = analyze_dataframe_intelligence(df)
            dashboard_data = generate_comprehensive_dashboard(df, analysis, request_type='bar_chart')
            response_text = "I've created a bar chart visualization based on your data. The dashboard now includes this chart along with relevant analysis."

            return jsonify({
                'response': response_text,
                'dashboard_data': dashboard_data
            })

        # Box plot visualization
        elif 'box plot' in message_lower or 'boxplot' in message_lower:
            analysis = analyze_dataframe_intelligence(df)
            dashboard_data = generate_comprehensive_dashboard(df, analysis, request_type='box_plot')
            response_text = "I've added box plot visualizations to show the distribution of numeric variables across different categories. This helps identify outliers and compare distributions."

            return jsonify({
                'response': response_text,
                'dashboard_data': dashboard_data
            })

        # ANOVA test
        elif 'anova' in message_lower or 'analysis of variance' in message_lower:
            analysis = analyze_dataframe_intelligence(df)
            dashboard_data = generate_comprehensive_dashboard(df, analysis, request_type='anova')
            response_text = "I've performed ANOVA analysis to test for significant differences between groups. The results are displayed in the dashboard along with statistical insights."

            return jsonify({
                'response': response_text,
                'dashboard_data': dashboard_data
            })

        # Comprehensive analysis request
        elif any(word in message_lower for word in ['analyze', 'analysis', 'comprehensive', 'full analysis', 'deep dive', 'complete overview']):
            analysis = analyze_dataframe_intelligence(df)
            dashboard_data = generate_comprehensive_dashboard(df, analysis, request_type='comprehensive')
            response_text = "I've performed a comprehensive analysis of your dataset including statistical summaries, correlations, visualizations, and key insights. The dashboard now shows everything an AI CSV analysis website would provide."

            return jsonify({
                'response': response_text,
                'dashboard_data': dashboard_data
            })

        # Check for specific requests like "create overview and pie chart"
        if 'overview' in message_lower and 'pie chart' in message_lower:
            # Generate overview and pie chart dashboard
            analysis = analyze_dataframe_intelligence(df)
            overview_text = generate_overview_text(df, analysis)
            dashboard_data = generate_dashboard_content(df, 'Dataset', analysis, overview_text)

            response_text = "I've created an overview and pie chart for your dataset. The dashboard now shows the dataset overview and visualizations including a pie chart for categorical data distribution."

            return jsonify({
                'response': response_text,
                'dashboard_data': dashboard_data
            })

        # Use AI to generate response
        if AI_AVAILABLE:
            # Create context from dataframe
            sample_data = df.head(10).to_string()
            analysis = analyze_dataframe_intelligence(df)

            prompt = f"""You are an AI assistant helping with data analysis. The user asked: "{message}"

Dataset info:
- {analysis['row_count']} rows, {analysis['col_count']} columns
- Columns: {', '.join(df.columns.tolist())}

Sample data:
{sample_data}

Provide a helpful response. If the user wants to update the dashboard or create new visualizations, indicate that in your response and suggest changes.

Response:"""

            ai_response = model.generate_content(prompt)
            response_text = ai_response.text.strip()

            # Check if response indicates dashboard update
            update_keywords = ['update', 'change', 'modify', 'new chart', 'add visualization', 'dashboard']
            needs_update = any(keyword in response_text.lower() for keyword in update_keywords)

            result = {'response': response_text}

            if needs_update:
                # Generate new dashboard data
                filename = 'Updated Dataset'
                new_dashboard = generate_dashboard_content(df, filename, analysis)
                result['dashboard_data'] = new_dashboard

            return jsonify(result)
        else:
            return jsonify({'response': 'AI is not available. Please check your API key.'})

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': 'Failed to process chat message'}), 500

def generate_overview_text(df: pd.DataFrame, analysis: Dict) -> str:
    """Generate a text overview of the dataset."""
    overview = f"""Dataset Overview:

- Shape: {analysis['row_count']} rows, {analysis['col_count']} columns
- Columns: {', '.join(df.columns.tolist())}

- Missing Values: {sum(info['null_count'] for info in analysis['columns'].values())} total
- Sample Data:
{df.head(3).to_string()}"""
    return overview

def generate_comprehensive_dashboard(df: pd.DataFrame, analysis: Dict, request_type: str = 'comprehensive') -> Dict[str, Any]:
    """Generate comprehensive dashboard with AI-driven analysis."""

    # Determine dataset type
    dashboard_title = 'Comprehensive AI Data Analysis Dashboard'
    dashboard_description = 'AI-powered analysis with statistical insights, visualizations, and comprehensive data exploration'

    # Generate blocks based on data analysis and request type
    blocks = []
    insights = []

    # Get numeric and categorical columns
    numeric_cols = [col for col, info in analysis['columns'].items() if info['is_numeric'] and not info['is_id']]
    categorical_cols = [col for col, info in analysis['columns'].items() if info['is_categorical'] and not info['is_id']]

    # Dataset Overview Block
    overview_text = f"""📊 **Dataset Overview**

**Shape:** {analysis['row_count']} rows × {analysis['col_count']} columns
**Numeric Columns:** {len(numeric_cols)} ({', '.join(numeric_cols[:3])}{'...' if len(numeric_cols) > 3 else ''})
**Categorical Columns:** {len(categorical_cols)} ({', '.join(categorical_cols[:3])}{'...' if len(categorical_cols) > 3 else ''})
**Missing Values:** {sum(info['null_count'] for info in analysis['columns'].values())} total

**Sample Data:**
{df.head(3).to_string()}"""

    blocks.append({
        'icon': '📋',
        'title': 'Dataset Overview',
        'type': 'text',
        'content': overview_text
    })

    # Statistical Summary Block
    if numeric_cols:
        stats_text = "📈 **Statistical Summary**\n\n"
        for col in numeric_cols[:5]:  # Limit to 5 columns
            col_data = df[col].dropna()
            if len(col_data) > 0:
                stats_text += f"**{col}:**\n"
                stats_text += f"• Mean: {col_data.mean():.2f}\n"
                stats_text += f"• Std: {col_data.std():.2f}\n"
                stats_text += f"• Min: {col_data.min():.2f}\n"
                stats_text += f"• Max: {col_data.max():.2f}\n"
                stats_text += f"• Missing: {df[col].isnull().sum()}\n\n"

        blocks.append({
            'icon': '📊',
            'title': 'Statistical Summary',
            'type': 'text',
            'content': stats_text
        })

    # Specific request handling
    if request_type == 'bar_chart':
        # General bar chart - create bar chart with available categorical and numeric data
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]

            grouped = df.groupby(cat_col)[num_col].mean().reset_index()
            labels = grouped[cat_col].tolist()
            data = grouped[num_col].tolist()

            blocks.append({
                'icon': '📊',
                'title': f'Average {num_col} by {cat_col}',
                'type': 'bar',
                'labels': labels,
                'data': data,
                'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            })

            insights.append(f"Bar chart shows average {num_col} varies across {cat_col} categories.")
        else:
            # Fallback: create bar chart from value counts if no numeric columns
            if categorical_cols:
                cat_col = categorical_cols[0]
                value_counts = df[cat_col].value_counts().head(8)
                labels = value_counts.index.tolist()
                data = value_counts.values.tolist()

                blocks.append({
                    'icon': '📊',
                    'title': f'{cat_col} Distribution',
                    'type': 'bar',
                    'labels': labels,
                    'data': data,
                    'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF']
                })

                insights.append(f"Bar chart shows the distribution of {cat_col} categories.")

    elif request_type == 'bar_sepal_species' and 'sepal_length' in df.columns and 'species' in df.columns:
        # Bar chart of average sepal length by species
        grouped = df.groupby('species')['sepal_length'].mean().reset_index()
        labels = grouped['species'].tolist()
        data = grouped['sepal_length'].tolist()

        blocks.append({
            'icon': '📊',
            'title': 'Average Sepal Length by Species',
            'type': 'bar',
            'labels': labels,
            'data': data,
            'colors': ['#FF6384', '#36A2EB', '#FFCE56']
        })

        insights.append("Bar chart shows average sepal length varies significantly across species.")

    elif request_type == 'box_plot':
        # Box plot visualizations
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]

            # Prepare box plot data
            box_data = []
            categories = df[cat_col].unique()[:5]  # Limit to 5 categories

            for category in categories:
                cat_values = df[df[cat_col] == category][num_col].dropna()
                if len(cat_values) > 0:
                    quartiles = np.percentile(cat_values, [25, 50, 75])
                    iqr = quartiles[2] - quartiles[0]
                    lower_whisker = max(cat_values.min(), quartiles[0] - 1.5 * iqr)
                    upper_whisker = min(cat_values.max(), quartiles[2] + 1.5 * iqr)

                    box_data.append({
                        'category': str(category),
                        'min': float(lower_whisker),
                        'q1': float(quartiles[0]),
                        'median': float(quartiles[1]),
                        'q3': float(quartiles[2]),
                        'max': float(upper_whisker)
                    })

            blocks.append({
                'icon': '📦',
                'title': f'{num_col} Distribution by {cat_col}',
                'type': 'boxplot',
                'data': box_data,
                'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
            })

            insights.append("Box plots reveal distribution patterns and potential outliers across categories.")

    elif request_type == 'anova':
        # ANOVA test results
        if categorical_cols and len(numeric_cols) >= 1:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]

            # Perform ANOVA
            try:
                groups = [group[num_col].dropna() for name, group in df.groupby(cat_col)]
                if len(groups) >= 2 and all(len(g) > 1 for g in groups):
                    f_stat, p_value = stats.f_oneway(*groups)

                    anova_text = f"""🔬 **ANOVA Test Results**

**Test:** One-way ANOVA for {num_col} across {cat_col}
**F-statistic:** {f_stat:.4f}
**P-value:** {p_value:.4f}

**Interpretation:**
• {'Significant differences exist between groups' if p_value < 0.05 else 'No significant differences between groups'}
• P-value {'< 0.05' if p_value < 0.05 else '>= 0.05'} indicates {'statistical significance' if p_value < 0.05 else 'no statistical significance'}

**Group Means:**
"""
                    for name, group in df.groupby(cat_col):
                        mean_val = group[num_col].mean()
                        count = len(group)
                        anova_text += f"• {name}: {mean_val:.2f} (n={count})\n"

                    blocks.append({
                        'icon': '🔬',
                        'title': 'ANOVA Analysis Results',
                        'type': 'text',
                        'content': anova_text
                    })

                    insights.append(f"ANOVA analysis shows {'significant' if p_value < 0.05 else 'no significant'} differences in {num_col} across {cat_col} groups.")
                else:
                    blocks.append({
                        'icon': '⚠️',
                        'title': 'ANOVA Analysis',
                        'type': 'text',
                        'content': 'Insufficient data for ANOVA test. Need at least 2 groups with multiple observations each.'
                    })
            except Exception as e:
                blocks.append({
                    'icon': '⚠️',
                    'title': 'ANOVA Analysis Error',
                    'type': 'text',
                    'content': f'Could not perform ANOVA: {str(e)}'
                })

    # Default comprehensive visualizations - Always include overview, bar, pie, and additional charts
    if request_type == 'comprehensive' or request_type not in ['bar_sepal_species', 'box_plot', 'anova', 'bar_chart']:

        # Always try to create Bar Chart
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]

            grouped = df.groupby(cat_col)[num_col].mean().reset_index()
            labels = grouped[cat_col].tolist()
            data = grouped[num_col].tolist()

            blocks.append({
                'icon': '📊',
                'title': f'Average {num_col} by {cat_col}',
                'type': 'bar',
                'labels': labels,
                'data': data,
                'colors': ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00d4ff']
            })

            insights.append(f"Bar chart shows how {num_col} varies across different {cat_col} categories.")

        # Always try to create Pie Chart
        if categorical_cols:
            cat_col = categorical_cols[0]
            value_counts = df[cat_col].value_counts().head(8)

            blocks.append({
                'icon': '🥧',
                'title': f'{cat_col} Distribution',
                'type': 'pie',
                'labels': value_counts.index.tolist(),
                'data': value_counts.values.tolist(),
                'colors': ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00d4ff', '#ff9a9e', '#a8edea', '#fed6e3']
            })

            insights.append(f"Pie chart shows the distribution of {cat_col} with {len(value_counts)} categories.")

        # Additional chart types - Line Chart (if time-like data or ordered categories)
        if len(numeric_cols) >= 2:
            # Try to create a line chart with ordered data
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]

            # Sort by x for line chart
            sample_df = df[[x_col, y_col]].dropna().head(50).sort_values(x_col)
            x_data = sample_df[x_col].tolist()
            y_data = sample_df[y_col].tolist()

            blocks.append({
                'icon': '📈',
                'title': f'{y_col} Trend by {x_col}',
                'type': 'line',
                'labels': [f'{x:.1f}' for x in x_data],
                'data': y_data,
                'colors': ['#667eea']
            })

            insights.append(f"Line chart shows the trend of {y_col} as {x_col} changes.")

        # Scatter plot for correlation analysis
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]

            sample_df = df[[x_col, y_col]].dropna().head(100)
            x_data = sample_df[x_col].tolist()
            y_data = sample_df[y_col].tolist()

            blocks.append({
                'icon': '📈',
                'title': f'{y_col} vs {x_col} Relationship',
                'type': 'scatter',
                'data': [{'x': x, 'y': y} for x, y in zip(x_data, y_data)],
                'colors': ['#667eea']
            })

            # Calculate correlation
            corr = df[[x_col, y_col]].corr().iloc[0, 1]
            insights.append(f"Scatter plot reveals a {'strong' if abs(corr) > 0.7 else 'moderate' if abs(corr) > 0.3 else 'weak'} {'positive' if corr > 0 else 'negative'} correlation ({corr:.2f}) between {x_col} and {y_col}.")

        # Histogram for numeric distributions
        if numeric_cols:
            num_col = numeric_cols[0]
            hist_data = df[num_col].dropna()

            # Create histogram bins
            hist, bin_edges = np.histogram(hist_data, bins=10)
            labels = [f'{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}' for i in range(len(bin_edges)-1)]
            data = hist.tolist()

            blocks.append({
                'icon': '📊',
                'title': f'{num_col} Distribution',
                'type': 'bar',
                'labels': labels,
                'data': data,
                'colors': ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00d4ff', '#ff9a9e', '#a8edea', '#fed6e3', '#d4a574', '#9ca3af']
            })

            insights.append(f"Histogram shows the frequency distribution of {num_col} values.")

        # Correlation Matrix (text-based)
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            corr_text = "🔗 **Correlation Matrix**\n\n"

            for i, col1 in enumerate(numeric_cols[:5]):
                for j, col2 in enumerate(numeric_cols[:5]):
                    if i < j:  # Upper triangle only
                        corr_val = corr_matrix.loc[col1, col2]
                        strength = "strong" if abs(corr_val) > 0.7 else "moderate" if abs(corr_val) > 0.3 else "weak"
                        direction = "positive" if corr_val > 0 else "negative"
                        corr_text += f"• {col1} ↔ {col2}: {strength} {direction} ({corr_val:.2f})\n"

            blocks.append({
                'icon': '🔗',
                'title': 'Correlation Analysis',
                'type': 'text',
                'content': corr_text
            })

    # Generate AI-powered insights
    if AI_AVAILABLE:
        try:
            sample_data = df.head(10).to_string()
            ai_insights_prompt = f"""Analyze this dataset and provide 3-5 key insights:

Dataset shape: {analysis['row_count']} rows, {analysis['col_count']} columns
Columns: {', '.join(df.columns.tolist())}
Sample data:
{sample_data}

Provide concise, actionable insights about patterns, trends, or notable findings."""

            ai_response = model.generate_content(ai_insights_prompt)
            ai_insights = ai_response.text.strip().split('\n')
            insights.extend([insight.strip('- •') for insight in ai_insights if insight.strip()][:5])
        except:
            pass

    # Add general insights if needed
    if len(insights) < 3:
        insights.extend([
            f'Dataset contains {analysis["row_count"]} records across {analysis["col_count"]} variables.',
            'AI analysis complete with statistical summaries and visualizations.',
            'Explore different chart types to uncover additional patterns.'
        ])

    return {
        'title': dashboard_title,
        'description': dashboard_description,
        'blocks': blocks,
        'insights': insights[:8]  # Limit to 8 insights
    }


def generate_dashboard_content(df: pd.DataFrame, filename: str, analysis: Dict, overview_text: str = None) -> Dict[str, Any]:
    """Generate dashboard content based on data analysis."""

    # Determine dataset type
    filename_lower = filename.lower()

    if 'titanic' in filename_lower:
        dashboard_title = 'Titanic Dataset Dashboard'
        dashboard_description = 'AI-generated dashboard showing insights from the Titanic passenger data'
    elif 'ai' in filename_lower or 'generated' in filename_lower:
        dashboard_title = 'AI Generated Dataset Dashboard'
        dashboard_description = 'AI-generated dashboard showing insights from the AI-created sample data'
    else:
        dataset_name = filename.replace('.csv', '').replace('.xlsx', '').replace('.xls', '')
        dashboard_title = f'{dataset_name} Dashboard'
        dashboard_description = f'AI-generated dashboard showing insights from the {dataset_name} dataset'

    # Generate blocks based on data analysis
    blocks = []
    insights = []

    # Add overview text block if provided
    if overview_text:
        blocks.append({
            'icon': '📋',
            'title': 'Dataset Overview',
            'type': 'text',
            'content': overview_text
        })

    # Get numeric and categorical columns
    numeric_cols = [col for col, info in analysis['columns'].items() if info['is_numeric'] and not info['is_id']]
    categorical_cols = [col for col, info in analysis['columns'].items() if info['is_categorical'] and not info['is_id']]

    # Create visualization blocks
    if categorical_cols and numeric_cols:
        # Bar chart for categorical vs numeric
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]

        # Group by categorical and aggregate numeric
        grouped = df.groupby(cat_col)[num_col].mean().reset_index()
        labels = grouped[cat_col].tolist()
        data = grouped[num_col].tolist()

        blocks.append({
            'icon': '📊',
            'title': f'{num_col} by {cat_col}',
            'type': 'bar',
            'labels': labels,
            'data': data,
            'colors': ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00d4ff']
        })

        insights.append(f'Average {num_col} varies across {cat_col} categories.')

    if len(numeric_cols) >= 2:
        # Scatter plot for correlation
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]

        # Sample data for scatter (limit to 100 points)
        sample_df = df[[x_col, y_col]].dropna().head(100)
        x_data = sample_df[x_col].tolist()
        y_data = sample_df[y_col].tolist()

        blocks.append({
            'icon': '📈',
            'title': f'{y_col} vs {x_col}',
            'type': 'scatter',
            'data': [{'x': x, 'y': y} for x, y in zip(x_data, y_data)],
            'colors': ['#667eea']
        })

        # Calculate correlation
        corr = df[[x_col, y_col]].corr().iloc[0, 1]
        insights.append(f'There is a {"strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.3 else "weak"} {"positive" if corr > 0 else "negative"} correlation ({corr:.2f}) between {x_col} and {y_col}.')

    if categorical_cols:
        # Pie chart for distribution
        cat_col = categorical_cols[0]
        value_counts = df[cat_col].value_counts().head(8)  # Limit to 8 categories

        blocks.append({
            'icon': '🥧',
            'title': f'{cat_col} Distribution',
            'type': 'pie',
            'labels': value_counts.index.tolist(),
            'data': value_counts.values.tolist(),
            'colors': ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00d4ff', '#ff9a9e', '#a8edea', '#fed6e3']
        })

        insights.append(f'The dataset contains {len(value_counts)} categories in {cat_col}, with {value_counts.index[0]} being the most common.')

    # Add general insights
    insights.extend([
        f'The dataset contains {analysis["row_count"]} records with {analysis["col_count"]} columns.',
        'AI has analyzed your dataset and identified key patterns.',
        'Consider exploring additional visualizations to uncover more insights.'
    ])

    return {
        'title': dashboard_title,
        'description': dashboard_description,
        'blocks': blocks,
        'insights': insights[:5]  # Limit to 5 insights
    }
if __name__ == '__main__':
    app.run(debug=True, port=5000)
