from flask import Flask, render_template , request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_migrate import Migrate

#from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Create a Flask instance
app = Flask(__name__)
app.config['SECRET_KEY']= "SECRET_KEY"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'  # Using SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking for performance
db = SQLAlchemy(app)
admin= Admin(app)
migrate =Migrate(app , db)


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
    address= db.Column(db.String(100), nullable= True)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    service_type = db.Column(db.String(50), db.ForeignKey('service.type_of_service'), nullable=False)  # Specific service type
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
    professional_id = db.Column(db.Integer, db.ForeignKey('professional_details.user_id'), nullable=True)
    date_of_request = db.Column(db.DateTime, default=datetime.utcnow)
    date_of_completion = db.Column(db.DateTime, nullable=True)
    service_status = db.Column(db.String(20), default='requested')  # requested/assigned/closed
    remarks = db.Column(db.Text)

    # Relationships
    service = db.relationship('Service', back_populates='service_requests')
    customer = db.relationship('User', back_populates='customer_requests')
    professional = db.relationship('ProfessionalDetails', back_populates='service_requests')

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Service, db.session))
admin.add_view(ModelView(ProfessionalDetails, db.session))
admin.add_view(ModelView(ServiceRequest, db.session))

# Define the route for the root URL
@app.route('/')
def home():
    # Render the home.html template from the templates folder
    return render_template('home.html' , logged_in = session.get('logged_in' , False))

ADMIN_CREDENTIALS = {"username": "admin", "password": "admin123"}

# Admin Dashboard Route (Requires Login)
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Fetch data to display
    users = User.query.all()
    services = Service.query.all()
    pending_pros = ProfessionalDetails.query.filter_by(is_approved=False).all()

    return render_template('admin_dashboard.html', users=users, services=services, pending_pros=pending_pros)

# Delete a Service
@app.route('/admin/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    service = Service.query.get(service_id)
    if service:
        db.session.delete(service)
        db.session.commit()
        # message = {"type":"success","body":"Service deleted successfully."}
        return jsonify({"status": "success", "message": "Service deleted successfully."}), 200
        # return render_template("admin_dashboard.html",message=message)
  
    message = {"type":"danger","body":"Service not found."}
    # return render_template("admin_dashboard.html",message=message)
    return jsonify({"status": "error", "message": "Service not found."}), 404

# Approve Service Professional
@app.route('/admin/approve_professional/<int:pro_id>', methods=['POST'])
def approve_professional(pro_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    professional = ProfessionalDetails.query.get(pro_id)
    if professional:
        professional.is_approved = True
        db.session.commit()
        return jsonify({"status": "success", "message": "Professional approved."}), 200
    return jsonify({"status": "error", "message": "Professional not found."}), 404

# Block User
@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
def block_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    user = User.query.get(user_id)
    if user:
        user.is_blocked = True
        db.session.commit()
        return jsonify({"status": "success", "message": "User blocked."}), 200
    return jsonify({"status": "error", "message": "User not found."}), 404

# Add New Service
# Add New Service
@app.route('/admin/add_service', methods=['POST'])
def add_service():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    service_name = request.form['name']
    service_type = request.form['type_of_service']
    base_price = request.form['base_price']
    description = request.form['description']
    time_required = request.form['time_required']

    new_service = Service(
        name=service_name,
        type_of_service=service_type,  # Save the selected service type
        base_price=base_price,
        description=description,
        time_required=time_required
    )
    db.session.add(new_service)
    db.session.commit()

    return jsonify({"status": "success", "message": "Service added successfully."}), 201


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        role = request.form['role']
        password = request.form['create_password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return "Passwords do not match", 400
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered", "error")
        
        new_user = User(name=name, email=email, phone_number=phone_number, password=password, role=role)

        if role == "customer":
            new_user.address = request.form['address']
        elif role == "serviceProvider":
            new_user.service_type = request.form['service_type']
            # Creating a new professional record
            professional_details = ProfessionalDetails(user=new_user)
            db.session.add(professional_details)
            db.session.commit()
            new_user.professional_details = professional_details

        session['logged_in'] = True
        db.session.add(new_user)
        db.session.commit()
        message = {"type":"success","body":"User Created Successfully"}
        return render_template('home.html',message=message)
    return render_template('home.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            # Login successful, redirect to the home page or dashboard
            if user.role == "admin":
                session['admin_logged_in'] = True
                return redirect(url_for('admin_dashboard'))
            session['logged_in'] = True
            message = {"type":"success","body":"Login Successful"}
            return render_template('home.html',message=message)
            
        else:
            # Login failed, display an error message
            pass

from flask import jsonify

@app.route('/api/book_service', methods=['POST'])
def book_service_api():
    # Check if the user is logged in
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "You must be logged in to book a service."}), 401
    
    # Get service ID and user ID from the request
    service_id = request.json.get('service_id')
    user_id = session.get('user_id')  # Assume user ID is stored in the session

    if not service_id:
        return jsonify({"status": "error", "message": "Service ID is required."}), 400
    
    # Check if the service exists
    service = Service.query.get(service_id)
    if not service:
        return jsonify({"status": "error", "message": "Service not found."}), 404

    # Create a new service request
    new_request = ServiceRequest(
        service_id=service_id,
        customer_id=user_id,
        service_status='requested'
    )
    db.session.add(new_request)
    db.session.commit()

    return jsonify({"status": "success", "message": "Booking successful!"}), 200



@app.route('/cleaning_services')
def cleaning_services():
    # Query services with type_of_service = "cleaning services"
    cleaning_services = Service.query.filter_by(type_of_service="cleaning services").all()
    return render_template('cleaning_services.html', services=cleaning_services)
@app.route('/beauty_services')
def beauty_services():
    beauty_services = Service.query.filter_by(type_of_service="beauty services").all()
    return render_template('beauty_services.html', services=beauty_services)

@app.route('/handyman_services')
def handyman_services():
    handyman_services = Service.query.filter_by(type_of_service="handyman services").all()
    return render_template('handyman_services.html', services=handyman_services)

@app.route('/security_services')
def security_services():
    security_services = Service.query.filter_by(type_of_service="security services").all()
    return render_template('security_services.html', services=security_services)

@app.route('/pet_care_services')
def pet_care_services():
    pet_care_services = Service.query.filter_by(type_of_service="pet-care services").all()
    return render_template('pet-care_services.html', services=pet_care_services)




@app.route('/logout')
def logout():
    session.pop('logged_in')

    return redirect(url_for('home'))


# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0",port="5000",debug=True)