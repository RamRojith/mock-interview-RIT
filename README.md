# RAMCO Academic System (RIT ERP)

A comprehensive Django-based Enterprise Resource Planning (ERP) system designed for Ramco Institute of Technology (RIT) to manage all academic and administrative operations.

## 📋 Overview

The RAMCO Academic System is a full-featured educational management platform that integrates multiple modules to handle the complete lifecycle of academic operations, from student admission to graduation, faculty management, course delivery, examination processing, and accreditation compliance.

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 6.0.2 with Django REST Framework
- **Database**: Multiple databases (MySQL, MSSQL) with database routing
- **Frontend**: HTML, CSS, JavaScript with Bootstrap
- **AI/ML**: LangChain, OpenAI GPT, ChromaDB for AI assistant features
- **File Processing**: ReportLab for PDF generation, OpenPyXL for Excel handling
- **Email**: Gmail SMTP integration
- **Deployment**: Configured for production with security headers

### Key Features
- Multi-role user management (Students, Faculty, Parents, Administrators)
- Comprehensive course and curriculum management
- Examination and assessment system
- Faculty leave and attendance management
- Fee collection and financial management
- Learning Management System (LMS)
- Library management
- NBA accreditation compliance tracking
- AI-powered chatbot assistant
- Data center management
- Feedback collection system
- Real-time notifications and email alerts

## 📚 Modules

### 1. User Accounts Management
- Multi-role authentication system
- Student, Faculty, and Parent profiles
- Department and degree management
- User permissions and access control
- Profile image management

### 2. Course Management
- Course creation and assignment
- Subject-faculty mapping
- Regulation and syllabus management
- Course categories and classifications
- Academic year management

### 3. Examination Management
- Internal assessment tracking
- Grade master configuration
- Examination scheduling
- Result processing and analysis
- Academic performance monitoring

### 4. Faculty Management
- Faculty profiles and information
- Designation management
- Teaching load assignment
- Faculty performance tracking
- Professional development records

### 5. Fee Management
- Fee structure configuration
- Payment tracking and collection
- Financial reporting
- Due date management
- Payment gateway integration ready

### 6. Learning Management System (LMS)
- Document sharing and management
- Assignment distribution
- Student submission tracking
- Academic resource repository
- Collaborative learning tools

### 7. Library Management
- Book cataloging and inventory
- Borrowing and return tracking
- Fine calculation and management
- Digital resource management
- Library usage analytics

### 8. NBA Accreditation
- Accreditation criteria tracking
- Intake and enrollment ratio monitoring
- Faculty qualification verification
- Infrastructure compliance
- Accreditation report generation

### 9. Faculty Leave Management
- Leave application and approval workflow
- Leave balance tracking
- Substitute faculty assignment
- Leave analytics and reporting

### 10. Feedback Management
- Student feedback collection
- Faculty evaluation system
- Course feedback analysis
- Quality improvement tracking

### 11. Data Center Management
- Centralized data management
- Report generation and analytics
- Data export and backup
- Audit trail maintenance

### 12. Student Management
- Student profile management
- Academic progress tracking
- Attendance monitoring
- Performance analytics
- Parent portal integration

### 13. AI Assistant & Chatbot
- Intelligent query processing
- Academic guidance and support
- Document analysis and insights
- Automated responses for common queries

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL Server
- MSSQL Server (for attendance database)
- Git

### Database Configuration
The system uses multiple databases:
- `default`: Main MySQL database (ramco_academic_system)
- `rit_approval_system`: Approval workflow database
- `rit_cgpatrack`: CGPA tracking database
- `rit_academic_system`: Legacy academic data
- `admissionform1`: Admission forms database
- `attendance_db`: MSSQL attendance database
- `erp_rit`: External ERP integration

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ramco_academic_system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure databases**
   - Create MySQL databases as specified in settings.py
   - Configure MSSQL connection for attendance database
   - Update database credentials in `rit_academic_system/settings.py`

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

## ⚙️ Configuration

### Email Configuration
The system is configured to use Gmail SMTP for email notifications. Update the following in `settings.py`:
```python
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### Security Settings
- CSRF trusted origins configured for production
- Secure proxy SSL header settings
- Debug mode disabled for production

### File Upload Settings
- Media files stored in `media/` directory
- Static files served from `static/` directory
- File size limits and type restrictions

## 🔐 Security Features

- Role-based access control (RBAC)
- CSRF protection
- SQL injection prevention
- XSS protection
- Secure password hashing
- Audit logging middleware
- File upload validation

## 📊 Database Schema

The system uses a complex database schema with relationships across multiple databases:

- **User Management**: Custom user model with role-based permissions
- **Academic Structure**: Degrees, departments, courses, subjects
- **Assessment**: Internal assessments, examinations, grading
- **Financial**: Fee structures, payments, financial tracking
- **LMS**: Documents, assignments, submissions
- **NBA**: Accreditation metrics and compliance tracking

## 🔧 API Endpoints

The system provides REST API endpoints for:
- User authentication and management
- Course and subject data
- Examination results
- Fee payment processing
- LMS document access
- Feedback submission

## 📈 Reporting & Analytics

- Academic performance reports
- Financial reports and analytics
- Attendance analytics
- Faculty workload analysis
- Student progress tracking
- Accreditation compliance reports

## 🌐 Deployment

### Production Deployment Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure production database
- [ ] Set up SSL certificate
- [ ] Configure web server (Nginx/Apache)
- [ ] Set up process manager (Gunicorn)
- [ ] Configure static file serving
- [ ] Set up backup systems
- [ ] Configure monitoring and logging

### Environment Variables
Create a `.env` file for sensitive configuration:
```
SECRET_KEY=your-secret-key
DATABASE_PASSWORD=your-db-password
EMAIL_HOST_PASSWORD=your-email-password
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test thoroughly
4. Submit a pull request with detailed description

## 📞 Support

For technical support or issues:
- IT Helpdesk: Extension 101
- Email: ritegovernance@ritrjpm.ac.in

## 📄 License

This project is proprietary software developed for Ramco Institute of Technology.

## 🏛️ About RIT

Ramco Institute of Technology (RIT) is committed to providing quality education and fostering innovation in engineering and technology. This ERP system supports our mission of delivering comprehensive educational services and maintaining high standards of academic excellence.

---

**Version**: 1.0.0
**Last Updated**: May 2026
**Django Version**: 6.0.2
**Python Version**: 3.8+</content>
<parameter name="filePath">e:\rit management\ramco_academic_system\README.md