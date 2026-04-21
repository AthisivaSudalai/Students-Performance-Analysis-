from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from datetime import timedelta, datetime, timezone
import os
import tempfile
from werkzeug.utils import secure_filename
from data_processor import DataProcessor
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import base64

app = Flask(__name__)
app.secret_key = 'spas-secret-key-2026'

# Use /tmp on Vercel (read-only filesystem), local dirs otherwise
IS_VERCEL = bool(os.environ.get('VERCEL'))
BASE_TMP  = tempfile.gettempdir()

UPLOAD_FOLDER = os.path.join(BASE_TMP, 'uploads')       if IS_VERCEL else 'uploads'
CHARTS_FOLDER = os.path.join(BASE_TMP, 'static_charts') if IS_VERCEL else 'static/charts'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}

# ── Session security config ───────────────────────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

SESSION_TIMEOUT_MINUTES = 30

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHARTS_FOLDER, exist_ok=True)

USERS = {
    'staff': 'password123',
    'admin': 'admin123'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ── Session helpers ───────────────────────────────────────────────────────────

def is_session_valid():
    """Check if the session exists and hasn't timed out due to inactivity."""
    if 'username' not in session:
        return False
    last_active = session.get('last_active')
    if last_active is None:
        return False
    elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(last_active)
    if elapsed > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        session.clear()
        return False
    return True

def touch_session():
    """Refresh the last-active timestamp on every authenticated request."""
    session['last_active'] = datetime.now(timezone.utc).isoformat()
    session.modified = True

def require_login(f):
    """Decorator to require login for specific routes."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_valid():
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ── Before every request ─────────────────────────────────────────────────────

@app.before_request
def check_session():
    """Enforce inactivity timeout on every request to protected routes."""
    protected = {'upload', 'dashboard', 'download_pdf'}
    
    # Allow access to login, logout, and static files without authentication
    if request.endpoint in {'login', 'logout', 'static'} or request.endpoint is None:
        return
    
    # For all other routes, enforce authentication
    if request.endpoint in protected or request.endpoint not in {'login', 'logout'}:
        if 'username' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        if not is_session_valid():
            flash('Your session expired due to inactivity. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        # Refresh session activity
        touch_session()

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if is_session_valid():
        return redirect(url_for('upload'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_session_valid():
        return redirect(url_for('upload'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember')  # "Remember this device" checkbox

        if username in USERS and USERS[username] == password:
            # Session fixation protection: clear any old session before setting new one
            session.clear()
            session['username'] = username
            session['last_active'] = datetime.now(timezone.utc).isoformat()
            session['login_time'] = datetime.now(timezone.utc).isoformat()

            if remember:
                # Persistent cookie — survives browser close (up to 2 hours)
                session.permanent = True
            else:
                # Session cookie — cleared when browser closes
                session.permanent = False

            return redirect(url_for('upload'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# ── Upload ────────────────────────────────────────────────────────────────────

@app.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    # Double-check authentication (belt and suspenders approach)
    if not is_session_valid():
        flash('Authentication required. Please log in first.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            flash('Please select a file before submitting.', 'error')
            return redirect(request.url)

        file = request.files['file']

        if not allowed_file(file.filename):
            flash('Only CSV (.csv) or Excel (.xlsx) files are accepted.', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        processor = DataProcessor(filepath)
        try:
            result = processor.validate_file()
            if not result['valid']:
                os.remove(filepath)
                flash(f'Validation failed: {result["error"]}', 'error')
                return redirect(request.url)

            processor.load_data()
            analysis = processor.analyze_data()
            processor.generate_visualizations(CHARTS_FOLDER)

            session['analysis'] = analysis
            session['filename'] = filename
            flash(f'File "{filename}" uploaded and analyzed successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('upload.html', username=session.get('username', ''))

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@require_login
def dashboard():
    if 'analysis' not in session:
        flash('No data available. Please upload a file first.', 'info')
        return redirect(url_for('upload'))

    analysis = session['analysis']
    filename = session.get('filename', '')
    login_time = session.get('login_time', '')

    # Build chart URLs — base64 on Vercel (no static folder), normal URLs locally
    if IS_VERCEL:
        chart_urls = {k: chart_to_base64(v) for k, v in {
            'histogram': 'histogram.png', 'bar_chart': 'bar_chart.png',
            'line_chart': 'line_chart.png', 'pie_chart': 'pie_chart.png',
            'performers': 'performers.png'
        }.items()}
    else:
        chart_urls = {
            'histogram':  url_for('static', filename='charts/histogram.png'),
            'bar_chart':  url_for('static', filename='charts/bar_chart.png'),
            'line_chart': url_for('static', filename='charts/line_chart.png'),
            'pie_chart':  url_for('static', filename='charts/pie_chart.png'),
            'performers': url_for('static', filename='charts/performers.png'),
        }

    return render_template('dashboard.html',
                           analysis=analysis,
                           filename=filename,
                           username=session['username'],
                           login_time=login_time,
                           chart_urls=chart_urls)

# ── PDF Download ──────────────────────────────────────────────────────────────

def chart_to_base64(filename):
    """Read a chart PNG and return a base64 data URI for embedding in PDF HTML."""
    path = os.path.join(CHARTS_FOLDER, filename)
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    return f'data:image/png;base64,{data}'

@app.route('/download-pdf')
@require_login
def download_pdf():
    if 'analysis' not in session:
        flash('No data available. Please upload a file first.', 'error')
        return redirect(url_for('upload'))

    analysis = session['analysis']
    filename = session.get('filename', 'report')

    try:
        # Create PDF using reportlab
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("EduMetrics - Student Performance Analysis Report", title_style))
        story.append(Spacer(1, 20))

        # File info
        story.append(Paragraph(f"<b>File:</b> {filename}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated by:</b> {session['username']}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Summary Statistics
        story.append(Paragraph("<b>Summary Statistics</b>", styles['Heading2']))
        summary_data = [
            ['Total Students', str(analysis['total_students'])],
            ['Average Score', f"{analysis['average_score']:.2f}"],
            ['Pass Rate', f"{analysis['pass_rate']:.1f}%"],
            ['Fail Rate', f"{analysis['fail_rate']:.1f}%"]
        ]
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # Top 5 Students
        story.append(Paragraph("<b>Top 5 Students (Overall Average)</b>", styles['Heading2']))
        top_data = [['Name', 'Test 1', 'Test 2', 'Test 3', 'Average']]
        for student in analysis['top_students']:
            top_data.append([
                student['Name'],
                str(student['Test1']),
                str(student['Test2']),
                str(student['Test3']),
                f"{student['Average']:.2f}"
            ])
        
        top_table = Table(top_data)
        top_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(top_table)
        story.append(Spacer(1, 20))

        # Bottom 5 Students
        story.append(Paragraph("<b>Bottom 5 Students (Overall Average)</b>", styles['Heading2']))
        bottom_data = [['Name', 'Test 1', 'Test 2', 'Test 3', 'Average']]
        for student in analysis['bottom_students']:
            bottom_data.append([
                student['Name'],
                str(student['Test1']),
                str(student['Test2']),
                str(student['Test3']),
                f"{student['Average']:.2f}"
            ])
        
        bottom_table = Table(bottom_data)
        bottom_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(bottom_table)
        story.append(Spacer(1, 20))

        # Add charts if they exist
        chart_files = ['histogram.png', 'bar_chart.png', 'line_chart.png', 'pie_chart.png', 'performers.png']
        for chart_file in chart_files:
            chart_path = os.path.join(CHARTS_FOLDER, chart_file)
            if os.path.exists(chart_path):
                try:
                    img = Image(chart_path, width=4*inch, height=3*inch)
                    story.append(img)
                    story.append(Spacer(1, 10))
                except:
                    pass  # Skip if image can't be loaded

        doc.build(story)
        
        pdf_name = filename.rsplit('.', 1)[0] + '_report.pdf'
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{pdf_name}"'
        return response
    
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/test-auth')
def test_auth():
    """Test route to verify authentication is working"""
    if is_session_valid():
        return f"✅ Authentication working! Logged in as: {session.get('username')}"
    else:
        return "❌ Not authenticated - you should be redirected to login"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
