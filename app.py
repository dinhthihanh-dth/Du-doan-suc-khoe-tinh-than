
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import numpy as np
import os
import pickle

# Load model machine learning 
model = pickle.load(open('model.pkl', 'rb'))

# Khởi tạo Flask app và cấu hình SQLite
app = Flask(__name__, template_folder='template')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'

# SQLAlchemy setup
db = SQLAlchemy(app)

# Định nghĩa model User cho SQLAlchemy
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# Định nghĩa model PredictionResult cho SQLAlchemy
class PredictionResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID tự tăng
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # ID của người dùng từ bảng User
    input_data = db.Column(db.String, nullable=False)  # Dữ liệu đầu vào
    prediction_result = db.Column(db.String, nullable=False)  # Kết quả dự đoán
    probability = db.Column(db.Float, nullable=False)  # Xác suất dự đoán

# Tạo bảng dữ liệu SQLite
with app.app_context():
    db.create_all()

# Route trang chủ
@app.route('/')
def home():
    return render_template("home.html")

# Route trang đăng ký
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match. Please try again.')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        if existing_user or existing_email:
            flash('Username or Email already exists. Please choose a different one.')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# Route trang đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            session['logged_in'] = True
            session['user_id'] = user.id
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.')

    return render_template('login.html')

# Route trang dashboard
@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session and session['logged_in']:
        return render_template('dashboard.html')
    else:
        flash('You need to log in first.')
        return redirect(url_for('login'))

# Route dự đoán
@app.route('/predict', methods=['POST', 'GET'])
def predict():
    if request.method == 'POST':
        try:
            int_features = [int(x) for x in request.form.values()]
            final = [np.array(int_features)]
            prediction = model.predict_proba(final)
            output = '{0:.{1}f}'.format(prediction[0][1], 2)

            if float(output) > 0.5:
                prediction_text = f'Bạn cần điều trị bệnh tâm thần. Xác suất mắc bệnh là {output}'
            else:
                prediction_text = f'Bạn không cần điều trị bệnh tâm thần. Xác suất mắc bệnh là {output}'

            # Lưu kết quả vào database
            user_id = session.get('user_id', None)
            if user_id:
                new_prediction = PredictionResult(
                    user_id=user_id,
                    input_data=str(int_features),
                    prediction_result=prediction_text,
                    probability=float(output)
                )
                db.session.add(new_prediction)
                db.session.commit()

            # Chuyển đến trang kết quả
            return render_template('result.html', pred=prediction_text)
        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('predict'))

    return render_template('predict.html')
# Route lịch sử dự đoán
@app.route('/history')
def history():
    if 'logged_in' in session and session['logged_in']:
        user_id = session.get('user_id')
        # Đảm bảo truy vấn trùng khớp cột user_id đúng
        predictions = PredictionResult.query.filter_by(user_id=user_id).all()
        return render_template('history.html', predictions=predictions)
    else:
        flash('You need to log in first.')
        return redirect(url_for('login'))
    
# Route trang tiếp theo, trang lời khuyên
@app.route('/next_page')
def next_page():
    return render_template('next_page.html')


# Chạy ứng dụng
if __name__ == '__main__':
    app.run(debug=True)
