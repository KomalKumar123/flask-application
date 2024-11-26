from flask import Flask, render_template , request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

# Create a Flask instance
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'  # Using SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking for performance
db = SQLAlchemy(app)

# User Table - General User Details
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)  # Unique Login ID
    password = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(15))
    role = db.Column(db.String(15), nullable=False)  # 'admin', 'customer', 'professional'
    is_blocked = db.Column(db.Boolean, default=False)  # Admin can block users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    professional_details = db.relationship('ProfessionalDetails', back_populates='user', uselist=False)
    customer_requests = db.relationship('ServiceRequest', back_populates='customer')

# Service Table - Details of all services
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type_of_service = db.Column(db.String(50), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    time_required = db.Column(db.Integer)  # Time in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    professionals = db.relationship('ProfessionalDetails', back_populates='service')
    service_requests = db.relationship('ServiceRequest', back_populates='service')

# ProfessionalDetails Table - Additional data for service professionals
class ProfessionalDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)  # Specific service type
    years_experience = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)  # Professional profile
    service_location = db.Column(db.String(100))  # City/area of operation
    average_rating = db.Column(db.Float, default=0.0)  # Average customer rating
    is_available = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # Admin approval for professionals

    # Relationships
    user = db.relationship('User', back_populates='professional_details')
    service = db.relationship('Service', back_populates='professionals')
    service_requests = db.relationship('ServiceRequest', back_populates='professional')

# ServiceRequest Table - Tracks requests made by customers
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional_details.id'), nullable=True)
    date_of_request = db.Column(db.DateTime, default=datetime.utcnow)
    date_of_completion = db.Column(db.DateTime, nullable=True)
    service_status = db.Column(db.String(20), default='requested')  # requested/assigned/closed
    remarks = db.Column(db.Text)

    # Relationships
    service = db.relationship('Service', back_populates='service_requests')
    customer = db.relationship('User', back_populates='customer_requests')
    professional = db.relationship('ProfessionalDetails', back_populates='service_requests')

# Define the route for the root URL
@app.route('/')
def home():
    # Render the home.html template from the templates folder
    return render_template('home.html')

@app.route('/beauty_services')
def beauty_services():
    # Render the beauty_services.html template from the templates folder
    return render_template('beauty_services.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        role = request.form['role']
        password = request.form['create_password']
        confirm_password = request.form['confirm_password']
        
        # You can add validation here (e.g., checking if passwords match)
        if password != confirm_password:
            return "Passwords do not match", 400

        # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return "Email already registered", 400  # Or render an error page

        # Create a new user
        new_user = User(name=name, email=email, phone_number=phone_number, password=password, role=role)
        
        # Add to the database
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('home'))  # Redirect to the home page or login page after successful registration
    
    return render_template('signup.html')  # Render the signup form

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    # Get all data to display
    users = User.query.all()
    services = Service.query.all()
    professionals = ProfessionalDetails.query.all()

    # Block a user (POST request)
    if request.method == 'POST':
        if 'block_user' in request.form:
            user_id = request.form['user_id']
            user = User.query.get(user_id)
            if user:
                user.is_blocked = True
                db.session.commit()
                return redirect(url_for('admin'))

        # Add a new service (POST request)
        if 'add_service' in request.form:
            service_name = request.form['service_name']
            service_base_price = request.form['service_base_price']
            new_service = Service(name=service_name, base_price=service_base_price)
            db.session.add(new_service)
            db.session.commit()
            return redirect(url_for('admin'))

        # Approve a professional (POST request)
        if 'approve_professional' in request.form:
            professional_id = request.form['professional_id']
            professional = ProfessionalDetails.query.get(professional_id)
            if professional:
                professional.is_approved = True
                db.session.commit()
                return redirect(url_for('admin'))

    return render_template('admin.html', users=users, services=services, professionals=professionals)



# Run the app
if __name__ == "__main__":
    app.run(debug=True)