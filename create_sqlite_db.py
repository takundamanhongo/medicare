"""
Convert MySQL schema to SQLite database
Run this to create hospitalmanagementsystem_final.db from your MySQL schema
"""

import sqlite3
import os

# SQLite database file
DB_PATH = "hospitalmanagementsystem_final.db"

# Your MySQL schema converted to SQLite
schema_sqlite = """
-- =====================================================
-- HOSPITAL MANAGEMENT SYSTEM - SQLITE VERSION
-- Based on your MySQL schema
-- =====================================================

-- Drop tables if they exist (in reverse order)
DROP TABLE IF EXISTS invoice_line_item;
DROP TABLE IF EXISTS invoice;
DROP TABLE IF EXISTS prescription;
DROP TABLE IF EXISTS patient_lab_test;
DROP TABLE IF EXISTS admission;
DROP TABLE IF EXISTS appointment;
DROP TABLE IF EXISTS medical_record;
DROP TABLE IF EXISTS nurse;
DROP TABLE IF EXISTS doctor;
DROP TABLE IF EXISTS patient;
DROP TABLE IF EXISTS person;
DROP TABLE IF EXISTS medicine;
DROP TABLE IF EXISTS lab_test_catalog;
DROP TABLE IF EXISTS room;
DROP TABLE IF EXISTS ward;
DROP TABLE IF EXISTS department;

-- Department Table
CREATE TABLE department (
    dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name VARCHAR(100) NOT NULL UNIQUE,
    floor_number INT,
    phone_extension VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ward Table
CREATE TABLE ward (
    ward_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_ward_id INT NULL,
    ward_name VARCHAR(100) NOT NULL,
    ward_type VARCHAR(20) DEFAULT 'General',
    total_beds INT CHECK (total_beds > 0),
    available_beds INT CHECK (available_beds >= 0),
    FOREIGN KEY (parent_ward_id) REFERENCES ward(ward_id) ON DELETE SET NULL
);

-- Room Table
CREATE TABLE room (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ward_id INT NOT NULL,
    room_number VARCHAR(10) NOT NULL,
    room_name VARCHAR(50),
    room_type VARCHAR(20) DEFAULT 'General',
    bed_capacity INT CHECK (bed_capacity > 0),
    dept_id INT NOT NULL,
    is_available BOOLEAN DEFAULT 1,
    UNIQUE(ward_id, room_number),
    FOREIGN KEY (ward_id) REFERENCES ward(ward_id) ON DELETE CASCADE,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE CASCADE
);

-- Person Table
CREATE TABLE person (
    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    id_number VARCHAR(20) UNIQUE,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    physical_address TEXT,
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(15),
    blood_type VARCHAR(5),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Patient Table
CREATE TABLE patient (
    person_id INTEGER PRIMARY KEY,
    marital_status VARCHAR(20) DEFAULT 'Single',
    occupation VARCHAR(100),
    insurance_provider VARCHAR(100),
    insurance_number VARCHAR(50),
    primary_physician_id INT,
    registration_fee_paid BOOLEAN DEFAULT 0,
    FOREIGN KEY (person_id) REFERENCES person(person_id) ON DELETE CASCADE
);

-- Doctor Table
CREATE TABLE doctor (
    person_id INTEGER PRIMARY KEY,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    dept_id INT NOT NULL,
    qualification TEXT,
    years_experience INT DEFAULT 0,
    consultation_fee DECIMAL(10,2) DEFAULT 0.00,
    available_from TIME DEFAULT '08:00:00',
    available_to TIME DEFAULT '17:00:00',
    max_appointments_per_day INT DEFAULT 20,
    FOREIGN KEY (person_id) REFERENCES person(person_id) ON DELETE CASCADE,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE CASCADE
);

-- Nurse Table
CREATE TABLE nurse (
    person_id INTEGER PRIMARY KEY,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    qualification VARCHAR(100) NOT NULL,
    ward_id INT NOT NULL,
    shift VARCHAR(20) DEFAULT 'Rotating',
    supervisor_id INT NULL,
    FOREIGN KEY (person_id) REFERENCES person(person_id) ON DELETE CASCADE,
    FOREIGN KEY (ward_id) REFERENCES ward(ward_id) ON DELETE CASCADE,
    FOREIGN KEY (supervisor_id) REFERENCES nurse(person_id) ON DELETE SET NULL
);

-- Appointment Table
CREATE TABLE appointment (
    appt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appt_datetime DATETIME NOT NULL,
    appt_type VARCHAR(20) DEFAULT 'Consultation',
    status VARCHAR(20) DEFAULT 'Scheduled',
    reason TEXT,
    notes TEXT,
    duration_minutes INT DEFAULT 30,
    check_in_time DATETIME NULL,
    check_out_time DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doctor_id, appt_datetime),
    FOREIGN KEY (patient_id) REFERENCES patient(person_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctor(person_id) ON DELETE CASCADE
);

-- Medical Record Table
CREATE TABLE medical_record (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    visit_date DATE NOT NULL,
    diagnosis TEXT NOT NULL,
    treatment TEXT,
    symptoms TEXT,
    blood_pressure_systolic INT,
    blood_pressure_diastolic INT,
    heart_rate INT,
    temperature DECIMAL(3,1),
    weight_kg DECIMAL(5,2),
    height_cm INT,
    notes TEXT,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(person_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctor(person_id) ON DELETE CASCADE
);

-- Medicine Table
CREATE TABLE medicine (
    medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_name VARCHAR(100) NOT NULL,
    generic_name VARCHAR(100),
    category VARCHAR(50),
    manufacturer VARCHAR(100),
    dosage_form VARCHAR(20) DEFAULT 'Tablet',
    strength VARCHAR(50),
    unit_price DECIMAL(10,2) NOT NULL,
    quantity_in_stock INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    requires_prescription BOOLEAN DEFAULT 1,
    expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lab Test Catalog
CREATE TABLE lab_test_catalog (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name VARCHAR(100) NOT NULL UNIQUE,
    test_category VARCHAR(20) NOT NULL,
    description TEXT,
    preparation_instructions TEXT,
    typical_duration_minutes INT,
    cost DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT 1
);

-- Patient Lab Tests
CREATE TABLE patient_lab_test (
    test_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    test_id INT NOT NULL,
    order_date DATETIME NOT NULL,
    scheduled_date DATE,
    status VARCHAR(20) DEFAULT 'Ordered',
    result_date DATE,
    result_value TEXT,
    result_units VARCHAR(50),
    reference_range VARCHAR(100),
    is_abnormal BOOLEAN DEFAULT 0,
    notes TEXT,
    performed_by INT NULL,
    FOREIGN KEY (patient_id) REFERENCES patient(person_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctor(person_id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES lab_test_catalog(test_id) ON DELETE CASCADE
);

-- Prescription Table
CREATE TABLE prescription (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INT NOT NULL,
    medicine_id INT NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    frequency VARCHAR(50),
    duration_days INT,
    quantity_prescribed INT,
    instructions TEXT,
    prescribed_date DATE NOT NULL,
    is_dispensed BOOLEAN DEFAULT 0,
    dispensed_date DATE NULL,
    dispensed_by INT NULL,
    FOREIGN KEY (record_id) REFERENCES medical_record(record_id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicine(medicine_id) ON DELETE CASCADE,
    FOREIGN KEY (dispensed_by) REFERENCES nurse(person_id) ON DELETE SET NULL
);

-- Invoice Table
CREATE TABLE invoice (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal DECIMAL(10,2) DEFAULT 0.00,
    tax DECIMAL(10,2) DEFAULT 0.00,
    discount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(10,2) DEFAULT 0.00,
    amount_paid DECIMAL(10,2) DEFAULT 0.00,
    payment_status VARCHAR(20) DEFAULT 'Pending',
    payment_method VARCHAR(20) NULL,
    payment_date DATETIME NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(person_id) ON DELETE CASCADE
);

-- Invoice Line Items
CREATE TABLE invoice_line_item (
    line_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INT NOT NULL,
    item_type VARCHAR(20) NOT NULL,
    item_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    quantity INT DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id) ON DELETE CASCADE
);

-- Admission Table
CREATE TABLE admission (
    admission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INT NOT NULL,
    room_id INT NOT NULL,
    admission_datetime DATETIME NOT NULL,
    expected_discharge_datetime DATETIME,
    actual_discharge_datetime DATETIME NULL,
    admission_reason TEXT,
    admitting_doctor_id INT NOT NULL,
    discharge_doctor_id INT NULL,
    discharge_notes TEXT,
    status VARCHAR(20) DEFAULT 'Admitted',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(person_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(room_id) ON DELETE CASCADE,
    FOREIGN KEY (admitting_doctor_id) REFERENCES doctor(person_id) ON DELETE CASCADE,
    FOREIGN KEY (discharge_doctor_id) REFERENCES doctor(person_id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_person_name ON person(last_name, first_name);
CREATE INDEX idx_person_phone ON person(phone_number);
CREATE INDEX idx_doctor_specialization ON doctor(specialization);
CREATE INDEX idx_appt_datetime ON appointment(appt_datetime);
CREATE INDEX idx_appt_status ON appointment(status);
CREATE INDEX idx_record_patient ON medical_record(patient_id);
CREATE INDEX idx_record_date ON medical_record(visit_date);
CREATE INDEX idx_invoice_patient ON invoice(patient_id);
CREATE INDEX idx_invoice_status ON invoice(payment_status);
CREATE INDEX idx_admission_patient ON admission(patient_id);
CREATE INDEX idx_admission_status ON admission(status);

-- Enable foreign keys
PRAGMA foreign_keys = ON;
"""

# Create the database
print("="*60)
print("Creating SQLite database from MySQL schema")
print("="*60)

# Remove existing database if present
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"✓ Removed existing {DB_PATH}")

# Create new database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Execute schema
try:
    cursor.executescript(schema_sqlite)
    print("✓ Tables created successfully")
except Exception as e:
    print(f"✗ Error: {e}")

# Verify tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print("\n📊 Tables created:")
for table in tables:
    print(f"  - {table[0]}")

conn.close()
print(f"\n✅ Database saved to: {DB_PATH}")
print("="*60)