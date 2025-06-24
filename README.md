# HomePro - AI-Powered Contractor Marketplace

HomePro is a web-based platform that connects homeowners with contractors through AI-powered project submission and bidding. Homeowners can submit project requests via audio, video, or text, and AI processes these requests for contractor review and bidding.

## Features

### Core Functionality
- **AI-Powered Project Submission**: Upload audio, video, or text descriptions
- **Automatic Transcription**: AWS Transcribe converts audio/video to text
- **Smart Analysis**: AWS Comprehend extracts project details, type, and scope
- **Bidding System**: Contractors can submit competitive bids
- **User Management**: Separate dashboards for homeowners and contractors
- **Project Management**: Track project status and manage bids

### User Types
- **Homeowners**: Submit projects, review bids, manage contractors
- **Contractors**: Browse projects, submit bids, manage business profile

### AI Features
- Audio/video transcription using AWS Transcribe
- Project type classification
- Scope of work extraction
- Timeline and budget analysis
- Location detail extraction

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: SQLAlchemy with SQLite (development)
- **Authentication**: Flask-Login
- **File Storage**: AWS S3
- **AI Services**: AWS Transcribe, AWS Comprehend
- **Email**: AWS SES

### Frontend
- **Framework**: Bootstrap 5
- **Icons**: Font Awesome
- **JavaScript**: Vanilla JS with modern ES6+
- **Styling**: Custom CSS with CSS Grid and Flexbox

### AWS Services
- **S3**: File storage for audio/video uploads
- **Transcribe**: Audio-to-text conversion
- **Comprehend**: Natural language processing
- **SES**: Email notifications

## Installation

### Prerequisites
- Python 3.8+
- AWS Account with configured credentials
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HomePro
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS credentials**
   ```bash
   # Option 1: AWS CLI
   aws configure
   
   # Option 2: Environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

5. **Set environment variables**
   Create a `.env` file in the project root:
   ```env
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   AWS_S3_BUCKET=your-s3-bucket-name
   AWS_REGION=us-east-1
   DATABASE_URL=sqlite:///homepro.db
   ```

6. **Initialize the database**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:5000`

## AWS Setup

### Required AWS Services

1. **S3 Bucket**
   - Create a bucket for file storage
   - Configure CORS for web uploads
   - Set appropriate permissions

2. **IAM Permissions**
   Your AWS user/role needs permissions for:
   - S3: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`
   - Transcribe: `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`
   - Comprehend: `comprehend:DetectEntities`, `comprehend:DetectSentiment`
   - SES: `ses:SendEmail`, `ses:SendRawEmail`

3. **SES Configuration**
   - Verify sender email addresses
   - Move out of sandbox for production

### Sample IAM Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "comprehend:DetectEntities",
                "comprehend:DetectSentiment",
                "comprehend:DetectKeyPhrases"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail",
                "ses:SendRawEmail"
            ],
            "Resource": "*"
        }
    ]
}
```

## Usage

### For Homeowners

1. **Register/Login**
   - Create account as "Homeowner"
   - Verify email address

2. **Submit Project**
   - Upload audio, video, or enter text description
   - AI will process and extract project details
   - Review and edit AI-generated summary
   - Confirm and post project

3. **Manage Projects**
   - View all submitted projects
   - Review contractor bids
   - Accept/reject bids
   - Close completed projects

### For Contractors

1. **Register/Login**
   - Create account as "Contractor"
   - Add business information and specialties
   - Verify email address

2. **Browse Projects**
   - View available projects
   - Filter by type, location, budget
   - Read project details

3. **Submit Bids**
   - Enter bid amount and timeline
   - Provide detailed work description
   - Track bid status

## File Structure

```
HomePro/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── static/
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── main.js       # JavaScript functionality
└── templates/
    ├── base.html         # Base template
    ├── index.html        # Homepage
    ├── login.html        # Login page
    ├── register.html     # Registration page
    ├── homeowner_dashboard.html
    ├── contractor_dashboard.html
    ├── submit_project.html
    ├── review_project.html
    └── project_detail.html
```

## API Endpoints

### Authentication
- `GET /` - Homepage
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /register` - Registration page
- `POST /register` - Process registration
- `GET /logout` - Logout user

### Projects
- `GET /dashboard` - User dashboard
- `GET /submit_project` - Project submission form
- `POST /submit_project` - Process project submission
- `GET /review_project/<id>` - Review AI-processed project
- `POST /confirm_project/<id>` - Confirm and post project
- `GET /project/<id>` - View project details
- `POST /close_project/<id>` - Close project

### Bidding
- `POST /submit_bid/<project_id>` - Submit bid
- `POST /accept_bid/<bid_id>` - Accept bid
- `POST /reject_bid/<bid_id>` - Reject bid

## Development

### Running in Development Mode
```bash
export FLASK_ENV=development
python app.py
```

### Database Migrations
For schema changes, you may need to recreate the database:
```bash
python -c "from app import app, db; app.app_context().push(); db.drop_all(); db.create_all()"
```

### Testing
Create test accounts:
- Homeowner: `homeowner@test.com` / `password123`
- Contractor: `contractor@test.com` / `password123`

## Production Deployment

### Environment Variables
Set these in production:
```env
FLASK_ENV=production
SECRET_KEY=strong-random-secret-key
DATABASE_URL=postgresql://user:pass@host:port/dbname
AWS_S3_BUCKET=production-bucket-name
```

### Database
For production, use PostgreSQL:
```bash
pip install psycopg2-binary
```

### Security Considerations
- Use HTTPS in production
- Set strong SECRET_KEY
- Configure proper CORS settings
- Implement rate limiting
- Use environment variables for sensitive data
- Regular security updates

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify AWS credentials are configured
   - Check IAM permissions
   - Ensure correct region settings

2. **File Upload Issues**
   - Check S3 bucket permissions
   - Verify CORS configuration
   - Ensure file size limits

3. **Database Errors**
   - Recreate database if schema changed
   - Check database file permissions
   - Verify SQLAlchemy configuration

4. **AI Processing Errors**
   - Check AWS service availability
   - Verify file formats are supported
   - Monitor AWS service limits

### Logs
Check application logs for detailed error information:
```bash
tail -f app.log
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Email: support@homepro.com
- Documentation: [Wiki](link-to-wiki)

## Roadmap

### Phase 1 (Current)
- ✅ Basic project submission
- ✅ AI processing
- ✅ Bidding system
- ✅ User management

### Phase 2 (Planned)
- 📋 Payment processing
- 📋 Real-time messaging
- 📋 Mobile app
- 📋 Advanced AI features
- 📋 Contractor verification
- 📋 Review system

### Phase 3 (Future)
- 📋 Multi-language support
- 📋 Advanced analytics
- 📋 API for third-party integrations
- 📋 Machine learning improvements