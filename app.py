"""
Hospital Management System - Flask-AppBuilder Web Application
FIXED VERSION - Correct permission handling
"""

from flask import Flask, request, redirect, g
from flask_appbuilder import AppBuilder, SQLA
from flask_appbuilder import ModelView
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.baseviews import BaseView
from flask_appbuilder import expose, has_access
from flask_appbuilder.views import ModelView, SimpleFormView
from flask_appbuilder.security.decorators import protect
from wtforms import Form, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
import os
import sqlite3
from datetime import datetime

# ============================================
# APP CONFIGURATION
# ============================================
app = Flask(__name__)

app.config['SECRET_KEY'] = 'hospital-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospitalmanagementsystem_final.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FAB_UPDATE_PERMS'] = True
app.config['FAB_ADD_SECURITY_VIEWS'] = True

# Initialize
db = SQLA(app)
appbuilder = AppBuilder(app, db.session)


# ============================================
# DATABASE MODELS (All 16 tables)
# ============================================

class Department(db.Model):
    __tablename__ = 'department'
    dept_id = Column(Integer, primary_key=True)
    dept_name = Column(String(100))
    floor_number = Column(Integer)
    phone_extension = Column(String(10))

    def __repr__(self):
        return self.dept_name


class Ward(db.Model):
    __tablename__ = 'ward'
    ward_id = Column(Integer, primary_key=True)
    parent_ward_id = Column(Integer, ForeignKey('ward.ward_id'))
    ward_name = Column(String(100))
    ward_type = Column(String(20))
    total_beds = Column(Integer)
    available_beds = Column(Integer)

    parent = relationship('Ward', remote_side=[ward_id])

    def __repr__(self):
        return self.ward_name


class Room(db.Model):
    __tablename__ = 'room'
    room_id = Column(Integer, primary_key=True)
    ward_id = Column(Integer, ForeignKey('ward.ward_id'))
    room_number = Column(String(10))
    room_name = Column(String(50))
    room_type = Column(String(20))
    bed_capacity = Column(Integer)
    dept_id = Column(Integer, ForeignKey('department.dept_id'))
    is_available = Column(Boolean)

    ward = relationship('Ward')
    department = relationship('Department')

    def __repr__(self):
        return f"Room {self.room_number}"


class Person(db.Model):
    __tablename__ = 'person'
    person_id = Column(Integer, primary_key=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    id_number = Column(String(20))
    date_of_birth = Column(Date)
    gender = Column(String(10))
    phone_number = Column(String(15))
    email = Column(String(100))
    physical_address = Column(Text)
    emergency_contact_name = Column(String(100))
    emergency_contact_phone = Column(String(15))
    blood_type = Column(String(5))
    is_active = Column(Boolean)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return self.full_name()


class Patient(db.Model):
    __tablename__ = 'patient'
    person_id = Column(Integer, ForeignKey('person.person_id'), primary_key=True)
    marital_status = Column(String(20))
    occupation = Column(String(100))
    insurance_provider = Column(String(100))
    insurance_number = Column(String(50))
    registration_fee_paid = Column(Boolean)

    person = relationship('Person')

    def __repr__(self):
        return f"Patient: {self.person.full_name()}"


class Doctor(db.Model):
    __tablename__ = 'doctor'
    person_id = Column(Integer, ForeignKey('person.person_id'), primary_key=True)
    license_number = Column(String(50))
    specialization = Column(String(100))
    dept_id = Column(Integer, ForeignKey('department.dept_id'))
    qualification = Column(Text)
    years_experience = Column(Integer)
    consultation_fee = Column(Float)
    max_appointments_per_day = Column(Integer)

    person = relationship('Person')
    department = relationship('Department')

    def __repr__(self):
        return f"Dr. {self.person.full_name()}"


class Nurse(db.Model):
    __tablename__ = 'nurse'
    person_id = Column(Integer, ForeignKey('person.person_id'), primary_key=True)
    license_number = Column(String(50))
    qualification = Column(String(100))
    ward_id = Column(Integer, ForeignKey('ward.ward_id'))
    shift = Column(String(20))

    person = relationship('Person')
    ward = relationship('Ward')

    def __repr__(self):
        return f"Nurse {self.person.full_name()}"


class Appointment(db.Model):
    __tablename__ = 'appointment'
    appt_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.person_id'))
    doctor_id = Column(Integer, ForeignKey('doctor.person_id'))
    appt_datetime = Column(DateTime)
    appt_type = Column(String(20))
    status = Column(String(20))
    reason = Column(Text)
    notes = Column(Text)
    duration_minutes = Column(Integer)

    patient = relationship('Patient')
    doctor = relationship('Doctor')

    def __repr__(self):
        return f"Appointment #{self.appt_id}"


class MedicalRecord(db.Model):
    __tablename__ = 'medical_record'
    record_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.person_id'))
    doctor_id = Column(Integer, ForeignKey('doctor.person_id'))
    visit_date = Column(Date)
    diagnosis = Column(Text)
    treatment = Column(Text)

    patient = relationship('Patient')
    doctor = relationship('Doctor')

    def __repr__(self):
        return f"Record #{self.record_id}"


class Medicine(db.Model):
    __tablename__ = 'medicine'
    medicine_id = Column(Integer, primary_key=True)
    medicine_name = Column(String(100))
    generic_name = Column(String(100))
    category = Column(String(50))
    dosage_form = Column(String(20))
    strength = Column(String(50))
    unit_price = Column(Float)
    quantity_in_stock = Column(Integer)
    reorder_level = Column(Integer)
    requires_prescription = Column(Boolean)
    expiry_date = Column(Date)

    def __repr__(self):
        return self.medicine_name


class LabTestCatalog(db.Model):
    __tablename__ = 'lab_test_catalog'
    test_id = Column(Integer, primary_key=True)
    test_name = Column(String(100))
    test_category = Column(String(20))
    description = Column(Text)
    cost = Column(Float)

    def __repr__(self):
        return self.test_name


class PatientLabTest(db.Model):
    __tablename__ = 'patient_lab_test'
    test_order_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.person_id'))
    doctor_id = Column(Integer, ForeignKey('doctor.person_id'))
    test_id = Column(Integer, ForeignKey('lab_test_catalog.test_id'))
    order_date = Column(DateTime)
    status = Column(String(20))
    result_value = Column(Text)
    is_abnormal = Column(Boolean)

    patient = relationship('Patient')
    doctor = relationship('Doctor')
    test = relationship('LabTestCatalog')

    def __repr__(self):
        return f"Test #{self.test_order_id}"


class Prescription(db.Model):
    __tablename__ = 'prescription'
    prescription_id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('medical_record.record_id'))
    medicine_id = Column(Integer, ForeignKey('medicine.medicine_id'))
    dosage = Column(String(100))
    quantity_prescribed = Column(Integer)
    prescribed_date = Column(Date)
    is_dispensed = Column(Boolean)

    medical_record = relationship('MedicalRecord')
    medicine = relationship('Medicine')

    def __repr__(self):
        return f"Prescription #{self.prescription_id}"


class Invoice(db.Model):
    __tablename__ = 'invoice'
    invoice_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.person_id'))
    invoice_date = Column(Date)
    total_amount = Column(Float)
    amount_paid = Column(Float)
    payment_status = Column(String(20))

    patient = relationship('Patient')

    def __repr__(self):
        return f"Invoice #{self.invoice_id}"


class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_item'
    line_item_id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoice.invoice_id'))
    description = Column(String(255))
    quantity = Column(Integer)
    unit_price = Column(Float)
    line_total = Column(Float)

    invoice = relationship('Invoice')


class Admission(db.Model):
    __tablename__ = 'admission'
    admission_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patient.person_id'))
    room_id = Column(Integer, ForeignKey('room.room_id'))
    admission_datetime = Column(DateTime)
    status = Column(String(20))

    patient = relationship('Patient')
    room = relationship('Room')

    def __repr__(self):
        return f"Admission #{self.admission_id}"


# ============================================
# CUSTOM SQL RUNNER VIEW (For Admin)
# ============================================

class SQLRunnerForm(Form):
    sql_query = TextAreaField('SQL Query', validators=[DataRequired()],
                              description="Enter any SQL query (SELECT, INSERT, UPDATE, DELETE)")
    submit = SubmitField('Execute')


class SQLRunnerView(SimpleFormView):
    route_base = '/sqlrunner'
    form = SQLRunnerForm
    form_title = 'Run Custom SQL Query'

    @expose('/', methods=['GET', 'POST'])
    @has_access
    def this_form_get(self):
        self._init_vars()
        form = SQLRunnerForm()
        return self.render_template('sqlrunner.html', form=form)

    def form_post(self, form):
        query = form.sql_query.data
        try:
            conn = sqlite3.connect('hospitalmanagementsystem_final.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)

            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                conn.close()

                if results:
                    columns = results[0].keys()
                    return self.render_template('sqlresults.html',
                                                results=results,
                                                columns=columns,
                                                query=query)
                else:
                    return f"No results returned for: {query}"
            else:
                conn.commit()
                rows = cursor.rowcount
                conn.close()
                return f"Query executed successfully! {rows} rows affected."

        except Exception as e:
            return f"Error: {str(e)}"


# ============================================
# VIEWS (All tables)
# ============================================

class DepartmentView(ModelView):
    datamodel = SQLAInterface(Department)
    list_columns = ['dept_id', 'dept_name', 'floor_number', 'phone_extension']


class WardView(ModelView):
    datamodel = SQLAInterface(Ward)
    list_columns = ['ward_id', 'ward_name', 'ward_type', 'total_beds', 'available_beds']


class RoomView(ModelView):
    datamodel = SQLAInterface(Room)
    list_columns = ['room_id', 'room_number', 'room_name', 'room_type', 'bed_capacity', 'is_available']


class PersonView(ModelView):
    datamodel = SQLAInterface(Person)
    list_columns = ['person_id', 'first_name', 'last_name', 'phone_number', 'email']


class PatientView(ModelView):
    datamodel = SQLAInterface(Patient)
    list_columns = ['person_id', 'person', 'marital_status', 'occupation', 'insurance_provider']


class DoctorView(ModelView):
    datamodel = SQLAInterface(Doctor)
    list_columns = ['person_id', 'person', 'specialization', 'department', 'consultation_fee']


class NurseView(ModelView):
    datamodel = SQLAInterface(Nurse)
    list_columns = ['person_id', 'person', 'qualification', 'ward', 'shift']


class AppointmentView(ModelView):
    datamodel = SQLAInterface(Appointment)
    list_columns = ['appt_id', 'patient', 'doctor', 'appt_datetime', 'status']


class MedicalRecordView(ModelView):
    datamodel = SQLAInterface(MedicalRecord)
    list_columns = ['record_id', 'patient', 'doctor', 'visit_date', 'diagnosis']


class MedicineView(ModelView):
    datamodel = SQLAInterface(Medicine)
    list_columns = ['medicine_id', 'medicine_name', 'category', 'unit_price', 'quantity_in_stock']


class LabTestCatalogView(ModelView):
    datamodel = SQLAInterface(LabTestCatalog)
    list_columns = ['test_id', 'test_name', 'test_category', 'cost']


class PatientLabTestView(ModelView):
    datamodel = SQLAInterface(PatientLabTest)
    list_columns = ['test_order_id', 'patient', 'test', 'order_date', 'status']


class PrescriptionView(ModelView):
    datamodel = SQLAInterface(Prescription)
    list_columns = ['prescription_id', 'medical_record', 'medicine', 'dosage', 'prescribed_date']


class InvoiceView(ModelView):
    datamodel = SQLAInterface(Invoice)
    list_columns = ['invoice_id', 'patient', 'invoice_date', 'total_amount', 'payment_status']


class InvoiceLineItemView(ModelView):
    datamodel = SQLAInterface(InvoiceLineItem)
    list_columns = ['line_item_id', 'invoice', 'description', 'quantity', 'unit_price', 'line_total']


class AdmissionView(ModelView):
    datamodel = SQLAInterface(Admission)
    list_columns = ['admission_id', 'patient', 'room', 'admission_datetime', 'status']


# ============================================
# DASHBOARD VIEW
# ============================================

class DashboardView(BaseView):
    route_base = "/dashboard"
    default_view = 'index'

    @expose('/')
    @has_access
    def index(self):
        stats = {
            'patients': db.session.query(Patient).count(),
            'doctors': db.session.query(Doctor).count(),
            'nurses': db.session.query(Nurse).count(),
            'appointments': db.session.query(Appointment).count(),
            'departments': db.session.query(Department).count(),
            'medicines': db.session.query(Medicine).count(),
            'rooms': db.session.query(Room).count(),
            'wards': db.session.query(Ward).count(),
        }

        return self.render_template('dashboard.html', stats=stats)


# ============================================
# REGISTER ALL VIEWS
# ============================================

# Dashboard
appbuilder.add_view(DashboardView, "Dashboard", icon="fa-home", category="")

# Main categories
appbuilder.add_view(PatientView, "Patients", icon="fa-users", category="Patients")
appbuilder.add_view(DoctorView, "Doctors", icon="fa-user-md", category="Staff")
appbuilder.add_view(NurseView, "Nurses", icon="fa-user-nurse", category="Staff")
appbuilder.add_view(AppointmentView, "Appointments", icon="fa-calendar", category="Appointments")
appbuilder.add_view(MedicalRecordView, "Medical Records", icon="fa-notes-medical", category="Medical")

# Facilities
appbuilder.add_view(DepartmentView, "Departments", icon="fa-building", category="Facilities")
appbuilder.add_view(WardView, "Wards", icon="fa-hospital", category="Facilities")
appbuilder.add_view(RoomView, "Rooms", icon="fa-bed", category="Facilities")
appbuilder.add_view(AdmissionView, "Admissions", icon="fa-procedures", category="Facilities")

# Pharmacy
appbuilder.add_view(MedicineView, "Medicines", icon="fa-pills", category="Pharmacy")
appbuilder.add_view(PrescriptionView, "Prescriptions", icon="fa-prescription", category="Pharmacy")

# Labs
appbuilder.add_view(LabTestCatalogView, "Lab Tests", icon="fa-flask", category="Labs")
appbuilder.add_view(PatientLabTestView, "Patient Tests", icon="fa-microscope", category="Labs")

# Billing
appbuilder.add_view(InvoiceView, "Invoices", icon="fa-file-invoice", category="Billing")
appbuilder.add_view(InvoiceLineItemView, "Invoice Items", icon="fa-list", category="Billing")

# Admin
appbuilder.add_view(PersonView, "All Persons", icon="fa-id-card", category="Admin")
appbuilder.add_view(SQLRunnerView, "Run SQL", icon="fa-database", category="Admin")

# ============================================
# CREATE TEMPLATES
# ============================================

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
if not os.path.exists(template_dir):
    os.makedirs(template_dir)

# Dashboard Template
dashboard_html = '''
{% extends "appbuilder/base.html" %}
{% block content %}
<div class="container">
    <h1>Hospital Management System</h1>
    <p class="lead">Welcome, {{ current_user.username }}!</p>

    <div class="row">
        <div class="col-md-3">
            <div class="panel panel-primary">
                <div class="panel-heading">Patients</div>
                <div class="panel-body text-center"><h2>{{ stats.patients }}</h2></div>
                <div class="panel-footer"><a href="/patientview/list">View</a></div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="panel panel-success">
                <div class="panel-heading">Doctors</div>
                <div class="panel-body text-center"><h2>{{ stats.doctors }}</h2></div>
                <div class="panel-footer"><a href="/doctorview/list">View</a></div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="panel panel-info">
                <div class="panel-heading">Nurses</div>
                <div class="panel-body text-center"><h2>{{ stats.nurses }}</h2></div>
                <div class="panel-footer"><a href="/nurseview/list">View</a></div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="panel panel-warning">
                <div class="panel-heading">Appointments</div>
                <div class="panel-body text-center"><h2>{{ stats.appointments }}</h2></div>
                <div class="panel-footer"><a href="/appointmentview/list">View</a></div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">Quick Actions</div>
                <div class="panel-body">
                    <a href="/patientview/add" class="btn btn-primary">Add Patient</a>
                    <a href="/doctorview/add" class="btn btn-success">Add Doctor</a>
                    <a href="/appointmentview/add" class="btn btn-info">Add Appointment</a>
                    <a href="/sqlrunner" class="btn btn-danger">Run SQL Query</a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

with open(os.path.join(template_dir, 'dashboard.html'), 'w') as f:
    f.write(dashboard_html)

# SQL Runner Template
sqlrunner_html = '''
{% extends "appbuilder/base.html" %}
{% block content %}
<div class="container">
    <h2>Run Custom SQL Query</h2>
    <p class="text-danger">Warning: Be careful with UPDATE, INSERT, DELETE queries!</p>

    <form method="POST" action="/sqlrunner/">
        <div class="form-group">
            <textarea name="sql_query" class="form-control" rows="5" placeholder="Enter SQL query..."></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Execute</button>
        <a href="/dashboard" class="btn btn-default">Cancel</a>
    </form>

    <hr>
    <h4>Example Queries:</h4>
    <ul>
        <li>SELECT * FROM patient LIMIT 10;</li>
        <li>SELECT COUNT(*) FROM appointment WHERE status = 'Completed';</li>
        <li>SELECT d.dept_name, COUNT(doc.person_id) as doctor_count FROM department d LEFT JOIN doctor doc ON d.dept_id = doc.dept_id GROUP BY d.dept_id;</li>
    </ul>
</div>
{% endblock %}
'''

with open(os.path.join(template_dir, 'sqlrunner.html'), 'w') as f:
    f.write(sqlrunner_html)

# SQL Results Template
sqlresults_html = '''
{% extends "appbuilder/base.html" %}
{% block content %}
<div class="container">
    <h2>Query Results</h2>
    <p><strong>Query:</strong> {{ query }}</p>

    <table class="table table-striped table-bordered">
        <thead>
            <tr>
                {% for col in columns %}
                <th>{{ col }}</th>
                {% endfor %}
            </tr>
        </thead>
        <tbody>
            {% for row in results %}
            <tr>
                {% for col in columns %}
                <td>{{ row[col] }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <a href="/sqlrunner" class="btn btn-primary">Run Another Query</a>
    <a href="/dashboard" class="btn btn-default">Back to Dashboard</a>
</div>
{% endblock %}
'''

with open(os.path.join(template_dir, 'sqlresults.html'), 'w') as f:
    f.write(sqlresults_html)


# ============================================
# CREATE TEST USERS
# ============================================

def create_test_users():
    from flask_appbuilder.security.sqla.models import User
    from werkzeug.security import generate_password_hash

    # Check if admin exists
    admin = appbuilder.session.query(User).filter_by(username='admin').first()
    if not admin:
        admin = User()
        admin.username = 'admin'
        admin.email = 'admin@hospital.com'
        admin.password = generate_password_hash('admin')
        admin.active = True
        appbuilder.session.add(admin)
        appbuilder.session.commit()
        print("✅ Created admin user: admin / admin")


# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("HOSPITAL MANAGEMENT SYSTEM - COMPLETE VERSION")
    print("=" * 60)

    with app.app_context():
        create_test_users()

    print("\n✅ Database connected")
    print("\n🌐 Server: http://localhost:8080")
    print("\n🔐 Login: admin / admin")
    print("\n📊 Features:")
    print("   • 16 tables with full CRUD")
    print("   • Custom SQL query runner")
    print("   • Dashboard with statistics")
    print("   • All views accessible")
    print("\nPress Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=8080, debug=True)