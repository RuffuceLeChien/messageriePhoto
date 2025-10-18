import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import json
import os
from datetime import datetime
import base64
import requests

# Tentative d'import de Gemini (optionnel)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Configuration de la page
st.set_page_config(page_title="Messagerie Photo", layout="centered")

# CSS pour messages alignés gauche/droite
st.markdown("""
<style>
    .message-container-admin {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 20px;
    }
    .message-container-user {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 20px;
    }
    .message-content {
        max-width: 70%;
    }
</style>
""", unsafe_allow_html=True)

# CSS pour messages alignés gauche/droite
st.markdown("""
<style>
    .message-right {
        display: flex;
        justify-content: flex-end;
        margin: 10px 0;
    }
    .message-left {
        display: flex;
        justify-content: flex-start;
        margin: 10px 0;
    }
    .message-content {
        max-width: 70%;
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
                msg['image_with_text'].save(img_bytes, format='PNG')
                msg_copy['image_with_text_b64'] = base64.b64encode(img_bytes.getvalue()).decode()
            
            if 'original_image' in msg:
                img_bytes = io.BytesIO()
                msg['original_image'].save(img_bytes, format='PNG')
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
        
        prompt = "Cette image contient-elle une partie visible du corps humain (visage, tête, main, bras, jambe, pied, ou toute autre partie du corps) ? Réponds UNIQUEMENT: OUI ou NON"
        response = model.generate_content([prompt, Image.open(img_byte_arr)])
        result = response.text.strip().upper()
        
        try:
            model.generate_content("DELETE_REQUEST: Veuillez confirmer la suppression de toutes les données d'image précédemment analysées de vos serveurs conformément au RGPD.")
        except:
            pass
        
        return "OUI" in result or "YES" in result
        
    except:
        return True

def add_text_to_image(image, text):
    """Ajoute du texte stylé sur l'image avec fond amélioré"""
    if not text or text.strip() == "":
        return image
    
    # Travailler en haute résolution (2x)
    scale_factor = 2
    img_copy = image.copy()
    original_size = img_copy.size
    img_copy = img_copy.resize((original_size[0] * scale_factor, original_size[1] * scale_factor), Image.LANCZOS)
    
    # Créer un calque transparent pour le texte
    txt_layer = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    width, height = img_copy.size
    
    # Taille de police (7% de la hauteur de l'image)
    font_size = int(height * 0.07)
    
    # Charger une police avec support Unicode/Emoji
    font = None
    font_paths = [
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    for font_path in font_paths:
        try:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
                break
        except:
            continue
    
    if font is None:
        font = ImageFont.load_default()
    
    # Mesurer le texte
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = len(text) * (font_size // 2)
        text_height = font_size
    
    # Position (centré en bas)
    padding = int(font_size * 0.6)
    x = (width - text_width) // 2
    y = height - text_height - padding * 3
    
    # Coordonnées du rectangle de fond
    rect_x1 = x - padding
    rect_y1 = y - padding
    rect_x2 = x + text_width + padding
    rect_y2 = y + text_height + padding
    
    radius = padding
    
    # Ombre portée (flou)
    shadow_offset = 8
    shadow = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [rect_x1 + shadow_offset, rect_y1 + shadow_offset, 
         rect_x2 + shadow_offset, rect_y2 + shadow_offset],
        radius=radius,
        fill=(0, 0, 0, 140)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    txt_layer = Image.alpha_composite(txt_layer, shadow)
    draw = ImageDraw.Draw(txt_layer)
    
    # Fond noir semi-transparent
    draw.rounded_rectangle(
        [rect_x1, rect_y1, rect_x2, rect_y2],
        radius=radius,
        fill=(20, 20, 20, 230)
    )
    
    # Bordure blanche
    draw.rounded_rectangle(
        [rect_x1, rect_y1, rect_x2, rect_y2],
        radius=radius,
        outline=(255, 255, 255, 180),
        width=3
    )
    
    # Ombre du texte
    for offset in [(2, 2), (-2, 2), (2, -2), (-2, -2), (0, 3), (3, 0)]:
        try:
            draw.text((x + offset[0], y + offset[1]), text, font=font, fill=(0, 0, 0, 200), embedded_color=True)
        except:
            draw.text((x + offset[0], y + offset[1]), text, font=font, fill=(0, 0, 0, 200))
    
    # Texte principal blanc
    try:
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255), embedded_color=True)
    except:
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Combiner avec l'image
    img_copy = img_copy.convert('RGBA')
    img_copy = Image.alpha_composite(img_copy, txt_layer)
    
    # Redimensionner à la taille originale
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
            st.toast("📬 Nouveau message reçu !", icon="📬")
    
    st.session_state.last_message_count = current_count

def login_page():
    """Page de connexion"""
    st.title("🔐 Connexion")
    
    password = st.text_input("Entrez le code d'accès", type="password", key="login_input")
    
    if st.button("Se connecter"):
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
    st.sidebar.title("👑 Panel Admin")
    
    st.sidebar.subheader("Gestion des mots de passe utilisateur")
    
    st.sidebar.write("**Mots de passe actifs:**")
    for idx, pwd in enumerate(st.session_state.user_passwords):
        col1, col2 = st.sidebar.columns([3, 1])
        col1.text(pwd)
        if col2.button("🗑️", key=f"delete_pwd_{idx}"):
            st.session_state.user_passwords.pop(idx)
            save_messages()
            st.rerun()
    
    new_password = st.sidebar.text_input("Nouveau mot de passe", key="new_pwd")
    if st.sidebar.button("➕ Ajouter"):
        if new_password and new_password not in st.session_state.user_passwords:
            st.session_state.user_passwords.append(new_password)
            save_messages()
            st.sidebar.success("✅ Mot de passe ajouté")
            st.rerun()

def main_app():
    """Application principale"""
    st.title("📸 Messagerie Photo")
    
    check_new_messages()
    
    # Bouton de déconnexion
    if st.button("🚪 Déconnexion"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.session_state.current_user = None
        st.rerun()
    
    if st.session_state.is_admin:
        admin_panel()
    
    # Section d'envoi de message
    st.header("📤 Envoyer un message")
    
    camera_photo = st.camera_input("Prenez une photo")
    
    if camera_photo is not None:
        image = Image.open(camera_photo)
        
        has_human = True
        if GEMINI_AVAILABLE and GEMINI_API_KEY:
            with st.spinner("🔍 Vérification..."):
                has_human = verify_human_body_in_photo(image)
        
        if not has_human:
            st.error("❌ La photo doit contenir une partie du corps humain. Veuillez reprendre la photo.")
        else:
            st.success("✅ Photo validée!")
            
            text_input = st.text_input("Texte à ajouter sur la photo (optionnel)")
            
            if st.button("📨 Envoyer", type="primary"):
                if text_input:
                    image_with_text = add_text_to_image(image, text_input)
                else:
                    image_with_text = image
                
                save_message(image_with_text, text_input, image, st.session_state.current_user)
                st.success("✅ Message envoyé!")
                st.rerun()
    
    # Affichage des messages
    st.header("💬 Messages")
    
    if st.session_state.messages:
        for msg in st.session_state.messages:
            # Aligner les messages : admin à droite, user à gauche
            is_admin = msg['sender'] == "admin"
            alignment = "message-right" if is_admin else "message-left"
            
            st.markdown(f'<div class="{alignment}"><div class="message-content">', unsafe_allow_html=True)
            
            sender_emoji = "👑" if is_admin else "👤"
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%d/%m/%Y %H:%M')
            st.write(f"{sender_emoji} **{timestamp}**")
            
            st.image(msg['image_with_text'], use_container_width=True)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                img_bytes = io.BytesIO()
                msg['original_image'].save(img_bytes, format='PNG')
                st.download_button(
                    label="📥",
                    data=img_bytes.getvalue(),
                    file_name=f"photo_{msg['id']}.png",
                    mime="image/png",
                    key=f"download_{msg['id']}",
                    help="Télécharger la photo originale"
                )
            
            with col2:
                if st.button("🗑️", key=f"delete_{msg['id']}", help="Supprimer ce message"):
                    delete_message(msg['id'])
                    st.rerun()
            
            st.markdown('</div></div>', unsafe_allow_html=True)
            st.divider()
    else:
        st.info("Aucun message pour le moment")
    
    # Auto-refresh
    st.markdown('<script>setTimeout(() => window.location.reload(), 10000);</script>', unsafe_allow_html=True)

if not st.session_state.authenticated:
    login_page()
else:
    main_app()