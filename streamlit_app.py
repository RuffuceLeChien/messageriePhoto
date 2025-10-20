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

# Tentative d'import de OpenCV pour détection de visage
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Tentative d'import de MediaPipe pour détection de mains et pose
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Tentative d'import de MediaPipe pour détection de mains et corps
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Configuration de la page
st.set_page_config(page_title="💕 Messagerie", page_icon="💕", layout="centered")

# CSS pour un design moderne et élégant
st.markdown("""
<style>
    /* Fond général avec dégradé */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Conteneur principal */
    .main .block-container {
        padding: 2rem 1rem;
        max-width: 900px;
    }
    
    /* Titre principal */
    h1 {
        color: white !important;
        text-align: center;
        font-weight: 300 !important;
        letter-spacing: 2px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        margin-bottom: 2rem !important;
    }
    
    /* Headers */
    h2 {
        color: white !important;
        font-weight: 400 !important;
        font-size: 1.3rem !important;
        margin-top: 2rem !important;
    }
    
    /* Messages alignés - admin à droite */
    .message-container-admin {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 20px;
        animation: slideInRight 0.3s ease;
    }
    
    /* Messages alignés - user à gauche */
    .message-container-user {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 20px;
        animation: slideInLeft 0.3s ease;
    }
    
    .message-content {
        max-width: 70%;
        background: white;
        border-radius: 20px;
        padding: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
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
    
    /* Boutons personnalisés */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
    }
    
    /* Bouton primaire */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(245, 87, 108, 0.6) !important;
    }
    
    /* Input texte */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 15px !important;
        padding: 0.8rem 1rem !important;
        color: #333 !important;
        font-size: 1rem !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #f5576c !important;
        box-shadow: 0 0 0 3px rgba(245, 87, 108, 0.2) !important;
    }
    
    /* Camera input */
    .stCameraInput > div {
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 20px !important;
        padding: 1rem !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
    }
    
    /* Download button petit */
    .stDownloadButton > button {
        background: rgba(255, 255, 255, 0.9) !important;
        color: #667eea !important;
        border-radius: 10px !important;
        padding: 0.4rem 0.8rem !important;
        font-size: 1.2rem !important;
        border: 2px solid #667eea !important;
    }
    
    /* Messages info/warning/error */
    .stAlert {
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 15px !important;
        border-left: 4px solid #667eea !important;
    }
    
    /* Divider */
    hr {
        margin: 1rem 0 !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* Sidebar */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%) !important;
    }
    
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    /* Images avec coins arrondis */
    img {
        border-radius: 15px !important;
    }
    
    /* Spinner personnalisé */
    .stSpinner > div {
        border-top-color: #f5576c !important;
    }
    
    /* Toast notifications */
    .st-toast {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-radius: 15px !important;
    }
</style>
""", unsafe_allow_html=True)

# CSS supplémentaires pour compatibilité
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
if 'countdown_active' not in st.session_state:
    st.session_state.countdown_active = False
if 'countdown_time' not in st.session_state:
    st.session_state.countdown_time = 3

def verify_human_body_simple(image):
    """Vérifie la présence d'un corps humain avec OpenCV + MediaPipe"""
    if not CV2_AVAILABLE:
        st.warning("⚠️ OpenCV non installé. Vérification désactivée.")
        return True
    
    try:
        # Convertir PIL Image en numpy array pour OpenCV
        img_array = np.array(image)
        
        # Convertir RGB en BGR (format OpenCV)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Convertir en niveaux de gris pour OpenCV
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        detections = []
        
        # === DÉTECTION OPENCV (Visages et Corps) ===
        
        # 1. Détection de visages (frontal)
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            if len(faces) > 0:
                detections.append(f"{len(faces)} visage(s)")
        except:
            pass
        
        # 2. Détection de visages (profil)
        try:
            profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
            profiles = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            if len(profiles) > 0:
                detections.append(f"{len(profiles)} profil(s)")
        except:
            pass
        
        # 3. Détection du corps entier
        try:
            body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
            bodies = body_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50))
            if len(bodies) > 0:
                detections.append(f"{len(bodies)} corps")
        except:
            pass
        
        # 4. Détection du haut du corps
        try:
            upperbody_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml')
            upperbodies = upperbody_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 50))
            if len(upperbodies) > 0:
                detections.append(f"{len(upperbodies)} haut du corps")
        except:
            pass
        
        # 5. Détection du bas du corps
        try:
            lowerbody_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_lowerbody.xml')
            lowerbodies = lowerbody_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
            if len(lowerbodies) > 0:
                detections.append(f"{len(lowerbodies)} bas du corps")
        except:
            pass
        
        # 6. Détection des yeux
        try:
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20))
            if len(eyes) >= 2:
                detections.append(f"{len(eyes)} yeux")
        except:
            pass
        
        # === DÉTECTION MEDIAPIPE (Mains, Pose, Visage) ===
        
        if MEDIAPIPE_AVAILABLE:
            # Détection des mains
            try:
                mp_hands = mp.solutions.hands
                hands_detector = mp_hands.Hands(
                    static_image_mode=True,
                    max_num_hands=2,
                    min_detection_confidence=0.5
                )
                results_hands = hands_detector.process(img_array)
                if results_hands.multi_hand_landmarks:
                    num_hands = len(results_hands.multi_hand_landmarks)
                    detections.append(f"{num_hands} main(s)")
                hands_detector.close()
            except:
                pass
            
            # Détection de la pose (corps, bras, jambes)
            try:
                mp_pose = mp.solutions.pose
                pose_detector = mp_pose.Pose(
                    static_image_mode=True,
                    min_detection_confidence=0.5
                )
                results_pose = pose_detector.process(img_array)
                if results_pose.pose_landmarks:
                    detections.append("pose corporelle")
                pose_detector.close()
            except:
                pass
        
        # Résultat OpenCV
        has_body_part_opencv = len(detections) > 0
        
        # === AJOUT MEDIAPIPE pour mains et pieds ===
        if MEDIAPIPE_AVAILABLE:
            try:
                # Détection des mains
                mp_hands = mp.solutions.hands
                hands_detector = mp_hands.Hands(
                    static_image_mode=True,
                    max_num_hands=2,
                    min_detection_confidence=0.5
                )
                results_hands = hands_detector.process(img_array)
                if results_hands.multi_hand_landmarks:
                    num_hands = len(results_hands.multi_hand_landmarks)
                    detections.append(f"{num_hands} main(s)")
                hands_detector.close()
            except Exception as e:
                st.warning(f"Erreur détection mains: {str(e)}")
            
            try:
                # Détection de la pose (inclut pieds, jambes, bras)
                mp_pose = mp.solutions.pose
                pose_detector = mp_pose.Pose(
                    static_image_mode=True,
                    min_detection_confidence=0.5
                )
                results_pose = pose_detector.process(img_array)
                if results_pose.pose_landmarks:
                    detections.append("pose (corps/pieds/bras)")
                pose_detector.close()
            except Exception as e:
                st.warning(f"Erreur détection pose: {str(e)}")
        
        # Résultat final
        has_body_part = len(detections) > 0
        
        # Afficher seulement si aucune détection
        if not has_body_part:
            st.error("❌ Aucune partie du corps détectée")
        
        return has_body_part
        
    except Exception as e:
        st.error(f"Erreur détection: {str(e)}")
        return True
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
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='font-size: 4rem; margin-bottom: 1rem;'>💕</h1>", unsafe_allow_html=True)
    st.title("Messagerie Photo")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("", type="password", key="login_input", placeholder="Code d'accès", label_visibility="collapsed")
        
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
    st.title("💕 Messagerie Photo")
    
    check_new_messages()
    
    # Bouton de déconnexion discret
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("🚪"):
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.current_user = None
            st.rerun()
    
    if st.session_state.is_admin:
        admin_panel()
    
    # Section d'envoi de message
    st.header("📤 Nouveau message")
    
    # Choix du mode de capture
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 Photo instantanée", use_container_width=True):
            st.session_state.countdown_active = False
    with col2:
        countdown_options = st.selectbox("⏱️ Compte à rebours", [3, 5, 10], key="countdown_select", label_visibility="collapsed")
        if st.button(f"⏱️ Photo dans {countdown_options}s", use_container_width=True):
            st.session_state.countdown_active = True
            st.session_state.countdown_time = countdown_options
    
    # Afficher le compte à rebours si activé
    if st.session_state.countdown_active and st.session_state.countdown_time > 0:
        st.markdown(f"""
            <div style='text-align: center; padding: 2rem;'>
                <h1 style='font-size: 5rem; color: white; animation: pulse 1s infinite;'>
                    {st.session_state.countdown_time}
                </h1>
            </div>
            <style>
                @keyframes pulse {{
                    0%, 100% {{ transform: scale(1); opacity: 1; }}
                    50% {{ transform: scale(1.2); opacity: 0.8; }}
                }}
            </style>
        """, unsafe_allow_html=True)
        
        # Décrémenter le compteur
        import time
        time.sleep(1)
        st.session_state.countdown_time -= 1
        st.rerun()
    
    # Prendre la photo quand le compte à rebours atteint 0
    if st.session_state.countdown_active and st.session_state.countdown_time == 0:
        st.success("📸 Prenez la photo maintenant !")
        st.session_state.countdown_active = False
    
    camera_photo = st.camera_input("📸 Prendre une photo", label_visibility="collapsed")
    
    if camera_photo is not None:
        image = Image.open(camera_photo)
        
        # Vérification du corps humain avec OpenCV + MediaPipe
        has_human = True
        
        if CV2_AVAILABLE:
            with st.spinner("🔍 Vérification de la photo en cours..."):
                has_human = verify_human_body_simple(image)
        else:
            st.warning("⚠️ Vérification désactivée (OpenCV non installé)")
        
        if not has_human:
            st.error("❌ La photo doit contenir une partie du corps humain. Veuillez reprendre la photo.")
        else:
            text_input = st.text_input("", key="text_msg", placeholder="💬 Ajouter un message (optionnel)...", label_visibility="collapsed")
            
            if st.button("💕 Envoyer", type="primary", use_container_width=True):
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