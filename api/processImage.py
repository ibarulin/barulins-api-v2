# --- Финальная, рабочая версия ---

# 1. Добавляем "кузов" - сам фреймворк Flask
from flask import Flask, request, jsonify
from flask_cors import CORS

# 2. Копируем все ваши идеальные "детали двигателя"
import os
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFilter, ImageEnhancer
import re
import google.generativeai as genai

# 3. Создаем саму "машину"
app = Flask(__name__)
# И открываем для нее все двери
CORS(app)

# 4. Вся ваша логика остается абсолютно без изменений
genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-pro')

def base64_to_image(base64_str):
    try:
        if ',' in base64_str:
            _, data = base64_str.split(',', 1)
        else:
            data = base64_str
        img_data = base64.b64decode(data)
        return Image.open(BytesIO(img_data))
    except Exception as e:
        raise ValueError(f"Ошибка декодирования Base64: {str(e)}")

def parse_gemini_response(response_text):
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return {'x': int(data.get('x', 960)), 'y': int(data.get('y', 324)), 'scale': float(data.get('scale', 0.8)), 'rotation': float(data.get('rotation', 0)), 'wall_height': int(data.get('wall_height', 600))}
        return {'x': 960, 'y': 324, 'scale': 0.8, 'rotation': 0, 'wall_height': 600}
    except:
        return {'x': 960, 'y': 324, 'scale': 0.8, 'rotation': 0, 'wall_height': 600}

def composite_images(interior, artwork, placement):
    art_width, art_height = artwork.size
    new_width = int(art_width * placement['scale'])
    new_height = int(art_height * placement['scale'])
    artwork = artwork.resize((new_width, new_height), Image.Resampling.LANCZOS)
    if placement['rotation'] != 0:
        artwork = artwork.rotate(placement['rotation'], expand=True)
    interior = interior.copy().convert('RGBA')
    x, y = placement['x'] - new_width // 2, placement['y'] - new_height // 2
    artwork_layer = Image.new('RGBA', interior.size)
    artwork_layer.paste(artwork, (x, y))
    interior = Image.alpha_composite(interior, artwork_layer)
    shadow = Image.new('RGBA', interior.size)
    draw = ImageDraw.Draw(shadow)
    draw.rectangle([x+5, y+5, x+new_width+5, y+new_height+5], fill=(0,0,0,50))
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    final_img = Image.alpha_composite(interior, shadow)
    return final_img.convert('RGB')

# 5. Создаем "дверь" в нашу машину по правильному адресу
@app.route('/api/process_image', methods=['POST'])
def handler():
    try:
        # Используем встроенный в "кузов" способ получить данные
        data = request.get_json()
        if not data or 'interiorImage' not in data or 'artworkImage' not in data:
            return jsonify({'error': 'Отсутствуют обязательные поля'}), 400
        
        # Вся ваша логика обработки остается здесь
        interior_img = base64_to_image(data['interiorImage'])
        artwork_img = base64_to_image(data['artworkImage'])
        
        prompt = "Ты — ассистент по дизайну. Проанализируй фото интерьера и верни ТОЛЬКО JSON с координатами для размещения картины: {\"x\": center_x, \"y\": top_y, \"scale\": 0.8, \"rotation\": 0, \"wall_height\": 600}. Размер интерьера 1920x1080."
        
        response = model.generate_content([prompt, interior_img, artwork_img])
        placement = parse_gemini_response(response.text)
        
        final_img = composite_images(interior_img, artwork_img, placement)
        
        buffered = BytesIO()
        final_img.save(buffered, format="PNG")
        final_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Используем встроенный в "кузов" способ отправить ответ
        return jsonify({'finalImage': final_b64})
    
    except Exception as e:
        print(f"!!! INTERNAL SERVER ERROR: {e}")
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500
