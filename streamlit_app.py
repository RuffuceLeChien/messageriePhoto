import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import json
import os
from datetime import datetime
import base64
import time
import requests

# Tentative d'import de Gemini (optionnel)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Configuration de la page
st.set_page_config(
    page_title="💕 Messagerie",
    page_icon="💕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé pour une interface moderne et élégante
st.markdown("""
<style>
    /* Cache le header et footer Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Style général */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Conteneur principal */
    .main .block-container {
        max-width: 800px;
        padding: 1rem 2rem;
    }
    
    /* Style de la zone de discussion */
    .chat-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        margin-bottom: 20px;
        max-height: 70vh;
        overflow-y: auto;
    }
    
    /* Messages admin (à droite) */
    .message-admin {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
        animation: slideInRight 0.3s ease;
    }
    
    .message-admin .message-content {
        max-width: 70%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px 20px 5px 20px;
        padding: 5px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Messages user (à gauche) */
    .message-user {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 15px;
        animation: slideInLeft 0.3s ease;
    }
    
    .message-user .message-content {
        max-width: 70%;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 20px 20px 20px 5px;
        padding: 5px;
        box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3);
    }
    
    .message-timestamp {
        font-size: 11px;
        color: rgba(255,255,255,0.8);
        margin: 5px 10px;
        font-weight: 500;
    }
    
    .message-image {
        border-radius: 15px;
        width: 100%;
        display: block;
    }
    
    /* Boutons d'action */
    .message-actions {
        display: flex;
        gap: 5px;
        margin-top: 5px;
        padding: 0 5px;
    }
    
    /* Zone d'envoi */
    .send-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 -5px 20px rgba(0,0,0,0.1);
        position: sticky;
        bottom: 0;
    }
    
    /* Animations */
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Boutons stylés */
    .stButton button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    /* Input stylé */
    .stTextInput input {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        padding: 12px 15px;
        font-size: 16px;
    }
    
    .stTextInput input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Scrollbar personnalisée */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0,0,0,0.05);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Configuration GitHub
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "") if hasattr(st, 'secrets') else ""
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "") if hasattr(st, 'secrets') else ""
GITHUB_BRANCH = "main"
DATA_FILE = "messages_data.json"

# Configuration Gemini
GEMINI_API_KEY = ""
if GEMINI_AVAILABLE:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, 'secrets') else ""
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)

def github_get_file(file_path):
    """Récupère un fichier depuis GitHub"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            return {
                'content': base64.b64decode(content['content']).decode('utf-8'),
                'sha': content['sha']
            }
    except:
        pass
    return None

def github_update_file(file_path, content, sha=None, message="Update data"):
    """Met à jour un fichier sur GitHub"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": GITHUB_BRANCH
    }
    
    if sha:
        data["sha"] = sha
    
    try:
        response = requests.put(url, headers=headers, json=data)
        return response.status_code in [200, 201]
    except:
        return False

def load_messages():
    """Charge les messages depuis GitHub"""
    file_data = github_get_file(DATA_FILE)
    
    if file_data:
        try:
            data = json.loads(file_data['content'])
            messages = []
            for msg in data.get('messages', []):
                if 'image_with_text_b64' in msg:
                    msg['image_with_text'] = Image.open(io.BytesIO(base64.b64decode(msg['image_with_text_b64'])))
                if 'original_image_b64' in msg:
                    msg['original_image'] = Image.open(io.BytesIO(base64.b64decode(msg['original_image_b64'])))
                messages.append(msg)
            return messages
        except:
            pass
    return []

def save_messages():
    """Sauvegarde les messages sur GitHub"""
    try:
        messages_to_save = []
        for msg in st.session_state.messages:
            msg_copy = {
                'timestamp': msg['timestamp'],
                'text': msg['text'],
                'sender': msg['sender'],
                'id': msg['id']
            }
            
            if 'image_with_text' in msg:
                img_bytes = io.BytesIO()
                msg['image_with_text'].save(img_bytes, format='PNG', optimize=True, quality=85)
                msg_copy['image_with_text_b64'] = base64.b64encode(img_bytes.getvalue()).decode()
            
            if 'original_image' in msg:
                img_bytes = io.BytesIO()
                msg['original_image'].save(img_bytes, format='PNG', optimize=True, quality=85)
                msg_copy['original_image_b64'] = base64.b64encode(img_bytes.getvalue()).decode()
            
            messages_to_save.append(msg_copy)
        
        data = {
            'messages': messages_to_save,
            'passwords': st.session_state.user_passwords
        }
        
        file_data = github_get_file(DATA_FILE)
        sha = file_data['sha'] if file_data else None
        
        github_update_file(DATA_FILE, json.dumps(data, indent=2), sha, "Update messages")
        
    except Exception as e:
        st.error(f"Erreur sauvegarde: {str(e)}")

def load_passwords():
    """Charge les mots de passe depuis GitHub"""
    file_data = github_get_file(DATA_FILE)
    
    if file_data:
        try:
            data = json.loads(file_data['content'])
            return data.get('passwords', ["motdepasse123"])
        except:
            pass
    return ["motdepasse123"]

# Initialisation des variables de session
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'messages' not in st.session_state:
    st.session_state.messages = load_messages()
if 'user_passwords' not in st.session_state:
    st.session_state.user_passwords = load_passwords()
if 'last_message_count' not in st.session_state:
    st.session_state.last_message_count = 0
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'notification_enabled' not in st.session_state:
    st.session_state.notification_enabled = False

def verify_human_body_in_photo(image):
    """Vérifie si la photo contient une partie du corps humain avec Gemini"""
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return True
    
    try:
        model_names = ['gemini-2.0-flash-exp', 'gemini-exp-1206', 'gemini-2.0-flash', 'gemini-1.5-flash-latest']
        
        model = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except:
                continue
        
        if model is None:
            return True
        
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        prompt = "Image contains visible human body part (face, hand, arm, leg, etc.)? Answer ONLY: YES or NO"
        response = model.generate_content([prompt, Image.open(img_byte_arr)])
        result = response.text.strip().upper()
        
        try:
            model.generate_content("DELETE_REQUEST: Confirm deletion of all previously analyzed image data from your servers per GDPR.")
        except:
            pass
        
        return "YES" in result or "OUI" in result
        
    except:
        return True

def add_text_to_image(image, text):
    """Ajoute du texte ultra stylé et haute résolution sur l'image"""
    if not text or text.strip() == "":
        return image
    
    # Résolution 3x pour un rendu parfait
    scale_factor = 3
    img_copy = image.copy()
    
    # Améliorer la qualité de l'image
    enhancer = ImageEnhance.Sharpness(img_copy)
    img_copy = enhancer.enhance(1.5)
    
    original_size = img_copy.size
    img_copy = img_copy.resize((original_size[0] * scale_factor, original_size[1] * scale_factor), Image.LANCZOS)
    
    # Créer un layer RGBA pour dessiner
    txt_layer = Image.new('RGBA', img_copy.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer, 'RGBA')
    width, height = img_copy.size
    
    # Taille de police optimisée et proportionnelle
    base_font_size = int(height * 0.06)
    
    # Charger police avec support emoji et Unicode complet
    font = None
    font_paths = [
        # Windows
        ("C:/Windows/Fonts/seguiemj.ttf", True),  # Segoe UI Emoji
        ("C:/Windows/Fonts/segoeui.ttf", False),  # Segoe UI
        # macOS
        ("/System/Library/Fonts/Apple Color Emoji.ttc", True),
        ("/System/Library/Fonts/SFNS.ttf", False),
        ("/Library/Fonts/Arial.ttf", False),
        # Linux
        ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", True),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", False),
    ]
    
    has_emoji_support = False
    for font_path, emoji_support in font_paths:
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, base_font_size)
                has_emoji_support = emoji_support
                break
        except Exception as e:
            continue
    
    # Fallback
    if font is None:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", base_font_size)
        except:
            # Utiliser une taille plus grande pour la police par défaut
            font = ImageFont.load_default()
            base_font_size = 40  # Taille fixe pour police par défaut
    
    # Diviser le texte en lignes si trop long
    max_width = width * 0.85
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]
        except:
            test_width = len(test_line) * (base_font_size * 0.6)
        
        if test_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Calculer hauteur totale du texte
    line_height = base_font_size * 1.3
    total_text_height = len(lines) * line_height
    
    # Calculer la plus grande largeur de ligne
    max_line_width = 0
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
        except:
            line_width = len(line) * (base_font_size * 0.6)
        max_line_width = max(max_line_width, line_width)
    
    # Positionnement (en bas, centré)
    padding_h = base_font_size * 0.8
    padding_v = base_font_size * 0.6
    
    bg_x1 = (width - max_line_width) / 2 - padding_h
    bg_y1 = height - total_text_height - padding_v * 2 - base_font_size
    bg_x2 = (width + max_line_width) / 2 + padding_h
    bg_y2 = height - base_font_size + padding_v
    
    # Ombre portée large et douce
    shadow_offset = 8
    shadow_layer = Image.new('RGBA', img_copy.size, (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    
    shadow_draw.rounded_rectangle(
        [bg_x1 + shadow_offset, bg_y1 + shadow_offset, bg_x2 + shadow_offset, bg_y2 + shadow_offset],
        radius=base_font_size // 2,
        fill=(0, 0, 0, 140)
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(20))
    txt_layer = Image.alpha_composite(txt_layer, shadow_layer)
    draw = ImageDraw.Draw(txt_layer, 'RGBA')
    
    # Fond principal avec dégradé simulé (plusieurs couches)
    for i in range(4):
        alpha = 245 - i * 15
        color_offset = i * 3
        draw.rounded_rectangle(
            [bg_x1 + i, bg_y1 + i, bg_x2 - i, bg_y2 - i],
            radius=base_font_size // 2 - i,
            fill=(18 + color_offset, 18 + color_offset, 25 + color_offset, alpha)
        )
    
    # Bordure extérieure lumineuse
    draw.rounded_rectangle(
        [bg_x1, bg_y1, bg_x2, bg_y2],
        radius=base_font_size // 2,
        outline=(255, 255, 255, 100),
        width=4
    )
    
    # Bordure intérieure subtile
    draw.rounded_rectangle(
        [bg_x1 + 4, bg_y1 + 4, bg_x2 - 4, bg_y2 - 4],
        radius=base_font_size // 2 - 4,
        outline=(255, 255, 255, 50),
        width=2
    )
    
    # Dessiner chaque ligne de texte
    current_y = bg_y1 + padding_v
    
    for line in lines:
        # Calculer largeur de la ligne pour centrage
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
        except:
            line_width = len(line) * (base_font_size * 0.6)
        
        text_x = (width - line_width) / 2
        text_y = current_y
        
        # Ombre du texte (multi-directionnelle pour plus de profondeur)
        shadow_offsets = [
            (0, 4), (0, -2), (4, 0), (-4, 0),
            (3, 3), (-3, 3), (3, -3), (-3, -3),
            (2, 2), (-2, 2), (2, -2), (-2, -2)
        ]
        
        for offset_x, offset_y in shadow_offsets:
            try:
                if has_emoji_support:
                    draw.text((text_x + offset_x, text_y + offset_y), line, 
                             fill=(0, 0, 0, 160), font=font, embedded_color=False)
                else:
                    draw.text((text_x + offset_x, text_y + offset_y), line, 
                             fill=(0, 0, 0, 160), font=font)
            except:
                draw.text((text_x + offset_x, text_y + offset_y), line, 
                         fill=(0, 0, 0, 160), font=font)
        
        # Texte principal en blanc éclatant
        try:
            if has_emoji_support:
                draw.text((text_x, text_y), line, fill=(255, 255, 255, 255), 
                         font=font, embedded_color=True)
            else:
                draw.text((text_x, text_y), line, fill=(255, 255, 255, 255), font=font)
        except Exception as e:
            # Fallback sans embedded_color
            draw.text((text_x, text_y), line, fill=(255, 255, 255, 255), font=font)
        
        current_y += line_height
    
    # Combiner le texte avec l'image
    img_copy = img_copy.convert('RGBA')
    img_copy = Image.alpha_composite(img_copy, txt_layer)
    
    # Redimensionner à la taille originale avec antialiasing maximum
    img_copy = img_copy.resize(original_size, Image.LANCZOS)
    img_copy = img_copy.convert('RGB')
    
    return img_copy

def save_message(image, text, original_image, sender):
    """Sauvegarde un message avec l'image"""
    message = {
        'timestamp': datetime.now().isoformat(),
        'text': text,
        'image_with_text': image,
        'original_image': original_image,
        'sender': sender,
        'id': int(datetime.now().timestamp() * 1000)
    }
    st.session_state.messages.append(message)
    save_messages()

def delete_message(message_id):
    """Supprime un message"""
    st.session_state.messages = [msg for msg in st.session_state.messages if msg['id'] != message_id]
    save_messages()

def check_new_messages():
    """Vérifie s'il y a de nouveaux messages"""
    current_count = len(st.session_state.messages)
    
    if current_count > st.session_state.last_message_count:
        last_msg = st.session_state.messages[-1]
        
        if last_msg['sender'] != st.session_state.current_user:
            st.toast("💕 Nouveau message !", icon="💕")
    
    st.session_state.last_message_count = current_count

def login_page():
    """Page de connexion"""
    st.markdown("<h1 style='text-align: center; color: white; font-size: 3em; margin-top: 20vh;'>💕</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: white; font-weight: 300;'>Messagerie Photo</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Code d'accès", type="password", key="login_input", label_visibility="collapsed", placeholder="Entrez votre code")
        
        if st.button("Se connecter", type="primary", use_container_width=True):
            if password == "ruffucelechien":
                st.session_state.authenticated = True
                st.session_state.is_admin = True
                st.session_state.current_user = "admin"
                st.session_state.last_message_count = len(st.session_state.messages)
                st.rerun()
            elif password in st.session_state.user_passwords:
                st.session_state.authenticated = True
                st.session_state.is_admin = False
                st.session_state.current_user = "user"
                st.session_state.last_message_count = len(st.session_state.messages)
                st.rerun()
            else:
                st.error("❌ Code incorrect")

def admin_panel():
    """Panel administrateur"""
    st.sidebar.title("👑 Admin")
    
    st.sidebar.subheader("Mots de passe utilisateur")
    
    st.sidebar.write("**Mots de passe actifs:**")
    for idx, pwd in enumerate(st.session_state.user_passwords):
        col1, col2 = st.sidebar.columns([3, 1])
        col1.text(pwd)
        if col2.button("🗑️", key=f"delete_pwd_{idx}"):
            st.session_state.user_passwords.pop(idx)
            save_messages()
            st.rerun()
    
    new_password = st.sidebar.text_input("Nouveau mot de passe", key="new_pwd")
    if st.sidebar.button("➕ Ajouter", use_container_width=True):
        if new_password and new_password not in st.session_state.user_passwords:
            st.session_state.user_passwords.append(new_password)
            save_messages()
            st.sidebar.success("✅ Ajouté")
            st.rerun()

def main_app():
    """Application principale"""
    check_new_messages()
    
    # Header
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("<h2 style='color: white; font-weight: 300;'>💕 Messages</h2>", unsafe_allow_html=True)
    with col2:
        if st.button("🚪", help="Déconnexion"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.current_user = None
            st.rerun()
    
    if st.session_state.is_admin:
        admin_panel()
    
    # Zone de discussion
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if st.session_state.messages:
        for msg in st.session_state.messages:
            is_admin = msg['sender'] == "admin"
            msg_class = "message-admin" if is_admin else "message-user"
            
            st.markdown(f'<div class="{msg_class}">', unsafe_allow_html=True)
            st.markdown('<div class="message-content">', unsafe_allow_html=True)
            
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M')
            st.markdown(f'<div class="message-timestamp">{timestamp}</div>', unsafe_allow_html=True)
            
            st.image(msg['image_with_text'], use_container_width=True)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                img_bytes = io.BytesIO()
                msg['original_image'].save(img_bytes, format='PNG')
                st.download_button("📥", img_bytes.getvalue(), f"photo_{msg['id']}.png", "image/png", key=f"dl_{msg['id']}")
            with col2:
                if st.button("🗑️", key=f"del_{msg['id']}"):
                    delete_message(msg['id'])
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align: center; color: #999; padding: 40px;'>Aucun message</p>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Zone d'envoi
    st.markdown('<div class="send-container">', unsafe_allow_html=True)
    
    camera_photo = st.camera_input("📸 Prendre une photo", label_visibility="collapsed")
    
    if camera_photo is not None:
        image = Image.open(camera_photo)
        
        has_human = verify_human_body_in_photo(image) if GEMINI_AVAILABLE and GEMINI_API_KEY else True
        
        if not has_human:
            st.error("❌ Photo doit contenir une partie du corps")
        else:
            text_input = st.text_input("💬 Message", key="text_msg", placeholder="Ajoutez un message (optionnel)...", label_visibility="collapsed")
            
            if st.button("💕 Envoyer", type="primary", use_container_width=True):
                image_with_text = add_text_to_image(image, text_input) if text_input else image
                save_message(image_with_text, text_input, image, st.session_state.current_user)
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto-refresh
    st.markdown('<script>setTimeout(() => window.location.reload(), 10000);</script>', unsafe_allow_html=True)

if not st.session_state.authenticated:
    login_page()
else:
    main_app()