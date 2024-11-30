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
        flash ('Service deleted successfully.', 'success')
        return redirect(url_for("admin_dashboard"))
        # return render_template("admin_dashboard.html",message=message)
  
    flash("Service Not Found", "danger")    
    return render_template("admin_dashboard.html")

# Approve Service Professional
@app.route('/admin/approve_professional/<int:pro_id>', methods=['POST'])
def approve_professional(pro_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    professional = ProfessionalDetails.query.get(pro_id)
    if professional:
        professional.is_approved = True
        db.session.commit()
        flash("Professional approved.", "sucsess")
        return redirect(url_for("admin_dashboard"))
    flash("Professional not found.", "danger")
    return redirect(url_for("admin_dashboard"))

# Block User
@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
def block_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    user = User.query.get(user_id)
    if user:
        user.is_blocked = True
        db.session.commit()
        flash("User Blocked sucessfully" , "success")
        return redirect(url_for("admin_dashboard"))
    flash("User Not Found", "warning")
    return redirect(url_for("admin_dashboard"))

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
    flash("Service added successfully.", "sucsses")
    return redirect(url_for("admin_dashboard"))


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
            # Get service type from the dropdown
            service_type = request.form['service_type']

            # Create a new ProfessionalDetails entry
            professional_details = ProfessionalDetails(
                user=new_user,
                service_type=service_type,
                years_experience=request.form['experience']
            )

            db.session.add(professional_details)

        db.session.add(new_user)
        db.session.commit()
        message = {"type":"success","body":"User Created Successfully"}
        session['logged_in']=True
        session['user_id'] = new_user.id
        flash("User logged successfully", "success")
        return render_template('home.html',message=message)
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if password== user.password:  # Validate password securely
            session['logged_in'] = True
            session['user_id'] = user.id  # Save user_id in the session
            
            if user.role == "admin":
                session['admin_logged_in'] = True
                return redirect(url_for('admin_dashboard'))
            elif user.role == "serviceProvider":
                return redirect(url_for('professional_dashboard'))
            else:
                return redirect(url_for('home'))  # Redirect customers to the home page
        else:
            flash("Invalid credentials. Please try again.", "danger")
    return render_template('home.html')


from flask import jsonify

@app.route('/book_service', methods=['POST'])
def book_service():
    if not session.get('logged_in'):
        flash("You must be logged in to book a service.", "danger")
        return redirect(url_for('home'))

    # Get data from the form
    service_id = request.form.get('service_id')
    user_id = session.get('user_id')  # Assume user_id is stored in the session

    # Check if the service exists
    service = Service.query.get(service_id)
    if not service:
        return flash("Service not found.", "danger")

    # Create a new service request
    new_request = ServiceRequest(
        service_id=service_id,
        customer_id=user_id,
        service_status='requested',  # Initial status
        remarks=''  # Add remarks if needed
    )

    db.session.add(new_request)
    db.session.commit()
    flash("Service booked successfully!", "success")
    return redirect(url_for('home'))

@app.route('/customer_history')
def customer_history():
    if not session.get('logged_in'):
        flash("You must be logged in to view your service history.", "danger")
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user or user.role != 'customer':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))

    # Fetch all service requests for the logged-in customer
    service_requests = ServiceRequest.query.filter_by(customer_id=user_id).all()

    return render_template('customer_history.html', service_requests=service_requests)


@app.route('/professional_dashboard')
def professional_dashboard():
    if not session.get('logged_in'):
        flash("You must be logged in to access the dashboard.", "danger")
        return redirect(url_for('login'))

    # Ensure user_id exists in the session
    user_id = session.get('user_id')
    if not user_id:
        flash("Session expired or invalid. Please log in again.", "danger")
        return redirect(url_for('login'))

    # Fetch the logged-in user
    user = User.query.get(user_id)
    if not user:
        flash("User not found. Please log in again.", "danger")
        return redirect(url_for('login'))

    # Ensure the user is a service provider
    if user.role != 'serviceProvider':
        flash("Unauthorized access to professional dashboard.", "danger")
        return redirect(url_for('home'))

    # Get the service professional's service type
    professional_details = ProfessionalDetails.query.filter_by(user_id=user_id).first()
    if not professional_details:
        flash("Professional details not found. Please contact support.", "danger")
        return redirect(url_for('home'))

    # Fetch all service requests matching the professional's service type and 'requested' status
    service_requests = ServiceRequest.query.join(Service).filter(
        Service.type_of_service == professional_details.service_type,
        ServiceRequest.service_status == 'requested'
    ).all()

    return render_template('professional_dashboard.html', service_requests=service_requests)

@app.route('/accept_service_request/<int:request_id>', methods=['POST'])
def accept_service_request(request_id):
    # Check if the professional is logged in
    if not session.get('logged_in'):
        flash("You must be logged in to accept a service request.", "danger")
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    # Ensure the user is a service provider
    if not user or user.role != 'serviceProvider':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))

    # Fetch the service request
    service_request = ServiceRequest.query.get(request_id)
    if not service_request:
        flash("Service request not found.", "danger")
        return redirect(url_for('professional_dashboard'))

    # Check if the service type matches the professional's service type
    professional_details = ProfessionalDetails.query.filter_by(user_id=user_id).first()
    if not professional_details:
        flash("Professional details not found. Please contact support.", "danger")
        return redirect(url_for('professional_dashboard'))

    if service_request.service.type_of_service != professional_details.service_type:
        flash("This service request does not match your service type.", "warning")
        return redirect(url_for('professional_dashboard'))

    # Update the service request with the professional's ID and status
    service_request.professional_id = user_id
    service_request.service_status = 'assigned'
    db.session.commit()

    flash("Service request accepted successfully!", "success")
    return redirect(url_for('professional_dashboard'))


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




@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0",port="5000",debug=True)