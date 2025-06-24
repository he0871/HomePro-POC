from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timedelta
# Optional imports for development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file will not be loaded.")

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    print("Warning: boto3 not installed. AWS features will be disabled.")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///homepro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
# CSRF protection disabled for development

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# AWS Configuration (optional for development)
if AWS_AVAILABLE:
    try:
        transcribe_client = boto3.client('transcribe', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        comprehend_client = boto3.client('comprehend', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
        s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    except Exception as e:
        print(f"Warning: AWS client initialization failed: {e}")
        AWS_AVAILABLE = False
else:
    transcribe_client = comprehend_client = s3_client = None

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'homeowner' or 'contractor'
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    specialties = db.Column(db.Text)  # For contractors
    business_info = db.Column(db.Text)  # For contractors
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    projects = db.relationship('Project', backref='homeowner', lazy=True)
    bids = db.relationship('Bid', backref='contractor', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    project_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    budget_min = db.Column(db.Float)
    budget_max = db.Column(db.Float)
    timeline = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Active')  # Active, Completed, Closed, Archived
    original_file_path = db.Column(db.String(255))
    ai_processed_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    homeowner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    bids = db.relationship('Bid', backref='project', lazy=True, cascade='all, delete-orphan')

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    timeline = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Submitted')  # Submitted, Under Review, Accepted, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    contractor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def allowed_file(filename, file_type):
    if file_type == 'audio':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp3', 'wav']
    elif file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp4', 'mov']
    return False

def process_ai_submission(file_path, file_type, text_content=None):
    """
    Process uploaded file or text using AWS AI services
    """
    try:
        transcribed_text = ""
        
        if text_content:
            transcribed_text = text_content
        elif file_type in ['audio', 'video'] and AWS_AVAILABLE:
            # Upload to S3 first
            s3_key = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(file_path)}"
            s3_client.upload_file(file_path, os.environ.get('AWS_S3_BUCKET'), s3_key)
            
            # Start transcription job
            job_name = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': f"s3://{os.environ.get('AWS_S3_BUCKET')}/{s3_key}"},
                MediaFormat=file_path.split('.')[-1].lower(),
                LanguageCode='en-US'
            )
            
            # Wait for transcription to complete (simplified for demo)
            import time
            while True:
                response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                if status == 'COMPLETED':
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    # Download and parse transcript (simplified)
                    transcribed_text = "Sample transcribed text from audio/video"
                    break
                elif status == 'FAILED':
                    raise Exception("Transcription failed")
                time.sleep(5)
        elif file_type in ['audio', 'video'] and not AWS_AVAILABLE:
            # Mock transcription for development
            transcribed_text = "Mock transcribed text: I need to fix my kitchen sink. It's been leaking for a week and I think it needs a new faucet. My budget is around $200-500 and I'd like it done within 2 weeks."
        
        # Use Comprehend to analyze the text or mock analysis
        if transcribed_text:
            if AWS_AVAILABLE:
                entities_response = comprehend_client.detect_entities(
                    Text=transcribed_text,
                    LanguageCode='en'
                )
                
                key_phrases_response = comprehend_client.detect_key_phrases(
                    Text=transcribed_text,
                    LanguageCode='en'
                )
            else:
                # Mock responses for development
                entities_response = {'Entities': []}
                key_phrases_response = {'KeyPhrases': []}
            
            # Extract project details (simplified logic)
            project_data = {
                'transcribed_text': transcribed_text,
                'title': extract_project_title(transcribed_text),
                'project_type': extract_project_type(transcribed_text, entities_response),
                'location': extract_location(entities_response),
                'description': transcribed_text,
                'budget_min': extract_budget_range(transcribed_text)[0],
                'budget_max': extract_budget_range(transcribed_text)[1],
                'timeline': extract_timeline(transcribed_text),
                'confidence': 0.85 if AWS_AVAILABLE else 0.75  # Lower confidence for mock data
            }
            
            return project_data
    
    except Exception as e:
        print(f"AI processing error: {e}")
        return None

# Helper functions for AI text analysis
def extract_project_title(text):
    """Extract a project title from the text"""
    # Simple logic to create a title from the first sentence or key phrases
    sentences = text.split('.')
    if sentences:
        first_sentence = sentences[0].strip()
        if len(first_sentence) > 50:
            return first_sentence[:47] + "..."
        return first_sentence
    return "Home Improvement Project"

def extract_project_type(text, entities_response):
    """Extract project type from text"""
    text_lower = text.lower()
    
    # Common project types and keywords
    project_types = {
        'plumbing': ['plumb', 'pipe', 'faucet', 'sink', 'toilet', 'drain', 'leak', 'water'],
        'electrical': ['electric', 'wire', 'outlet', 'switch', 'light', 'circuit', 'power'],
        'kitchen': ['kitchen', 'cabinet', 'countertop', 'appliance', 'stove', 'refrigerator'],
        'bathroom': ['bathroom', 'shower', 'bathtub', 'tile', 'vanity'],
        'roofing': ['roof', 'shingle', 'gutter', 'leak'],
        'flooring': ['floor', 'carpet', 'hardwood', 'tile', 'laminate'],
        'painting': ['paint', 'wall', 'interior', 'exterior'],
        'hvac': ['heating', 'cooling', 'hvac', 'furnace', 'air conditioning'],
        'general': ['repair', 'fix', 'maintenance', 'handyman']
    }
    
    for project_type, keywords in project_types.items():
        if any(keyword in text_lower for keyword in keywords):
            return project_type.title()
    
    return 'General'

def extract_location(entities_response):
    """Extract location from entities"""
    # Look for location entities
    if 'Entities' in entities_response:
        for entity in entities_response['Entities']:
            if entity['Type'] == 'LOCATION':
                return entity['Text']
    return 'Not specified'

def extract_budget_range(text):
    """Extract budget range from text"""
    import re
    
    # Look for dollar amounts
    dollar_pattern = r'\$([0-9,]+)'
    matches = re.findall(dollar_pattern, text)
    
    if matches:
        amounts = [int(match.replace(',', '')) for match in matches]
        if len(amounts) >= 2:
            return min(amounts), max(amounts)
        elif len(amounts) == 1:
            amount = amounts[0]
            # If single amount, create a range around it
            return amount * 0.8, amount * 1.2
    
    # Look for budget keywords
    text_lower = text.lower()
    if 'budget' in text_lower or 'cost' in text_lower or 'price' in text_lower:
        # Default budget ranges based on common project types
        if any(word in text_lower for word in ['kitchen', 'bathroom']):
            return 5000, 25000
        elif any(word in text_lower for word in ['roof', 'hvac']):
            return 3000, 15000
        else:
            return 500, 5000
    
    return None, None

def extract_timeline(text):
    """Extract timeline from text"""
    text_lower = text.lower()
    
    # Look for timeline keywords
    if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'emergency']):
        return 'ASAP'
    elif any(word in text_lower for word in ['week', '1 week', 'within a week']):
        return '1 week'
    elif any(word in text_lower for word in ['2 weeks', 'two weeks', 'couple weeks']):
        return '2 weeks'
    elif any(word in text_lower for word in ['month', '1 month', 'within a month']):
        return '1 month'
    elif any(word in text_lower for word in ['flexible', 'no rush', 'whenever']):
        return 'Flexible'
    
    return '2-4 weeks'

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        location = request.form.get('location', '')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            user_type=user_type,
            first_name=first_name,
            last_name=last_name,
            location=location,
            is_verified=True  # Skip email verification for MVP
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful!')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'homeowner':
        projects = Project.query.filter_by(homeowner_id=current_user.id).order_by(Project.created_at.desc()).all()
        return render_template('homeowner_dashboard.html', projects=projects)
    else:
        projects = Project.query.filter_by(status='Active').order_by(Project.created_at.desc()).all()
        return render_template('contractor_dashboard.html', projects=projects)

@app.route('/submit_project', methods=['GET', 'POST'])
def submit_project():
    # Allow unauthenticated access for project submission
    if request.method == 'POST':
        # Handle file upload
        file = request.files.get('file')
        text_description = request.form.get('text_description', '')
        
        ai_results = None
        file_path = None
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Determine file type and process with AI
            if allowed_file(filename, 'audio') or allowed_file(filename, 'video'):
                ai_results = process_ai_submission(file_path, 'audio' if allowed_file(filename, 'audio') else 'video')
        
        # If no file or AI processing failed, use text description
        if not ai_results and text_description:
            ai_results = process_ai_submission(None, 'text', text_description)
        
        if ai_results:
            # Store in session for review
            session['ai_results'] = ai_results
            session['file_path'] = file_path
            return redirect(url_for('review_project'))
        else:
            flash('Please provide either a file or text description')
    
    return render_template('submit_project.html')

@app.route('/review_project')
def review_project():
    ai_results = session.get('ai_results')
    file_path = session.get('file_path')
    
    if not ai_results:
        flash('No project data found. Please submit a project first.')
        return redirect(url_for('submit_project'))
    
    return render_template('review_project.html', ai_results=ai_results, file_path=file_path)

@app.route('/confirm_project', methods=['POST'])
def confirm_project():
    # Check if user is logged in for project confirmation
    if not current_user.is_authenticated:
        flash('Please log in to confirm and submit your project')
        return redirect(url_for('login'))
    
    if current_user.user_type != 'homeowner':
        flash('Only homeowners can submit projects')
        return redirect(url_for('dashboard'))
    
    # Get form data
    title = request.form['title']
    description = request.form['description']
    project_type = request.form['project_type']
    location = request.form['location']
    budget_min = float(request.form['budget_min']) if request.form['budget_min'] else None
    budget_max = float(request.form['budget_max']) if request.form['budget_max'] else None
    timeline = request.form['timeline']
    
    # Create project
    project = Project(
        title=title,
        description=description,
        project_type=project_type,
        location=location,
        budget_min=budget_min,
        budget_max=budget_max,
        timeline=timeline,
        homeowner_id=current_user.id
    )
    
    db.session.add(project)
    db.session.commit()
    
    flash('Project submitted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/project/<int:project_id>')
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Only show bids to authenticated users
    bids = []
    show_bids = False
    if current_user.is_authenticated:
        bids = Bid.query.filter_by(project_id=project_id).order_by(Bid.amount.asc()).all()
        show_bids = True
    
    return render_template('project_detail.html', project=project, bids=bids, show_bids=show_bids)

@app.route('/submit_bid/<int:project_id>', methods=['POST'])
@login_required
def submit_bid(project_id):
    if current_user.user_type != 'contractor':
        flash('Only contractors can submit bids')
        return redirect(url_for('dashboard'))
    
    project = Project.query.get_or_404(project_id)
    
    # Check if contractor already bid on this project
    existing_bid = Bid.query.filter_by(project_id=project_id, contractor_id=current_user.id).first()
    if existing_bid:
        flash('You have already submitted a bid for this project')
        return redirect(url_for('view_project', project_id=project_id))
    
    amount = float(request.form['amount'])
    timeline = request.form['timeline']
    description = request.form['description']
    
    bid = Bid(
        amount=amount,
        timeline=timeline,
        description=description,
        project_id=project_id,
        contractor_id=current_user.id
    )
    
    db.session.add(bid)
    db.session.commit()
    
    flash('Bid submitted successfully!')
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/accept_bid/<int:bid_id>', methods=['POST'])
@login_required
def accept_bid(bid_id):
    bid = Bid.query.get_or_404(bid_id)
    project = bid.project
    
    # Only the project owner can accept bids
    if project.homeowner_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only accept bids for your own projects'}), 403
    
    # Check if project is still active
    if project.status != 'Active':
        return jsonify({'success': False, 'message': 'This project is no longer active'}), 400
    
    # Update bid status to accepted
    bid.status = 'Accepted'
    
    # Reject all other bids for this project
    other_bids = Bid.query.filter_by(project_id=project.id).filter(Bid.id != bid_id).all()
    for other_bid in other_bids:
        if other_bid.status == 'Submitted':
            other_bid.status = 'Rejected'
    
    # Keep project active - don't close it automatically
    # Project will be marked as 'Completed' when work is finished
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Bid accepted successfully! Project awarded to {bid.contractor.first_name} {bid.contractor.last_name}'
    })

@app.route('/reject_bid/<int:bid_id>', methods=['POST'])
@login_required
def reject_bid(bid_id):
    bid = Bid.query.get_or_404(bid_id)
    project = bid.project
    
    # Only the project owner can reject bids
    if project.homeowner_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only reject bids for your own projects'}), 403
    
    # Update bid status to rejected
    bid.status = 'Rejected'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Bid rejected successfully'})

@app.route('/complete_project/<int:project_id>', methods=['POST'])
@login_required
def complete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check if user has permission to mark project as completed
    # Either the homeowner or the contractor with accepted bid can mark it complete
    accepted_bid = Bid.query.filter_by(project_id=project_id, status='Accepted').first()
    
    can_complete = False
    if current_user.id == project.homeowner_id:
        can_complete = True
    elif accepted_bid and current_user.id == accepted_bid.contractor_id:
        can_complete = True
    
    if not can_complete:
        return jsonify({'success': False, 'message': 'You do not have permission to complete this project'}), 403
    
    # Check if project has an accepted bid
    if not accepted_bid:
        return jsonify({'success': False, 'message': 'Project must have an accepted bid before it can be completed'}), 400
    
    project.status = 'Completed'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Project marked as completed successfully!'})

@app.route('/close_project/<int:project_id>', methods=['POST'])
@login_required
def close_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if project.homeowner_id != current_user.id:
        flash('You can only close your own projects')
        return redirect(url_for('dashboard'))
    
    project.status = 'Closed'
    db.session.commit()
    
    flash('Project closed successfully!')
    return redirect(url_for('dashboard'))

def create_demo_users():
    """Create demo users if they don't exist"""
    # Create demo homeowner
    homeowner = User.query.filter_by(email='homeowner@demo.com').first()
    if not homeowner:
        homeowner = User(
            email='homeowner@demo.com',
            password_hash=generate_password_hash('demo123'),
            user_type='homeowner',
            first_name='Demo',
            last_name='Homeowner',
            location='New York, NY',
            is_verified=True
        )
        db.session.add(homeowner)
    
    # Create demo contractor
    contractor = User.query.filter_by(email='contractor@demo.com').first()
    if not contractor:
        contractor = User(
            email='contractor@demo.com',
            password_hash=generate_password_hash('demo123'),
            user_type='contractor',
            first_name='Demo',
            last_name='Contractor',
            location='New York, NY',
            specialties='Plumbing, Electrical, General Repairs',
            business_info='Licensed contractor with 10+ years experience',
            is_verified=True
        )
        db.session.add(contractor)
    
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_demo_users()
    app.run(host='127.0.0.1', port=8000, debug=True)