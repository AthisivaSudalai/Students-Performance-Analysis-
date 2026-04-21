from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from datetime import timedelta, datetime, timezone
import os
from werkzeug.utils import secure_filename
from data_processor import DataProcessor
from xhtml2pdf import pisa
import io
import base64

app = Flask(__name__)
app.secret_key = 'spas-secret-key-2026'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}

# ── Session security config ───────────────────────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY'] = True   # JS cannot access the cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # idle timeout

SESSION_TIMEOUT_MINUTES = 30  # inactivity timeout

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/charts', exist_ok=True)

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

# ── Before every request ─────────────────────────────────────────────────────

@app.before_request
def check_session():
    """Enforce inactivity timeout on every request to protected routes."""
    protected = {'upload', 'dashboard', 'download_pdf'}
    if request.endpoint in protected:
        if 'username' in session and not is_session_valid():
            flash('Your session expired due to inactivity. Please log in again.', 'error')
            return redirect(url_for('login'))
        if is_session_valid():
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
def upload():
    if not is_session_valid():
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
            processor.generate_visualizations()

            session['analysis'] = analysis
            session['filename'] = filename
            return redirect(url_for('dashboard'))

        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('upload.html')

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if not is_session_valid():
        return redirect(url_for('login'))
    if 'analysis' not in session:
        flash('No data yet. Please upload a file first.', 'error')
        return redirect(url_for('upload'))

    analysis = session['analysis']
    filename = session.get('filename', '')
    login_time = session.get('login_time', '')

    return render_template('dashboard.html',
                           analysis=analysis,
                           filename=filename,
                           username=session['username'],
                           login_time=login_time)

# ── PDF Download ──────────────────────────────────────────────────────────────

def chart_to_base64(filename):
    """Read a chart PNG and return a base64 data URI for embedding in PDF HTML."""
    path = os.path.join('static', 'charts', filename)
    if not os.path.exists(path):
        return ''
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    return f'data:image/png;base64,{data}'

@app.route('/download-pdf')
def download_pdf():
    if not is_session_valid():
        return redirect(url_for('login'))
    if 'analysis' not in session:
        flash('No data available. Please upload a file first.', 'error')
        return redirect(url_for('upload'))

    analysis = session['analysis']
    filename = session.get('filename', 'report')

    charts = {
        'histogram':  chart_to_base64('histogram.png'),
        'bar_chart':  chart_to_base64('bar_chart.png'),
        'line_chart': chart_to_base64('line_chart.png'),
        'pie_chart':  chart_to_base64('pie_chart.png'),
        'performers': chart_to_base64('performers.png'),
    }

    html = render_template('pdf_report.html',
                           analysis=analysis,
                           filename=filename,
                           username=session['username'],
                           charts=charts)

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)

    if pisa_status.err:
        flash('Error generating PDF. Please try again.', 'error')
        return redirect(url_for('dashboard'))

    pdf_name = filename.rsplit('.', 1)[0] + '_report.pdf'
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{pdf_name}"'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
