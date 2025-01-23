from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import pymysql
import os
import qrcode
import json  # Import the json module
from pymysql.cursors import DictCursor  # استيراد DictCursor

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['QR_CODE_FOLDER'] = 'static/qr_codes'

# إنشاء مجلدات التحميل ورموز QR إذا لم تكن موجودة
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['QR_CODE_FOLDER']):
    os.makedirs(app.config['QR_CODE_FOLDER'])

# معلومات الاتصال بقاعدة البيانات
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'admin_panel'
}

# معلومات API
API_KEY = 'OVrcTPCnL0cbYY9UhVchJOnBV5cCxeVxCe1vlcQ7'
BASE_URL = 'https://api.nal.usda.gov/fdc/v1/foods/search'

# دالة لاسترجاع القيم الغذائية من API
def get_nutritional_info(food_name, quantity):
    params = {
        'api_key': API_KEY,
        'query': food_name,
        'pageSize': 1
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict):  # تأكد أن البيانات هي قاموس
            foods = data.get('foods', [])
            if foods:
                food = foods[0]
                nutrients = food.get('foodNutrients', [])
                try:
                    nutritional_info = {
                        'calories': next((n['value'] for n in nutrients if n['nutrientName'] == 'Energy'), 0) * (quantity / 100),
                        'protein': next((n['value'] for n in nutrients if n['nutrientName'] == 'Protein'), 0) * (quantity / 100),
                        'fat': next((n['value'] for n in nutrients if n['nutrientName'] == 'Total lipid (fat)'), 0) * (quantity / 100),
                        'carbohydrates': next((n['value'] for n in nutrients if n['nutrientName'] == 'Carbohydrate, by difference'), 0) * (quantity / 100),
                        'default_quantity': 100  # الكمية الافتراضية
                    }
                    return nutritional_info
                except (KeyError, TypeError) as e:
                    print(f"Error processing nutritional info: {e}")
                    return None
    return None

# دالة لتوليد رمز QR
def generate_qr_code(data, meal_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    # تأكد من ترميز البيانات باستخدام UTF-8
    qr.add_data(data.encode('utf-8'))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qr_code_path = os.path.join(app.config['QR_CODE_FOLDER'], f'meal_{meal_id}.png')
    img.save(qr_code_path)
    return qr_code_path

# صفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')

# API لتحديث القيم الغذائية
@app.route('/get_nutrition', methods=['POST'])
def get_nutrition():
    data = request.json
    ingredient_name = data.get('ingredient_name')
    quantity = float(data.get('quantity', 100))  # الكمية الافتراضية 100 جرام
    nutritional_info = get_nutritional_info(ingredient_name, quantity)
    return jsonify(nutritional_info)

# API لحفظ الوجبة
@app.route('/save_meal', methods=['POST'])
def save_meal():
    meal_name_ar = request.form.get('meal_name_ar')
    meal_name_en = request.form.get('meal_name_en')
    meal_category = request.form.get('meal_category')
    meal_image = request.files.get('meal_image')
    ingredients = request.form.get('ingredients')

    # Parse the ingredients string into a list of dictionaries
    try:
        ingredients = json.loads(ingredients)
    except json.JSONDecodeError as e:
        return jsonify({"status": "error", "message": f"Invalid ingredients format: {e}"})

    if meal_image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], meal_image.filename)
        meal_image.save(image_path)
    else:
        image_path = None

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # إدخال الوجبة في قاعدة البيانات
            sql = """
            INSERT INTO meals (meal_name_ar, meal_name_en, meal_category, meal_image, ingredient_name, quantity, calories, protein, fat, carbohydrates)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            for ingredient in ingredients:
                cursor.execute(sql, (
                    meal_name_ar, meal_name_en, meal_category, image_path, ingredient['name'], ingredient['quantity'],
                    ingredient['calories'], ingredient['protein'],
                    ingredient['fat'], ingredient['carbohydrates']
                ))
            meal_id = cursor.lastrowid  # الحصول على الـ ID الخاص بالوجبة
        connection.commit()

        # توليد رمز QR
        qr_data = f"""
        اسم الوجبة (عربي): {meal_name_ar}
        اسم الوجبة (إنجليزي): {meal_name_en}
        التصنيف: {meal_category}
        السعرات الحرارية: {sum(float(i['calories']) for i in ingredients):.2f}
        البروتين: {sum(float(i['protein']) for i in ingredients):.2f} جرام
        الدهون: {sum(float(i['fat']) for i in ingredients):.2f} جرام
        الكربوهيدرات: {sum(float(i['carbohydrates']) for i in ingredients):.2f} جرام
        """
        qr_code_path = generate_qr_code(qr_data, meal_id)
        qr_code_url = f"/{qr_code_path}"

        return jsonify({"status": "success", "message": "تم حفظ الوجبة بنجاح!", "qr_code_url": qr_code_url})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        connection.close()

# عرض الوجبات المحفوظة
@app.route('/meals')
def meals():
    connection = pymysql.connect(**db_config, cursorclass=DictCursor)  # استخدام DictCursor
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM meals"
            cursor.execute(sql)
            meals = cursor.fetchall()  # البيانات الآن ستكون قواميس
    finally:
        connection.close()
    return render_template('meals.html', meals=meals)

# حذف وجبة
@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM meals WHERE id = %s"
            cursor.execute(sql, (meal_id,))
        connection.commit()
    finally:
        connection.close()
    return redirect(url_for('meals'))

if __name__ == '__main__':
    app.run(debug=True)