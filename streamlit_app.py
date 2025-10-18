import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
st.set_page_config(page_title="Messagerie Photo", layout="centered")

# Configuration GitHub
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "") if hasattr(st, 'secrets') else ""
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "") if hasattr(st, 'secrets') else ""  # Format: "username/repo"
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
                # Convertir les images base64 en objets PIL
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
            
            # Convertir les images en base64
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
        
        # Récupérer le SHA actuel du fichier
        file_data = github_get_file(DATA_FILE)
        sha = file_data['sha'] if file_data else None
        
        # Mettre à jour le fichier
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

# Initialisation des variables de session (APRÈS les définitions de fonctions)
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
    if not GEMINI_AVAILABLE:
        return True
    
    if not GEMINI_API_KEY:
        return True
    
    try:
        model_names = [
            'gemini-2.0-flash-exp',
            'gemini-exp-1206', 
            'gemini-2.0-flash',
            'gemini-1.5-flash-latest', 
            'gemini-1.5-pro-latest', 
            'gemini-1.5-flash',
            'gemini-pro-vision', 
            'gemini-pro'
        ]
        
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
        
        prompt = """Analyse cette image et réponds UNIQUEMENT par 'OUI' ou 'NON'.
        Question: Cette image contient-elle une partie visible du corps humain (visage, tête, main, bras, jambe, pied, ou toute autre partie du corps) ?
        Réponds uniquement: OUI ou NON"""
        
        response = model.generate_content([prompt, Image.open(img_byte_arr)])
        result = response.text.strip().upper()
        
        try:
            deletion_prompt = "DELETE_REQUEST: Veuillez confirmer la suppression de toutes les données d'image précédemment analysées de vos serveurs conformément au RGPD."
            model.generate_content(deletion_prompt)
        except:
            pass
        
        return "OUI" in result
        
    except Exception as e:
        return True

def add_text_to_image(image, text):
    """Ajoute du texte stylé et haute résolution sur l'image"""
    scale_factor = 2
    img_copy = image.copy()
    original_size = img_copy.size
    img_copy = img_copy.resize((original_size[0] * scale_factor, original_size[1] * scale_factor), Image.LANCZOS)
    
    draw = ImageDraw.Draw(img_copy, 'RGBA')
    width, height = img_copy.size
    
    font_size = int(height * 0.05)
    
    font = None
    font_paths = [
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/System/Library/Fonts/SFNS.ttf",
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
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = len(text) * (font_size // 2)
        text_height = font_size
    
    padding = 25
    x = (width - text_width) // 2
    y = height - text_height - padding * 2
    
    background_height = text_height + padding * 2
    background_y = y - padding
    
    shadow_offset = 4
    shadow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [x - padding + shadow_offset, background_y + shadow_offset, 
         x + text_width + padding + shadow_offset, background_y + background_height + shadow_offset],
        radius=20,
        fill=(0, 0, 0, 100)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    img_copy.paste(shadow, (0, 0), shadow)
    
    draw.rounded_rectangle(
        [x - padding, background_y, x + text_width + padding, background_y + background_height],
        radius=20,
        fill=(20, 20, 20, 220)
    )
    
    draw.rounded_rectangle(
        [x - padding, background_y, x + text_width + padding, background_y + background_height],
        radius=20,
        outline=(255, 255, 255, 60),
        width=2
    )
    
    shadow_color = (0, 0, 0, 150)
    for offset in [(2, 2), (-2, 2), (2, -2), (-2, -2)]:
        try:
            draw.text((x + offset[0], y + offset[1]), text, fill=shadow_color, font=font, embedded_color=True)
        except:
            draw.text((x + offset[0], y + offset[1]), text, fill=shadow_color, font=font)
    
    try:
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font, embedded_color=True)
    except:
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    img_copy = img_copy.resize(original_size, Image.LANCZOS)
    
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
    """Vérifie s'il y a de nouveaux messages et envoie une notification"""
    current_count = len(st.session_state.messages)
    
    if current_count > st.session_state.last_message_count:
        last_msg = st.session_state.messages[-1]
        
        if last_msg['sender'] != st.session_state.current_user:
            st.toast("📬 Nouveau message reçu !", icon="📬")
            
            st.markdown("""
                <script>
                if ("Notification" in window && Notification.permission === "granted") {
                    new Notification("Messagerie Photo", {
                        body: "Vous avez reçu un nouveau message !",
                        icon: "📸"
                    });
                }
                </script>
            """, unsafe_allow_html=True)
    
    st.session_state.last_message_count = current_count

def request_notification_permission():
    """Demande la permission pour les notifications du navigateur"""
    st.markdown("""
        <script>
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }
        </script>
    """, unsafe_allow_html=True)

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
    """Application principale de messagerie"""
    st.title("📸 Messagerie Photo")
    
    if not st.session_state.notification_enabled:
        request_notification_permission()
        st.session_state.notification_enabled = True
    
    check_new_messages()
    
    st.markdown("""
        <script>
        setTimeout(function() {
            window.location.reload();
        }, 5000);
        </script>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🚪 Déconnexion"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.current_user = None
            st.rerun()
    
    if st.session_state.is_admin:
        admin_panel()
    
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
            text_input = st.text_input("Texte à ajouter sur la photo (optionnel)", key="text_msg")
            
            if st.button("📨 Envoyer", type="primary"):
                if text_input:
                    image_with_text = add_text_to_image(image, text_input)
                else:
                    image_with_text = image
                
                save_message(image_with_text, text_input, image, st.session_state.current_user)
                st.success("✅ Message envoyé!")
                st.rerun()
    
    st.header("💬 Messages")
    
    if st.session_state.messages:
        for idx, msg in enumerate(reversed(st.session_state.messages)):
            with st.container():
                col1, col2, col3 = st.columns([6, 1, 1])
                
                with col1:
                    sender_emoji = "👑" if msg['sender'] == "admin" else "👤"
                    st.write(f"{sender_emoji} **{datetime.fromisoformat(msg['timestamp']).strftime('%d/%m/%Y %H:%M')}**")
                
                with col2:
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
                
                with col3:
                    if st.button("🗑️", key=f"delete_{msg['id']}", help="Supprimer ce message"):
                        delete_message(msg['id'])
                        st.rerun()
                
                st.image(msg['image_with_text'], use_container_width=True)
                st.divider()
    else:
        st.info("Aucun message pour le moment")

if not st.session_state.authenticated:
    login_page()
else:
    main_app()